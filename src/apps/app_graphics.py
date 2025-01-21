import os
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
import requests
import json
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

zabbix_url = os.getenv("URL_ZABBIX")
zabbix_user = os.getenv("USER_ZABBIX")
zabbix_password = os.getenv("PASS_ZABBIX")

log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "zabbix.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

output_dir = os.path.join(os.getcwd(), "output", "images")
os.makedirs(output_dir, exist_ok=True)

def load_host_id_from_storage():
    storage_file = 'client_info.json' 
    if os.path.exists(storage_file):
        with open(storage_file, 'r') as f:
            data = json.load(f)
            return data.get('idhostzbx', None)
    return None

def connect_zabbix():
    zapi = ZabbixAPI(zabbix_url)
    zapi.login(zabbix_user, zabbix_password)
    logging.info(f"Connected to Zabbix API version {zapi.api_version()}")
    return zapi

def get_three_months_period():
    today = datetime.today()
    three_months_ago = today - timedelta(days=90)
    
    stime = int(three_months_ago.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    etime = int(today.replace(hour=23, minute=59, second=59, microsecond=0).timestamp())
    
    logging.info(f"Período de três meses: {three_months_ago.date()} até {today.date()}")
    return stime, etime

def download_graph_zabbix_via_http(session, graphid, graph_name, host_name, stime, etime):

    graph_filename = f"grafico_{graphid}.png"
    graph_path = os.path.join(output_dir, graph_filename)
    
    if os.path.exists(graph_path):
        logging.info(f"Graph {graph_filename} já foi baixado anteriormente. Usando o arquivo local.")
        return graph_path

    # Caso o gráfico não esteja no storage, faça a requisição HTTP para baixá-lo
    graph_url = f"{zabbix_url}/chart2.php?graphid={graphid}&stime={stime}&etime={etime}"
    logging.info(f"Gerada URL para gráfico {graphid} do host {host_name}: {graph_url}")
    
    try:
        response = session.get(graph_url, stream=True)
        response.raise_for_status()

        filename = (lambda graph_name: 
                    "grafico_memoria.png" if "memória" in graph_name.lower() 
                    else "grafico_cpu.png" if "CPU - utilização" in graph_name 
                    else f"grafico_{graphid}.png")(graph_name)

        graph_path = os.path.join(output_dir, filename)
        with open(graph_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

        logging.info(f"Gráfico {graphid} do host {host_name} salvo em {graph_path}")
        return graph_path

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao baixar gráfico {graphid} para o host {host_name}: {e}")
        return None

# Função para fazer o download dos gráficos automaticamente
def download_graphs_automatically():
    try:
        host_id = load_host_id_from_storage()
        if not host_id:
            logging.error("HOST_ID não encontrado no armazenamento local.")
            return

        zapi = connect_zabbix()
        host = zapi.host.get(hostids=host_id, output=['hostid', 'name'])
        if not host:
            logging.error(f"Nenhum host encontrado com o ID {host_id}.")
            return

        host_name = host[0]['name']
        logging.info(f"Host identificado: {host_name}")

        graphs = zapi.graph.get(output=['graphid', 'name'], hostids=host_id)

        graphs_relevant = list(filter(
            lambda graph: 'CPU - utilização' in graph['name'] or 'memória' in graph['name'].lower(),
            graphs
        ))

        if not graphs_relevant:
            logging.error("Nenhum gráfico relevante encontrado para o host especificado.")
            return

        session = requests.Session()
        session.post(f"{zabbix_url}/index.php", data={'name': zabbix_user, 'password': zabbix_password, 'enter': 'Sign in'})
        session.headers.update({'User-Agent': 'Mozilla/5.0'})

        stime, etime = get_three_months_period()

        graph_paths = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(download_graph_zabbix_via_http, session, graph['graphid'], graph['name'], host_name, stime, etime)
                for graph in graphs_relevant
            ]
            for future in futures:
                result = future.result()
                if result:
                    graph_paths.append(result)

        if not graph_paths:
            logging.error("Falha ao baixar gráficos.")
            return

        logging.info(f"Gráficos baixados com sucesso: {graph_paths}")

    except Exception as e:
        logging.error(f"Erro ao processar gráficos: {e}")

app = Flask(__name__)

@app.route('/baixar_graficos', methods=['GET'])
def download_graphs():
    try:
        host_id = load_host_id_from_storage()
        if not host_id:
            return jsonify({"error": "HOST_ID não encontrado no armazenamento local."}), 400

        zapi = connect_zabbix()
        host = zapi.host.get(hostids=host_id, output=['hostid', 'name'])
        if not host:
            return jsonify({"error": f"Nenhum host encontrado com o ID {host_id}."}), 404

        host_name = host[0]['name']
        logging.info(f"Host identificado: {host_name}")

        graphs = zapi.graph.get(output=['graphid', 'name'], hostids=host_id)

        graphs_relevant = list(filter(
            lambda graph: 'CPU - utilização' in graph['name'] or 'memória' in graph['name'].lower(),
            graphs
        ))

        if not graphs_relevant:
            return jsonify({"error": "Nenhum gráfico relevante encontrado para o host especificado."}), 404

        session = requests.Session()
        session.post(f"{zabbix_url}/index.php", data={'name': zabbix_user, 'password': zabbix_password, 'enter': 'Sign in'})
        session.headers.update({'User-Agent': 'Mozilla/5.0'})

        stime, etime = get_three_months_period()

        graph_paths = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(download_graph_zabbix_via_http, session, graph['graphid'], graph['name'], host_name, stime, etime)
                for graph in graphs_relevant
            ]
            for future in futures:
                result = future.result()
                if result:
                    graph_paths.append(result)

        if not graph_paths:
            return jsonify({"error": "Falha ao baixar gráficos."}), 500

        return jsonify({"message": "Gráficos baixados com sucesso.", "files": graph_paths}), 200

    except Exception as e:
        logging.error(f"Erro ao processar gráficos: {e}")
        return jsonify({"error": "Erro ao processar gráficos."}), 500

if __name__ == '__main__':
    download_graphs_automatically()
