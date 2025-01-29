import os
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pyzabbix import ZabbixAPI
from scipy.signal import argrelextrema
import logging
import json
from flask import Flask, send_file, jsonify
from dotenv import load_dotenv

load_dotenv()

# Configuração do log
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, 'zabbix.log'), level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Configuração do Zabbix
zabbix_url = os.getenv("URL_ZBX")
zabbix_user = os.getenv("USER_ZBX")
zabbix_password = os.getenv("PASS_ZBX")

# Função para ler o hostid do arquivo JSON
def obter_hostid_do_json():
    try:
        with open('client_info.json', 'r') as file:
            client_info = json.load(file)
            hostid = client_info.get('idhostzbx')
            if hostid is None:
                logging.error("O hostid não foi encontrado no arquivo JSON.")
                raise ValueError("Host ID não encontrado no arquivo JSON.")
            return hostid
    except Exception as e:
        logging.error(f"Erro ao ler o arquivo client_info.json: {e}")
        raise

def conectar_zabbix():
    try:
        zapi = ZabbixAPI(zabbix_url)
        zapi.login(zabbix_user, zabbix_password)
        logging.info(f"Conectado ao Zabbix API versão {zapi.api_version()}")
        return zapi
    except Exception as e:
        logging.error(f"Erro ao conectar ao Zabbix: {e}")
        raise

def obter_itens_do_host(zapi, hostid):
    try:
        items = zapi.item.get(hostids=hostid, output="extend")
        if not items:
            logging.warning(f"Nenhum item encontrado para o host {hostid}.")
            return {}

        # Filtrando apenas os itens que contêm "CPU" ou "Memória" no nome
        items_per_host = {item['name']: item['itemid'] for item in items if "CPU" in item['name'] or "memória" in item['name']}
        logging.info(f"Itens encontrados para o host {hostid}: {list(items_per_host.keys())}")
        return items_per_host
    except Exception as e:
        logging.error(f"Erro ao obter itens do host {hostid}: {e}")
        return {}

def obter_historico_ultimos_90_dias(zapi, itemid):
    try:
        hoje = pd.Timestamp.today()
        time_from = int((hoje - pd.Timedelta(days=90)).timestamp()) 
        time_till = int(hoje.timestamp()) 

        historico = zapi.history.get(
            itemids=itemid,
            time_from=time_from,
            time_till=time_till,
            output="extend",
            history=3,
            sortfield="clock",
            sortorder="ASC",
            limit=100000
        )

        if not historico:
            logging.warning(f"Nenhum histórico encontrado para o item {itemid}.")
        return historico
    except Exception as e:
        logging.error(f"Erro ao obter histórico do item {itemid}: {e}")
        return []

def gerar_grafico_consolidado(zapi, itens_per_host, hostid):
    fig = go.Figure()

    for item_name, itemid in itens_per_host.items():
        historico = obter_historico_ultimos_90_dias(zapi, itemid)

        if not historico:
            logging.warning(f"Nenhum dado encontrado para o item {item_name} do host {hostid}.")
            continue

        try:
            timestamps = [int(i['clock']) for i in historico]
            valores = [float(i['value']) for i in historico]
            datas = [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)) for ts in timestamps]
            df = pd.DataFrame({'DataHora': pd.to_datetime(datas), 'Valor': valores}).sort_values('DataHora').set_index('DataHora').resample('D').mean().dropna()

            min_loc = argrelextrema(df['Valor'].values, np.less)[0]
            max_loc = argrelextrema(df['Valor'].values, np.greater)[0]

            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['Valor'],
                mode='lines',
                name=item_name
            ))

            fig.add_trace(go.Scatter(
                x=df.index[min_loc],
                y=df['Valor'].iloc[min_loc],
                mode='markers',
                marker=dict(color='green', size=8),
                name=f"{item_name} - Mínimos Locais"
            ))

            fig.add_trace(go.Scatter(
                x=df.index[max_loc],
                y=df['Valor'].iloc[max_loc],
                mode='markers',
                marker=dict(color='red', size=8),
                name=f"{item_name} - Máximos Locais"
            ))

        except KeyError as e:
            logging.error(f"Erro ao acessar chave nos dados de histórico para o item {item_name}: {e}")
            continue

    # Diretório de saída para os gráficos
    output_dir = 'output/images'
    os.makedirs(output_dir, exist_ok=True)

    fig_path = os.path.join(output_dir, f"cpu_memoria.jpeg")
    fig.write_image(fig_path, format='jpeg', engine='kaleido') 
    logging.info(f"Gráfico consolidado salvo em {fig_path}")
    return fig_path

@app.route('/gerar_grafico', methods=['GET'])
def gerar_grafico():
    try:
        hostid = obter_hostid_do_json() 
        zapi = conectar_zabbix()
        itens_per_host = obter_itens_do_host(zapi, hostid)
        fig_path = gerar_grafico_consolidado(zapi, itens_per_host, hostid)

        if os.path.exists(fig_path):
            return send_file(fig_path, as_attachment=True)
        return jsonify({"erro": "Gráfico não encontrado."}), 404
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico: {e}")
        return jsonify({"erro": "Erro ao gerar gráfico."}), 500

if __name__ == '__main__':
    with app.app_context():
          gerar_grafico()