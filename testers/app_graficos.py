import os
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pyzabbix import ZabbixAPI
from scipy.signal import argrelextrema
import logging
from flask import Flask, send_file, jsonify

logging.basicConfig(filename='zabbix_data_processing.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Configuração do Zabbix
zabbix_url = "http://10.85.104.3"
zabbix_user = "tauge.suporte"
zabbix_password = "Aehee4haen8Sa.f"

def conectar_zabbix():
    try:
        zapi = ZabbixAPI(zabbix_url)
        zapi.login(zabbix_user, zabbix_password)
        logging.info(f"Conectado ao Zabbix API versão {zapi.api_version()}")
        return zapi
    except Exception as e:
        logging.error(f"Erro ao conectar ao Zabbix: {e}")
        raise

def obter_itens_do_grupo(zapi, groupid):
    try:
        hosts = zapi.host.get(groupids=groupid, output="extend")
        if not hosts:
            logging.warning("Nenhum host encontrado no grupo fornecido.")
            return []

        items_per_host = {}
        for host in hosts:
            host_name = host['host']
            host_id = host['hostid']
            items = zapi.item.get(hostids=host_id, output="extend")
            if items:
                items_per_host[host_name] = {item['name']: item['itemid'] for item in items if item['name'] in ["CPU utilização", "Memória usada em %"]}
        logging.info(f"Total de hosts com itens filtrados: {len(items_per_host)}")
        return items_per_host
    except Exception as e:
        logging.error(f"Erro ao obter itens do Zabbix: {e}")
        return {}

def obter_historico_mes_passado(zapi, itemid):
    try:
        hoje = pd.Timestamp.today()

        primeiro_dia_mes_anterior = (hoje.replace(day=1) - pd.Timedelta(days=1)).replace(day=1)
        ultimo_dia_mes_anterior = hoje.replace(day=1) - pd.Timedelta(days=1)

        time_from = int(primeiro_dia_mes_anterior.timestamp())
        time_till = int(ultimo_dia_mes_anterior.timestamp())

        historico = zapi.history.get(
            itemids=itemid,
            time_from=time_from,
            time_till=time_till,
            output="extend",
            history=0,
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

def gerar_grafico_consolidado(zapi, itens_per_host, tipo_item, groupid):
    fig = go.Figure()

    for host_name, itens in itens_per_host.items():
        if tipo_item not in itens:
            continue

        itemid = itens[tipo_item]
        historico = obter_historico_mes_passado(zapi, itemid)

        if not historico:
            logging.warning(f"Nenhum dado encontrado para o item {tipo_item} do host {host_name}.")
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
                name=host_name
            ))

            fig.add_trace(go.Scatter(
                x=df.index[min_loc],
                y=df['Valor'].iloc[min_loc],
                mode='markers',
                marker=dict(color='green', size=8),
                name=f"{host_name} - Mínimos Locais"
            ))

            fig.add_trace(go.Scatter(
                x=df.index[max_loc],
                y=df['Valor'].iloc[max_loc],
                mode='markers',
                marker=dict(color='red', size=8),
                name=f"{host_name} - Máximos Locais"
            ))

        except KeyError as e:
            logging.error(f"Erro ao acessar chave nos dados de histórico para o item {tipo_item}: {e}")
            continue

    grafico_dir = f"graficos_{groupid}/{tipo_item.replace(' ', '_').lower()}"
    os.makedirs(grafico_dir, exist_ok=True)

    fig_path = os.path.join(grafico_dir, f"{tipo_item.replace(' ', '_').lower()}_consolidado.jpeg")
    fig.write_image(fig_path, format='jpeg')
    logging.info(f"Gráfico consolidado salvo em {fig_path}")
    return fig_path

@app.route('/gerar_grafico/<int:groupid>/<string:tipo_item>', methods=['GET'])
def gerar_grafico(groupid, tipo_item):
    zapi = conectar_zabbix()
    itens_per_host = obter_itens_do_grupo(zapi, groupid)
    fig_path = gerar_grafico_consolidado(zapi, itens_per_host, tipo_item, groupid)
   
    local_output_dir = "/home/tauge/Documentos/automacao/output"
    os.makedirs(local_output_dir, exist_ok=True)
    
    local_fig_path = os.path.join(local_output_dir, os.path.basename(fig_path))

    try:
        if os.path.exists(fig_path):
            os.rename(fig_path, local_fig_path)
            logging.info(f"Gráfico movido para {local_fig_path}")
            return send_file(local_fig_path, as_attachment=True)
        else:
            logging.error("Gráfico não encontrado no caminho gerado.")
            return jsonify({"erro": "Gráfico não encontrado."}), 404
    except Exception as e:
        logging.error(f"Erro ao mover ou baixar o gráfico: {e}")
        return jsonify({"erro": "Erro ao processar o gráfico."}), 500

if __name__ == '__main__':
    app.run(debug=True)
