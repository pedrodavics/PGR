import os
import logging
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "zabbix.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

output_dir = os.path.join(os.getcwd(), "output")
os.makedirs(output_dir, exist_ok=True)

zabbix_url = os.getenv("URL_ZABBIX")
zabbix_user = os.getenv("USER_ZABBIX")
zabbix_password = os.getenv("PASS_ZABBIX")

def conectar_zabbix():
    zapi = ZabbixAPI(zabbix_url)
    zapi.login(zabbix_user, zabbix_password)
    logging.info(f"Conectado ao Zabbix API versão {zapi.api_version()}")
    return zapi

def obter_periodo_tres_meses():
    hoje = datetime.today()
    tres_meses_atras = hoje - timedelta(days=90)
    
    stime = int(tres_meses_atras.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    etime = int(hoje.replace(hour=23, minute=59, second=59, microsecond=0).timestamp())
    
    logging.info(f"Período dos últimos 3 meses: {tres_meses_atras.date()} até {hoje.date()}")
    return stime, etime

def baixar_grafico_zabbix_via_http(session, graphid, graph_name, host_name, stime, etime):
    grafico_url = f"{zabbix_url}/chart2.php?graphid={graphid}&stime={stime}&etime={etime}"
    logging.info(f"URL gerado para o gráfico {graphid} do host {host_name}: {grafico_url}")
    try:
        response = session.get(grafico_url, stream=True)
        response.raise_for_status()
        
        host_dir = os.path.join(output_dir, host_name)
        os.makedirs(host_dir, exist_ok=True)

        # Nome do arquivo com base no tipo do gráfico
        if "memória" in graph_name.lower():
            filename = "grafico_memoria.png"
        elif "CPU - utilização" in graph_name:
            filename = "grafico_cpu.png"
        else:
            filename = f"grafico_{graphid}.png"

        grafico_path = os.path.join(host_dir, filename)
        with open(grafico_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)

        logging.info(f"Gráfico {graphid} do host {host_name} salvo em {grafico_path}")
        return grafico_path

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao baixar gráfico {graphid} para o host {host_name}: {e}")
        return None

app = Flask(__name__)

@app.route('/baixar_graficos/<int:host_id>', methods=['GET'])
def baixar_graficos(host_id):
    try:
        zapi = conectar_zabbix()
        host = zapi.host.get(hostids=host_id, output=['hostid', 'name'])
        if not host:
            return jsonify({"erro": f"Nenhum host encontrado com o ID {host_id}."}), 404

        host_name = host[0]['name']
        logging.info(f"Host identificado: {host_name}")

        graficos = zapi.graph.get(output=['graphid', 'name'], hostids=host_id)
        graficos_relevantes = [grafico for grafico in graficos if 'CPU - utilização' in grafico['name'] or 'memória' in grafico['name'].lower()]

        if not graficos_relevantes:
            return jsonify({"erro": "Nenhum gráfico relevante encontrado para o host especificado."}), 404

        session = requests.Session()
        session.post(f"{zabbix_url}/index.php", data={'name': zabbix_user, 'password': zabbix_password, 'enter': 'Sign in'})

        stime, etime = obter_periodo_tres_meses()

        grafico_paths = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(baixar_grafico_zabbix_via_http, session, grafico['graphid'], grafico['name'], host_name, stime, etime)
                for grafico in graficos_relevantes
            ]
            for future in futures:
                result = future.result()
                if result:
                    grafico_paths.append(result)

        if not grafico_paths:
            return jsonify({"erro": "Falha ao baixar os gráficos."}), 500

        return jsonify({"mensagem": "Gráficos baixados com sucesso.", "arquivos": grafico_paths}), 200

    except Exception as e:
        logging.error(f"Erro ao processar os gráficos: {e}")
        return jsonify({"erro": "Erro ao processar os gráficos."}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
