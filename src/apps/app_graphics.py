import os
import logging
import requests
from flask import Flask, send_file, jsonify
from pyzabbix import ZabbixAPI

logging.basicConfig(filename='zabbix_data_processing.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

zabbix_url = "http://10.85.104.3"
zabbix_user = "tauge.suporte"
zabbix_password = "Aehee4haen8Sa.f"

output_dir = os.path.join(os.getcwd(), "output")
os.makedirs(output_dir, exist_ok=True)

def conectar_zabbix():
    try:
        zapi = ZabbixAPI(zabbix_url)
        zapi.login(zabbix_user, zabbix_password)
        logging.info(f"Conectado ao Zabbix API versão {zapi.api_version()}")
        return zapi
    except Exception as e:
        logging.error(f"Erro ao conectar ao Zabbix: {e}")
        raise

def obter_graficos_por_grupo(zapi, group_id):
    try:
        # Obter todos os hosts associados ao group_id
        hosts = zapi.host.get(groupids=group_id, output=['hostid'])
        
        if not hosts:
            logging.error(f"Nenhum host encontrado para o grupo {group_id}.")
            return []
        
        # Obter gráficos para os hosts encontrados
        graphs = []
        for host in hosts:
            graphs.extend(zapi.graph.get(output=['graphid', 'name'], hostids=host['hostid']))
        
        if not graphs:
            logging.error(f"Nenhum gráfico encontrado para o grupo {group_id}.")
            return []
        
        return graphs
    except Exception as e:
        logging.error(f"Erro ao buscar gráficos para o grupo {group_id}: {e}")
        return []

def baixar_grafico_zabbix_via_http(session, graphid, groupid):
    try:
        # Construir a URL do gráfico com parâmetros de tempo
        grafico_url = f"{zabbix_url}/chart2.php?graphid={graphid}&period=3600"
        
        # Caminho de salvamento
        grafico_path = os.path.join(output_dir, f"grupo_{groupid}_grafico_{graphid}.png")
        
        # Fazer o download do gráfico
        headers = {
            'Content-Type': 'application/json',
        }
        response = session.get(grafico_url, headers=headers, stream=True)
        if response.status_code == 200:
            with open(grafico_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            logging.info(f"Gráfico {graphid} do grupo {groupid} salvo em {grafico_path}")
            return grafico_path
        else:
            logging.error(f"Erro ao baixar o gráfico {graphid}: Status code {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Erro ao baixar gráfico {graphid}: {e}")
        return None

@app.route('/baixar_graficos/<int:group_id>', methods=['GET'])
def baixar_graficos(group_id):
    try:
        zapi = conectar_zabbix()

        graficos = obter_graficos_por_grupo(zapi, group_id)

        logging.info(f"Gráficos retornados para o grupo {group_id}: {graficos}")

        if not graficos:
            return jsonify({"erro": "Não foi possível localizar gráficos para o grupo."}), 500
        
        grafico_paths = []

        # Autenticar via sessão para download dos gráficos
        session = requests.Session()
        session.post(f"{zabbix_url}/index.php", data={
            'name': zabbix_user,
            'password': zabbix_password,
            'enter': 'Sign in'
        })

        for grafico in graficos:
            grafico_path = baixar_grafico_zabbix_via_http(session, grafico['graphid'], groupid=group_id)  

            if grafico_path:
                grafico_paths.append(grafico_path)
        
        if not grafico_paths:
            return jsonify({"erro": "Falha ao baixar os gráficos."}), 500
        
        # Retornar o primeiro gráfico baixado como exemplo
        return send_file(grafico_paths[0], as_attachment=True)
    
    except Exception as e:
        logging.error(f"Erro ao processar os gráficos: {e}")
        return jsonify({"erro": "Erro ao processar os gráficos."}), 500

if __name__ == '__main__':
    app.run(debug=True)
