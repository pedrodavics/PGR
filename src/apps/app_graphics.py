import os
import json
import logging
import requests
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

# Carrega as variáveis de ambiente
load_dotenv(dotenv_path='/home/tauge/Documents/tauge/PGR/.env')

# Configuração do log
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'zabbix.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configurações do Zabbix
ZABBIX_URL = os.getenv("URL_ZBX")
ZABBIX_USER = os.getenv("USER_ZBX")
ZABBIX_PASSWORD = os.getenv("PASS_ZBX")
OUTPUT_DIR = "/home/tauge/Documents/tauge/PGR/output/graphics"

def obter_hostid_do_json():
    try:
        with open('client_info.json', 'r') as file:
            return json.load(file)['idhostzbx']
    except Exception as e:
        logging.error(f"Erro ao ler client_info.json: {e}")
        raise

def validar_url_zabbix():
    parsed = urlparse(ZABBIX_URL)
    if not parsed.path.endswith('/api_jsonrpc.php'):
        new_path = parsed.path.rstrip('/') + '/api_jsonrpc.php'
        return parsed._replace(path=new_path).geturl()
    return ZABBIX_URL

def get_periodo_30_dias():
    hoje = datetime.now(timezone.utc)
    inicio = hoje - timedelta(days=30)
    return inicio, hoje

def generate_plotly_graph(zapi, graph, dt_inicio, dt_fim):
    try:
        fig = go.Figure()
        # Verifica se o gráfico possui os itens associados (gitems)
        if 'gitems' not in graph:
            logging.error(f"Gráfico '{graph['name']}' não possui itens associados (gitems).")
            return

        # Para cada item do gráfico, coleta os dados do período
        for item in graph['gitems']:
            itemid = item.get('itemid')
            if not itemid:
                continue

            # Recupera detalhes do item
            item_details = zapi.item.get(
                itemids=itemid,
                output=["name", "value_type"]
            )
            if not item_details:
                logging.error(f"Item {itemid} não encontrado para o gráfico '{graph['name']}'.")
                continue

            item_detail = item_details[0]
            value_type = int(item_detail.get('value_type'))
            item_name = item_detail.get('name')

            # Define o tipo de histórico a ser consultado com base no value_type (0 = float, 3 = unsigned)
            history_type = value_type

            # Se o período for maior que 7 dias, utiliza trend (dados agregados) em vez de history
            periodo_dias = (dt_fim - dt_inicio).days
            if periodo_dias > 7:
                # Coleta dados de trends utilizando o método correto "trend.get"
                data = zapi.trend.get(
                    itemids=itemid,
                    time_from=int(dt_inicio.timestamp()),
                    time_till=int(dt_fim.timestamp()),
                    output="extend",
                    sortfield="clock",
                    sortorder="ASC"
                )
                if not data:
                    logging.warning(f"Sem dados de trend para o item '{item_name}' no gráfico '{graph['name']}'.")
                    continue
                x_vals = [datetime.fromtimestamp(int(point['clock']), tz=timezone.utc) for point in data]
                y_vals = [float(point['value_avg']) for point in data]
                logging.info(f"Dados de trend coletados para o item '{item_name}' do gráfico '{graph['name']}' com {len(x_vals)} pontos.")
            else:
                # Coleta dados históricos (history)
                data = zapi.history.get(
                    history=history_type,
                    itemids=itemid,
                    time_from=int(dt_inicio.timestamp()),
                    time_till=int(dt_fim.timestamp()),
                    sortfield="clock",
                    sortorder="ASC"
                )
                if not data:
                    logging.warning(f"Sem dados de history para o item '{item_name}' no gráfico '{graph['name']}'.")
                    continue
                x_vals = [datetime.fromtimestamp(int(point['clock']), tz=timezone.utc) for point in data]
                y_vals = [float(point['value']) for point in data]
                logging.info(f"Dados de history coletados para o item '{item_name}' do gráfico '{graph['name']}' com {len(x_vals)} pontos.")

            # Configura a cor do item (assegurando que esteja no formato hexadecimal)
            color = item.get('color', 'FFFFFF')
            if not color.startswith('#'):
                color = '#' + color

            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines',
                name=item_name,
                line=dict(color=color)
            ))

        # Configuração do layout para deixar o fundo preto, similar ao Zabbix
        fig.update_layout(
            title=graph['name'],
            paper_bgcolor='black',
            plot_bgcolor='black',
            font=dict(color='white'),
            xaxis=dict(title='Tempo', gridcolor='gray'),
            yaxis=dict(title='Valor', gridcolor='gray'),
            legend=dict(font=dict(color='white'))
        )

        # Salva o gráfico gerado pelo Plotly como PNG
        safe_name = "".join([c if c.isalnum() else "_" for c in graph['name']])
        file_path = os.path.join(OUTPUT_DIR, f"{safe_name}_plotly.png")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        fig.write_image(file_path)
        logging.info(f"Gráfico Plotly salvo: {file_path}")

    except Exception as e:
        logging.error(f"Falha ao gerar gráfico Plotly para '{graph['name']}': {str(e)}")

def processar_graficos():
    try:
        # Autentica na API do Zabbix
        zapi = ZabbixAPI(validar_url_zabbix())
        zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
        logging.info("Autenticação API realizada com sucesso.")

        hostid = obter_hostid_do_json()
        
        # Obtém os gráficos do host, incluindo os itens associados (gitems)
        graphs = zapi.graph.get(
            hostids=hostid,
            output=["name", "graphid"],
            selectGraphItems="extend"
        )
        
        # Filtra os gráficos relevantes (por exemplo, CPU e memória)
        graphs_relevantes = [
            g for g in graphs 
            if any(kw in g['name'] for kw in ['CPU - utilização', 'memória'])
        ]
        
        if not graphs_relevantes:
            logging.error("Nenhum gráfico relevante encontrado.")
            return

        # Define o período de 30 dias (início alinhado ao começo do dia UTC)
        dt_fim = datetime.now(timezone.utc)
        dt_inicio = dt_fim - timedelta(days=30)
        dt_inicio = dt_inicio.replace(hour=0, minute=0, second=0, microsecond=0)

        # Gera o gráfico para cada gráfico relevante usando Plotly
        for graph in graphs_relevantes:
            generate_plotly_graph(zapi, graph, dt_inicio, dt_fim)

    except Exception as e:
        logging.error(f"Erro crítico: {str(e)}")
        print(f"Erro: {str(e)}")

if __name__ == '__main__':
    processar_graficos()
