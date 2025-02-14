import os
import time
import json
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from dotenv import load_dotenv
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(filename='logs/zabbix.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

zabbix_url = os.getenv("URL_ZBX")
zabbix_user = os.getenv("USER_ZBX")
zabbix_pass = os.getenv("PASS_ZBX")
zabbix_auth = os.getenv("AUTH_ZBX")

def load_host_id():
    """Carregar o ID do host do arquivo client_info.json"""
    try:
        with open("client_info.json", "r") as f:
            return json.load(f).get("idhostzbx")
    except Exception as e:
        logging.error(f"Error loading client_info.json: {e}")
        return None

class ZabbixAPI:
    def __init__(self, url, user, password, auth_token=None):
        self.url = url
        self.user = user
        self.password = password
        self.auth_token = auth_token

    def connect(self):
        """Conectar à API do Zabbix e obter o token de autenticação"""
        if not self.auth_token:
            self.auth_token = os.getenv("AUTH_ZBX")
            if not self.auth_token:
                raise ValueError("Auth token is not provided.")
        logging.info(f"Using Auth Token: {self.auth_token}")

    def _post_request(self, data):
        """Método para enviar requisições POST para a API Zabbix"""
        try:
            response = requests.post(self.url, json=data, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Request error: {e}")
            raise

    def get_host_items(self, host_id):
        """Obter itens do host via Zabbix API"""
        data = {
            "jsonrpc": "2.0",
            "method": "item.get",
            "params": {"hostids": host_id, "output": "extend"},
            "auth": self.auth_token,
            "id": 1
        }
        return self._post_request(data).get("result", [])


class GraphGenerator:
    def __init__(self, zabbix_api):
        self.zabbix_api = zabbix_api

    def generate_graph(self, host_name, item_type, history_data):
        """Gerar gráfico a partir dos dados históricos do Zabbix"""
        df = self.prepare_data(history_data)
        if df.empty:
            logging.warning(f"Insufficient data for {item_type} on host {host_name}.")
            return

        min_loc, max_loc = self.get_local_extrema(df)
        fig = self.create_figure(df, min_loc, max_loc, host_name, item_type)
        self.save_graph(fig, item_type)

    def prepare_data(self, history_data):
        """Preparar os dados para o gráfico"""
        timestamps = [int(i['clock']) for i in history_data]
        values = [float(i['value']) for i in history_data]
        dates = [time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)) for ts in timestamps]
        df = pd.DataFrame({'DateTime': pd.to_datetime(dates), 'Value': values})
        return df.sort_values('DateTime').set_index('DateTime').resample('D').mean().dropna()

    def get_local_extrema(self, df):
        """Obter os extremos locais de mínimo e máximo"""
        min_loc = argrelextrema(df['Value'].values, np.less)[0]
        max_loc = argrelextrema(df['Value'].values, np.greater)[0]
        return min_loc, max_loc

    def create_figure(self, df, min_loc, max_loc, host_name, item_type):
        """Criar o gráfico com os dados e marcar os extremos locais"""
        fig = go.Figure()
        fig.update_layout(template="plotly_dark")
        fig.add_trace(go.Scatter(x=df.index, y=df['Value'], mode='lines', name=host_name))
        fig.add_trace(go.Scatter(x=df.index[min_loc], y=df['Value'].iloc[min_loc], mode='markers', marker=dict(color='green', size=8), name=f"{host_name} - Min Local"))
        fig.add_trace(go.Scatter(x=df.index[max_loc], y=df['Value'].iloc[max_loc], mode='markers', marker=dict(color='red', size=8), name=f"{host_name} - Max Local"))
        return fig

    def save_graph(self, fig, item_type):
        """Salvar o gráfico gerado como imagem"""
        os.makedirs("output/images", exist_ok=True)
        img_name = "grafico_cpu.jpeg" if "CPU" in item_type else "grafico_memoria.jpeg"
        fig.write_image(os.path.join("output/images", img_name), format='jpeg')
        logging.info(f"Graph saved as {img_name}")


def fetch_and_generate_graph(zabbix_api, host_name, items, item_type, time_from, time_till):
    """Buscar dados históricos e gerar gráfico em paralelo"""
    itemid = items.get(item_type)
    if itemid:
        history_data = zabbix_api.get_history(itemid, time_from, time_till, 3)  
        if history_data:
            graph_generator = GraphGenerator(zabbix_api)
            graph_generator.generate_graph(host_name, item_type, history_data)


def get_time_range():
    """Obter o intervalo de tempo para a consulta de dados históricos"""
    today = pd.Timestamp.today()
    first_day_last_month = (today.replace(day=1) - pd.Timedelta(days=1)).replace(day=1)
    time_from = int(first_day_last_month.timestamp())
    time_till = int(time.time())
    return time_from, time_till


def main():
    """Função principal para conectar à API Zabbix e gerar gráficos"""
    zabbix_api = ZabbixAPI(zabbix_url, zabbix_user, zabbix_pass, zabbix_auth) 
    zabbix_api.connect()

    host_id = load_host_id()
    if not host_id:
        logging.error("Host ID not found in JSON file.")
        return

    host_info = zabbix_api.get_host_items(host_id)
    time_from, time_till = get_time_range()

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(fetch_and_generate_graph, zabbix_api, "HostName", host_info, item_type, time_from, time_till)
            for item_type in ["CPU utilização", "Memória usada em %"] if item_type in host_info
        ]
        for future in futures:
            future.result()


if __name__ == '__main__':
    main() 
