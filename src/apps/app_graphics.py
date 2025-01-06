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

# Função para buscar gráficos por group_id
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

def baixar_grafico_zabbix(zapi, graphid, groupid):
    try:
        graph = zapi.graph.get(graphids=graphid, output='extend')
        if not graph:
            logging.error(f"Gráfico com ID {graphid} não encontrado.")
            return None

        # Registre o conteúdo completo do gráfico para verificar a estrutura
        logging.info(f"Conteúdo do gráfico {graphid}: {graph}")
        
        # Verifique o campo correto para a URL, se for necessário
        graph_url = graph[0].get('url', None)
        
        if not graph_url:
            logging.error(f"Campo 'url' não encontrado para o gráfico {graphid}.")
            return None
        
        grafico_url_completa = f"{zabbix_url}{graph_url}"

        grafico_path = os.path.join(output_dir, f"grupo_{groupid}_grafico_{graphid}.jpeg")

        response = requests.get(grafico_url_completa)
        if response.status_code == 200:
            img_data = response.content
            with open(grafico_path, 'wb') as f:
                f.write(img_data)
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

        for grafico in graficos:
            grafico_path = baixar_grafico_zabbix(zapi, grafico['graphid'], groupid=group_id)  

            if grafico_path:
                grafico_paths.append(grafico_path)
        
        if not grafico_paths:
            return jsonify({"erro": "Falha ao baixar os gráficos."}), 500
        
        return send_file(grafico_paths[0], as_attachment=True)
    
    except Exception as e:
        logging.error(f"Erro ao processar os gráficos: {e}")
        return jsonify({"erro": "Erro ao processar os gráficos."}), 500

if __name__ == '__main__':
    app.run(debug=True)
