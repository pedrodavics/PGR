import os
import json
import logging
import requests
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

# Carrega variáveis de ambiente
load_dotenv(dotenv_path='/home/tauge/Documents/tauge/PGR/.env')

# Configuração do log
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'zabbix.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configurações do Zabbix e diretórios de saída
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
    Gera listas de tick positions e labels a cada 12h.
    Se for meia-noite, label = 'MM-DD' (em #a64949);
    Caso contrário, label = 'hh:mm AM/PM' (em branco).
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
    Gera o gráfico com estilos customizados:
      - "CPU - utilização":
          * Todos os itens são plotados empilhados (stackgroup='cpu') com linha #00FF00,
            preenchimento cinza semi-transparente e nome de item exibido.
          * O eixo Y é fixo em 0..20% (como originalmente).
          * Eixo X com ticks a cada 12h.
          * Os nomes dos itens aparecem numa anotação no canto inferior esquerdo.
          * Uma seta branca (apontando para cima) é posicionada fora do gráfico no canto superior esquerdo.
          * Uma seta branca (apontando para a direita) é posicionada fora do gráfico no canto inferior direito,
            com tamanho semelhante à seta superior.
      - "Uso de memória":
          * Cada item é plotado individualmente (linha verde) e uma linha tracejada laranja é desenhada em 100%.
    """
    try:
        fig = go.Figure()
        nome_grafico = graph['name'].lower()
        periodo_dias = (dt_fim - dt_inicio).days

        if "cpu - utilização" in nome_grafico:
            usar_trend = (periodo_dias > 7)
            primeiro_item = True
            todos_nomes = []
            for item in graph['gitems']:
                itemid = item.get('itemid')
                if not itemid:
                    continue
                item_details = zapi.item.get(
                    itemids=itemid,
                    output=["name", "value_type"]
                )
                if not item_details:
                    continue
                nome_item = item_details[0].get("name", "")
                todos_nomes.append(nome_item)
                value_type = int(item_details[0].get('value_type', 0))
                if usar_trend:
                    data = zapi.trend.get(
                        itemids=itemid,
                        time_from=int(dt_inicio.timestamp()),
                        time_till=int(dt_fim.timestamp()),
                        output="extend",
                        sortfield="clock",
                        sortorder="ASC"
                    )
                    if not data:
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
                        continue
                    x_vals = [datetime.fromtimestamp(int(d['clock']), tz=timezone.utc) for d in data]
                    y_vals = [float(d['value']) for d in data]
                if not y_vals:
                    continue
                if primeiro_item:
                    fill_type = 'tozeroy'
                    primeiro_item = False
                else:
                    fill_type = 'tonexty'
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='lines',
                    name=nome_item,
                    line=dict(color='#00FF00', width=1),
                    fill=fill_type,
                    fillcolor='rgba(103,103,103,0.3)',
                    stackgroup='cpu'
                ))
            # Layout e eixos
            fig.update_layout(
                title=dict(
                    text="H.São Paulo - Oracle Prod: CPU utilização",
                    x=0.5,
                    y=0.93,
                    font=dict(color='white')
                )
            )
            tick_times, tick_labels = criar_ticks_personalizados(dt_inicio, dt_fim)
            fig.update_xaxes(
                tickmode='array',
                tickvals=tick_times,
                ticktext=[""] * len(tick_times),
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
            for t, label in zip(tick_times, tick_labels):
                cor = "#a64949" if (t.hour == 0) else "white"
                fig.add_annotation(
                    x=t,
                    y=-0.07,
                    xref="x",
                    yref="paper",
                    text=label,
                    showarrow=False,
                    font=dict(color=cor, size=10),
                    xanchor="center",
                    yanchor="top",
                    textangle=90
                )

            # Seta no canto superior esquerdo: a ponta da seta (apontando para cima)
            # O vértice está em (0, 1.04) e a base é definida de forma simétrica (0.00144 à direita e à esquerda)
            fig.add_shape(
                type="path",
                path="M 0,1.04 L 0.00144,1 L -0.00144,1 Z",
                fillcolor="white",
                line=dict(width=0),
                xref="paper",
                yref="paper"
            )

            # Seta no canto inferior direito: a ponta da seta (apontando para a direita)
            # O vértice está em (1.04, 0) e a base é definida com deslocamento vertical de ±0.00144
            fig.add_shape(
                type="path",
                path="M 1.0075,0 L 1.001,0.0125 L 1.001,-0.0125 Z",
                fillcolor="white",
                line=dict(width=0),
                xref="paper",
                yref="paper"
            )

        elif "uso de memória" in nome_grafico or "uso de memoria" in nome_grafico:
            fig.update_layout(title=dict(text=graph['name'], font=dict(color='white')))
            usar_trend = (periodo_dias > 7)
            for item in graph['gitems']:
                itemid = item.get('itemid')
                if not itemid:
                    continue
                item_details = zapi.item.get(
                    itemids=itemid,
                    output=["name", "value_type"]
                )
                if not item_details:
                    continue
                item_name = item_details[0].get('name', '')
                value_type = int(item_details[0].get('value_type', 0))
                if usar_trend:
                    data = zapi.trend.get(
                        itemids=itemid,
                        time_from=int(dt_inicio.timestamp()),
                        time_till=int(dt_fim.timestamp()),
                        output="extend",
                        sortfield="clock",
                        sortorder="ASC"
                    )
                    if not data:
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
                        continue
                    x_vals = [datetime.fromtimestamp(int(d['clock']), tz=timezone.utc) for d in data]
                    y_vals = [float(d['value']) for d in data]
                if not y_vals:
                    continue
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='lines',
                    name=item_name,
                    line=dict(color='#00FF00', width=2)
                ))
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

        fig.update_layout(
            width=1638,
            height=368,
            paper_bgcolor='#1f2124',
            plot_bgcolor='#393d42',
            font=dict(color='white'),
            legend=dict(
                font=dict(color='white'),
                orientation='h',
                x=-0.02,
                y=-0.3,
                xanchor='left',
                yanchor='top'
            ),
            margin=dict(l=80, r=50, t=70, b=90)
        )

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
