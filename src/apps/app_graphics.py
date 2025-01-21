import os
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "zabbix.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,  # Aumentei o nível de log para DEBUG para mais informações
    format='%(asctime)s - %(levelname)s - %(message)s'
)

output_dir = os.path.join(os.getcwd(), "output", "images")
os.makedirs(output_dir, exist_ok=True)

zabbix_url = os.getenv("URL_ZABBIX")
zabbix_user = os.getenv("USER_ZABBIX")
zabbix_password = os.getenv("PASS_ZABBIX")
host_id = os.getenv("ID_ZABBIX")

def connect_zabbix():
    zapi = ZabbixAPI(zabbix_url)
    zapi.login(zabbix_user, zabbix_password)
    logging.info(f"Connected to Zabbix API version {zapi.api_version()}")
    return zapi

def get_three_months_period():
    today = datetime.today()
    three_months_ago = today - timedelta(days=90)

    # Gerando os timestamps para o período de 90 dias
    stime = int(three_months_ago.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    etime = int(today.replace(hour=23, minute=59, second=59, microsecond=0).timestamp())

    # Debugging dos valores de stime e etime
    logging.debug(f"Debug - stime: {stime} ({three_months_ago})")
    logging.debug(f"Debug - etime: {etime} ({today})")

    return stime, etime

def download_graph_zabbix_via_http(graphid, graph_name, host_name, stime, etime):
    # Gerando a URL do gráfico com os parâmetros stime e etime através da API Zabbix
    try:
        graph_url = f"{zabbix_url}/chart2.php?graphid={graphid}&stime={stime}&etime={etime}"
        logging.debug(f"Generated URL for graph {graphid} of host {host_name}: {graph_url}")

        response = requests.get(graph_url, stream=True)
        response.raise_for_status()

        # Verificando o tipo de conteúdo da resposta
        content_type = response.headers.get('Content-Type')
        if 'image/png' not in content_type:
            logging.error(f"Expected image/png but got {content_type}. URL: {graph_url}")
            return None

        filename = (lambda graph_name: 
                    "grafico_memoria.png" if "memória" in graph_name.lower() 
                    else "grafico_cpu.png" if "CPU - utilização" in graph_name 
                    else f"grafico_{graphid}.png")(graph_name)

        graph_path = os.path.join(output_dir, filename)
        with open(graph_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

        logging.info(f"Graph {graphid} of host {host_name} saved at {graph_path}")
        return graph_path

    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading graph {graphid} for host {host_name}: {e}")
        return None


app = Flask(__name__)

@app.route('/baixar_graficos', methods=['GET'])
def download_graphs():
    try:
        if not host_id:
            return jsonify({"error": "HOST_ID not found in environment variables."}), 400

        zapi = connect_zabbix()
        host = zapi.host.get(hostids=host_id, output=['hostid', 'name'])
        if not host:
            return jsonify({"error": f"No host found with ID {host_id}."}), 404

        host_name = host[0]['name']
        logging.info(f"Host identified: {host_name}")

        graphs = zapi.graph.get(output=['graphid', 'name'], hostids=host_id)

        graphs_relevant = list(filter(
            lambda graph: 'CPU - utilização' in graph['name'] or 'memória' in graph['name'].lower(),
            graphs
        ))

        if not graphs_relevant:
            return jsonify({"error": "No relevant graphs found for the specified host."}), 404

        stime, etime = get_three_months_period()

        graph_paths = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(download_graph_zabbix_via_http, graph['graphid'], graph['name'], host_name, stime, etime)
                for graph in graphs_relevant
            ]
            for future in futures:
                result = future.result()
                if result:
                    graph_paths.append(result)

        if not graph_paths:
            return jsonify({"error": "Failed to download graphs."}), 500

        return jsonify({"message": "Graphs downloaded successfully.", "files": graph_paths}), 200

    except Exception as e:
        logging.error(f"Error processing graphs: {e}")
        return jsonify({"error": "Error processing graphs."}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
