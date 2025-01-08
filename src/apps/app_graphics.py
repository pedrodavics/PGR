import os
import logging
import requests
from datetime import datetime, timedelta
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
        hosts = zapi.host.get(groupids=group_id, output=['hostid', 'name'])
        
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
        
        return hosts, graphs
    except Exception as e:
        logging.error(f"Erro ao buscar gráficos para o grupo {group_id}: {e}")
        return [], []

def obter_periodo_tres_meses():
    hoje = datetime.today()

    # Primeiro dia do mês atual
    primeiro_dia_mes_atual = hoje.replace(day=1)

    # Último dia do mês anterior ao mês atual
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)

    # Primeiro dia do mês 3 meses atrás
    primeiro_dia_tres_meses_atras = (primeiro_dia_mes_atual - timedelta(days=90)).replace(day=1)

    stime = int(primeiro_dia_tres_meses_atras.timestamp())
    etime = int(ultimo_dia_mes_anterior.replace(hour=23, minute=59, second=59).timestamp())

    return stime, etime

def baixar_grafico_zabbix_via_http(session, graphid, groupid, host_name):
    try:
        # Obter o período dos últimos 3 meses
        desde, ate = obter_periodo_tres_meses()
        
        logging.info(f"Período calculado: stime={desde}, etime={ate}")

        # Construir a URL do gráfico com o período exato
        grafico_url = f"{zabbix_url}/chart2.php?graphid={graphid}&stime={desde}&etime={ate}"
        
        # Caminho de salvamento
        grupo_dir = os.path.join(output_dir, f"graficos_{groupid}")
        os.makedirs(grupo_dir, exist_ok=True)

        host_dir = os.path.join(grupo_dir, host_name)
        os.makedirs(host_dir, exist_ok=True)
        
        grafico_path = os.path.join(host_dir, f"grafico_{graphid}.png")

        # Fazer o download do gráfico
        headers = {'Content-Type': 'application/json'}
        response = session.get(grafico_url, headers=headers, stream=True)
        if response.status_code == 200:
            with open(grafico_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            logging.info(f"Gráfico {graphid} do host {host_name} no grupo {groupid} salvo em {grafico_path}")
            return grafico_path
        else:
            logging.error(f"Erro ao baixar o gráfico {graphid} para o host {host_name}: Status code {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Erro ao baixar gráfico {graphid} para o host {host_name}: {e}")
        return None


@app.route('/baixar_graficos/<int:group_id>', methods=['GET'])
def baixar_graficos(group_id):
    try:
        zapi = conectar_zabbix()

        hosts, graficos = obter_graficos_por_grupo(zapi, group_id)

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

        for host in hosts:
            for grafico in graficos:
                grafico_path = baixar_grafico_zabbix_via_http(session, grafico['graphid'], group_id, host['name'])  

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
