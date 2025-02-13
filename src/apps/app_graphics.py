import os
import time
import json
import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from flask import Flask, send_file, jsonify
from dotenv import load_dotenv
from scipy.signal import argrelextrema

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do log
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'zabbix.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Configuração do Zabbix (obtida via .env)
zabbix_url = os.getenv("URL_ZBX")            # Ex.: "https://seuzabbix.com/zabbix/api_jsonrpc.php"
zabbix_user = os.getenv("USER_ZBX")            # Seu usuário de API
zabbix_password = os.getenv("PASS_ZBX")        # Sua senha

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

# Função para efetuar o login via API JSON-RPC do Zabbix
def login_zabbix():
    try:
        headers = {"Content-Type": "application/json-rpc"}
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "user": zabbix_user,
                "password": zabbix_password
            },
            "id": 1,
            "auth": None
        }
        response = requests.post(zabbix_url, headers=headers, data=json.dumps(payload))
        result = response.json()
        if "error" in result:
            logging.error(f"Erro ao efetuar login: {result['error']}")
            raise Exception(f"Erro no login: {result['error']}")
        token = result.get("result")
        logging.info("Login efetuado com sucesso. Token obtido.")
        return token
    except Exception as e:
        logging.error(f"Erro ao efetuar login no Zabbix: {e}")
        raise

# Função auxiliar para chamadas à API JSON-RPC do Zabbix
def zabbix_api(method, params, auth_token):
    try:
        headers = {"Content-Type": "application/json-rpc"}
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
            "auth": auth_token
        }
        response = requests.post(zabbix_url, headers=headers, data=json.dumps(payload))
        result = response.json()
        if "error" in result:
            logging.error(f"Erro na chamada da API {method}: {result['error']}")
            raise Exception(f"Erro na chamada da API {method}: {result['error']}")
        return result.get("result")
    except Exception as e:
        logging.error(f"Erro ao chamar a API {method}: {e}")
        raise

# Obtém os itens do host filtrando por itens relacionados à "CPU" ou "memória"
def obter_itens_do_host(auth_token, hostid):
    try:
        params = {
            "output": "extend",
            "hostids": hostid
        }
        items = zabbix_api("item.get", params, auth_token)
        if not items:
            logging.warning(f"Nenhum item encontrado para o host {hostid}.")
            return {}
        # Filtra itens cujo nome contenha "CPU" ou "memória"
        items_per_host = {item['name']: item['itemid'] for item in items if "CPU" in item['name'] or "memória" in item['name']}
        logging.info(f"Itens encontrados para o host {hostid}: {list(items_per_host.keys())}")
        return items_per_host
    except Exception as e:
        logging.error(f"Erro ao obter itens do host {hostid}: {e}")
        return {}

# Obtém o histórico dos últimos 90 dias para um item (ajuste o período se necessário)
def obter_historico_ultimos_90_dias(auth_token, itemid):
    try:
        hoje = pd.Timestamp.today()
        time_from = int((hoje - pd.Timedelta(days=90)).timestamp())
        time_till = int(hoje.timestamp())
        params = {
            "output": "extend",
            "itemids": itemid,
            "time_from": time_from,
            "time_till": time_till,
            "history": 3,  # Ajuste conforme o tipo de dado do item (0,3, etc.)
            "sortfield": "clock",
            "sortorder": "ASC",
            "limit": 100000
        }
        historico = zabbix_api("history.get", params, auth_token)
        if not historico:
            logging.warning(f"Nenhum histórico encontrado para o item {itemid}.")
        return historico
    except Exception as e:
        logging.error(f"Erro ao obter histórico do item {itemid}: {e}")
        return []

# Gera o gráfico consolidado para os itens do host
def gerar_grafico_consolidado(auth_token, itens_per_host, hostid):
    fig = go.Figure()

    for item_name, itemid in itens_per_host.items():
        historico = obter_historico_ultimos_90_dias(auth_token, itemid)
        if not historico:
            logging.warning(f"Nenhum dado encontrado para o item {item_name} do host {hostid}.")
            continue
        try:
            timestamps = [int(i['clock']) for i in historico]
            valores = [float(i['value']) for i in historico]
            datas = [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)) for ts in timestamps]
            df = pd.DataFrame({'DataHora': pd.to_datetime(datas), 'Valor': valores})
            df = df.sort_values('DataHora').set_index('DataHora').resample('D').mean().dropna()

            # Identifica mínimos e máximos locais
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
            logging.error(f"Erro ao acessar dados históricos para o item {item_name}: {e}")
            continue
# Diretório de saída os gráficos
    output_dir = 'output/images'
    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, "cpu_memoria.jpeg")
    fig.write_image(fig_path, format='jpeg', engine='kaleido')
    logging.info(f"Gráfico consolidado salvo em {fig_path}")
    return fig_path

# Endpoint para gerar o gráfico
@app.route('/gerar_grafico', methods=['GET'])
def gerar_grafico():
    try:
        hostid = obter_hostid_do_json()
        auth_token = login_zabbix()
        itens_per_host = obter_itens_do_host(auth_token, hostid)
        fig_path = gerar_grafico_consolidado(auth_token, itens_per_host, hostid)
        if os.path.exists(fig_path):
            return send_file(fig_path, as_attachment=True)
        return jsonify({"erro": "Gráfico não encontrado."}), 404
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico: {e}")
        return jsonify({"erro": "Erro ao gerar gráfico."}), 500

if __name__ == '__main__':
    with app.app_context():
        gerar_grafico()
