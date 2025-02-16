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

def criar_ticks_personalizados(dt_inicio, dt_fim):
    """
    Cria ticks a cada 12h para o eixo X.
    Se for meia-noite, formata como 'MM-DD';
    Caso contrário, formata como 'hh:mm AM/PM'.
    """
    tick_times = []
    tick_labels = []
    atual = dt_inicio
    while atual <= dt_fim:
        tick_times.append(atual)
        if atual.hour == 0:
            label = atual.strftime('%m-%d')
        else:
            label = atual.strftime('%I:%M %p')
        tick_labels.append(label)
        atual += timedelta(hours=12)
    return tick_times, tick_labels

def generate_plotly_graph(zapi, graph, dt_inicio, dt_fim):
    """
    Gera o gráfico com estilo diferenciado para:
      - "CPU - utilização": área fill com opacidade baixa, eixos customizados, fundo da imagem cinza,
        grid pontilhado e ticks a cada 12h.
      - "Uso de memória": linha verde sem fill e linha tracejada laranja em 100%.
    """
    try:
        fig = go.Figure()

        if 'gitems' not in graph:
            logging.error(f"Gráfico '{graph['name']}' não possui itens associados (gitems).")
            return

        nome_grafico = graph['name'].lower()
        periodo_dias = (dt_fim - dt_inicio).days

        for item in graph['gitems']:
            itemid = item.get('itemid')
            if not itemid:
                continue

            item_details = zapi.item.get(
                itemids=itemid,
                output=["name", "value_type"]
            )
            if not item_details:
                logging.error(f"Item {itemid} não encontrado em '{graph['name']}'.")
                continue

            item_detail = item_details[0]
            item_name = item_detail.get('name')
            value_type = int(item_detail.get('value_type'))

            if periodo_dias > 7:
                data = zapi.trend.get(
                    itemids=itemid,
                    time_from=int(dt_inicio.timestamp()),
                    time_till=int(dt_fim.timestamp()),
                    output="extend",
                    sortfield="clock",
                    sortorder="ASC"
                )
                if not data:
                    logging.warning(f"Sem dados de trend para '{item_name}' em '{graph['name']}'.")
                    continue
                x_vals = [datetime.fromtimestamp(int(d['clock']), tz=timezone.utc) for d in data]
                y_vals = [float(d['value_avg']) for d in data]
            else:
                data = zapi.history.get(
                    history=value_type,
                    itemids=itemid,
                    time_from=int(dt_inicio.timestamp()),
                    time_till=int(dt_fim.timestamp()),
                    sortfield="clock",
                    sortorder="ASC"
                )
                if not data:
                    logging.warning(f"Sem dados de history para '{item_name}' em '{graph['name']}'.")
                    continue
                x_vals = [datetime.fromtimestamp(int(d['clock']), tz=timezone.utc) for d in data]
                y_vals = [float(d['value']) for d in data]

            if not y_vals:
                continue

            # Para CPU - utilização, aplica área fill com baixa opacidade
            if "cpu - utilização" in nome_grafico:
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='lines',
                    name=item_name,
                    line=dict(color='#00FF00', width=1),
                    fill='tozeroy',
                    fillcolor='rgba(0,255,0,0.2)'
                ))
            # Para Uso de memória, mantém linha verde sem fill
            elif "uso de memória" in nome_grafico or "uso de memoria" in nome_grafico:
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='lines',
                    name=item_name,
                    line=dict(color='#00FF00', width=2)
                ))

        # Estilos e configurações específicas para CPU - utilização
        if "cpu - utilização" in nome_grafico:
            fig.update_layout(
                title=dict(
                    text="H.São Paulo - Oracle Prod: CPU utilização",
                    x=0.5,
                    y=0.93
                )
            )
            tick_times, tick_labels = criar_ticks_personalizados(dt_inicio, dt_fim)
            fig.update_xaxes(
                tickmode='array',
                tickvals=tick_times,
                ticktext=tick_labels,
                range=[dt_inicio, dt_fim],
                showgrid=True,
                gridcolor='gray',
                griddash="dot",
                gridwidth=1,
                linecolor='gray',
                mirror=True
            )
            fig.update_yaxes(
                range=[0, 20],
                dtick=5,
                ticksuffix='%',
                showgrid=True,
                gridcolor='gray',
                griddash="dot",
                gridwidth=1,
                linecolor='gray',
                mirror=True
            )
        # Configurações para Uso de memória
        elif "uso de memória" in nome_grafico or "uso de memoria" in nome_grafico:
            fig.update_layout(title=graph['name'])
            fig.add_shape(
                type="line",
                xref="paper", yref="y",
                x0=0, x1=1,
                y0=100, y1=100,
                line=dict(color="orange", width=2, dash="dot")
            )
            fig.update_xaxes(
                showgrid=True,
                gridcolor='gray',
                griddash="dot",
                gridwidth=1,
                linecolor='gray'
            )
            fig.update_yaxes(
                showgrid=True,
                gridcolor='gray',
                griddash="dot",
                gridwidth=1,
                linecolor='gray'
            )

        # Define dimensões e fundo geral (imagem cinza)
        fig.update_layout(
            width=1980,
            height=720,
            paper_bgcolor='gray',
            plot_bgcolor='gray',
            font=dict(color='white'),
            legend=dict(
                font=dict(color='white'),
                orientation='h',
                x=0,
                y=1.05
            ),
            margin=dict(l=80, r=50, t=70, b=50)
        )

        # Removemos qualquer anotação extra que possa interferir
        # (não adicionamos nenhuma annotation com métricas)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        safe_name = "".join([c if c.isalnum() else "_" for c in graph['name']])
        file_path = os.path.join(OUTPUT_DIR, f"{safe_name}_plotly.png")
        fig.write_image(file_path)
        logging.info(f"Gráfico Plotly salvo: {file_path}")

    except Exception as e:
        logging.error(f"Falha ao gerar gráfico Plotly para '{graph['name']}': {str(e)}")

def processar_graficos():
    try:
        zapi = ZabbixAPI(validar_url_zabbix())
        zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
        logging.info("Autenticação API realizada com sucesso.")

        hostid = obter_hostid_do_json()

        graphs = zapi.graph.get(
            hostids=hostid,
            output=["name", "graphid"],
            selectGraphItems="extend"
        )

        # Filtra somente os gráficos "CPU - utilização" e "Uso de memória"
        graphs_relevantes = [
            g for g in graphs 
            if ('CPU - utilização' in g['name']) or ('Uso de memória' in g['name'])
        ]

        if not graphs_relevantes:
            logging.error("Nenhum gráfico relevante encontrado (CPU - utilização / Uso de memória).")
            return

        dt_fim = datetime.now(timezone.utc)
        dt_inicio = dt_fim - timedelta(days=30)
        dt_inicio = dt_inicio.replace(hour=0, minute=0, second=0, microsecond=0)

        for graph in graphs_relevantes:
            generate_plotly_graph(zapi, graph, dt_inicio, dt_fim)

    except Exception as e:
        logging.error(f"Erro crítico: {str(e)}")
        print(f"Erro: {str(e)}")

if __name__ == '__main__':
    processar_graficos()
