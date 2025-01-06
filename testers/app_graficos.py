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

# Criar a pasta "output" se não existir
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

    # Diretório específico do tipo de gráfico
    grafico_dir = os.path.join(output_dir, f"grupo_{groupid}")
    os.makedirs(grafico_dir, exist_ok=True)

    fig_path = os.path.join(grafico_dir, f"{tipo_item.replace(' ', '_').lower()}_consolidado.jpeg")
    fig.write_image(fig_path, format='jpeg')
    logging.info(f"Gráfico consolidado salvo em {fig_path}")
    return fig_path

@app.route('/gerar_grafico/<int:groupid>', methods=['GET'])
def gerar_graficos_para_grupo(groupid):
    TIPOS_ITENS = ["CPU utilização", "Memória usada em %"]
    zapi = conectar_zabbix()

    # Obter itens do grupo
    itens_per_host = obter_itens_do_grupo(zapi, groupid)
    if not itens_per_host:
        logging.error(f"Nenhum host ou item encontrado para o grupo {groupid}.")
        return jsonify({"erro": f"Nenhum dado encontrado para o grupo {groupid}."}), 404

    graficos_gerados = []

    for tipo_item in TIPOS_ITENS:
        try:
            fig_path = gerar_grafico_consolidado(zapi, itens_per_host, tipo_item, groupid)
            graficos_gerados.append({"tipo_item": tipo_item, "caminho": fig_path})
        except Exception as e:
            logging.error(f"Erro ao gerar gráfico para {tipo_item}: {e}")
            continue

    if not graficos_gerados:
        return jsonify({"erro": "Nenhum gráfico foi gerado devido a problemas no processamento."}), 500

    return jsonify({
        "mensagem": f"Gráficos gerados com sucesso para o grupo {groupid}.",
        "graficos": graficos_gerados
    })


if __name__ == '__main__':
    app.run(debug=True)
