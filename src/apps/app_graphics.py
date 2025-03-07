import os
import json
import logging
import requests
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

# Carrega variáveis de ambiente do arquivo .env
load_dotenv(dotenv_path='/home/tauge/Documents/tauge/PGR/.env')

# Configuração de logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'zabbix.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configurações do Zabbix e diretório de saída
ZABBIX_URL = os.getenv("URL_ZBX")
ZABBIX_USER = os.getenv("USER_ZBX")
ZABBIX_PASSWORD = os.getenv("PASS_ZBX")
OUTPUT_DIR = "/home/tauge/Documents/tauge/PGR/output/graphics"

### Funções Auxiliares

def obter_hostid_do_json():
    """Obtém o hostid do Zabbix a partir de um arquivo JSON."""
    try:
        with open('client_info.json', 'r') as file:
            return json.load(file)['idhostzbx']
    except Exception as e:
        logging.error(f"Erro ao ler client_info.json: {e}")
        raise

def validar_url_zabbix():
    """Valida e corrige a URL do Zabbix para incluir '/api_jsonrpc.php'."""
    parsed = urlparse(ZABBIX_URL)
    if not parsed.path.endswith('/api_jsonrpc.php'):
        new_path = parsed.path.rstrip('/') + '/api_jsonrpc.php'
        return parsed._replace(path=new_path).geturl()
    return ZABBIX_URL

def criar_ticks_personalizados(dt_inicio, dt_fim):
    """
    Gera posições e rótulos de ticks a cada 12 horas.
    - Meia-noite: 'MM-DD' (cor #a64949)
    - Outros horários: 'hh:mm AM/PM' (branco)
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

### Função Principal de Geração de Gráficos

def generate_plotly_graph(zapi, graph, dt_inicio, dt_fim):
    """Gera gráficos Plotly para CPU e memória com tratamento de lacunas."""
    try:
        fig = go.Figure()
        nome_grafico = graph['name'].lower()
        periodo_dias = (dt_fim - dt_inicio).days
        usar_trend = (periodo_dias > 7)

        # Define threshold para detectar lacunas nos dados
        threshold = timedelta(hours=2) if usar_trend else timedelta(minutes=10)

        # **Gráfico de CPU - Utilização**
        if "cpu - utilização" in nome_grafico:
            scale_factor_cpu = 1.5
            primeiro_item = True

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
                value_type = int(item_details[0].get('value_type', 0))

                # Obtém dados (trend ou history)
                if usar_trend:
                    data = zapi.trend.get(
                        itemids=itemid,
                        time_from=int(dt_inicio.timestamp()),
                        time_till=int(dt_fim.timestamp()),
                        output="extend",
                        sortfield="clock",
                        sortorder="ASC"
                    )
                    x_vals = [datetime.fromtimestamp(int(d['clock']), tz=timezone.utc) for d in data]
                    y_vals = [float(d['value_avg']) * scale_factor_cpu for d in data]
                else:
                    data = zapi.history.get(
                        history=value_type,
                        itemids=itemid,
                        time_from=int(dt_inicio.timestamp()),
                        time_till=int(dt_fim.timestamp()),
                        sortfield="clock",
                        sortorder="ASC"
                    )
                    x_vals = [datetime.fromtimestamp(int(d['clock']), tz=timezone.utc) for d in data]
                    y_vals = [float(d['value']) * scale_factor_cpu for d in data]

                if not y_vals:
                    continue

                # Divide em segmentos contínuos
                segments = []
                current_segment = {'x': [], 'y': []}
                for i in range(len(x_vals)):
                    if i > 0 and (x_vals[i] - x_vals[i-1]) > threshold:
                        segments.append(current_segment)
                        current_segment = {'x': [], 'y': []}
                    current_segment['x'].append(x_vals[i])
                    current_segment['y'].append(y_vals[i])
                if current_segment['x']:
                    segments.append(current_segment)

                fill_type = 'tozeroy' if primeiro_item else 'tonexty'
                primeiro_item = False

                for seg in segments:
                    fig.add_trace(go.Scatter(
                        x=seg['x'],
                        y=seg['y'],
                        mode='lines',
                        name=nome_item if seg == segments[0] else "",
                        line=dict(color='#00FF00', width=1),
                        fill=fill_type,
                        fillcolor='rgba(103,103,103,0.3)',
                        stackgroup='cpu',
                        showlegend=(seg == segments[0])
                    ))

            # Configura layout do gráfico de CPU
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
                ticklabelstandoff=20,
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

            # Adiciona setas ao gráfico
            fig.add_shape(type="path", path="M 0,1.04 L 0.00144,1 L -0.00144,1 Z", fillcolor="white", line=dict(width=0), xref="paper", yref="paper")
            fig.add_shape(type="path", path="M 1.0075,0 L 1.001,0.0125 L 1.001,-0.0125 Z", fillcolor="white", line=dict(width=0), xref="paper", yref="paper")

        # **Gráfico de Uso de Memória**
        elif "uso de memória" in nome_grafico or "uso de memoria" in nome_grafico:
            primeiro_item_mem = True
            all_memory_values = []

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

                # Obtém dados (trend ou history)
                if usar_trend:
                    data = zapi.trend.get(
                        itemids=itemid,
                        time_from=int(dt_inicio.timestamp()),
                        time_till=int(dt_fim.timestamp()),
                        output="extend",
                        sortfield="clock",
                        sortorder="ASC"
                    )
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
                    x_vals = [datetime.fromtimestamp(int(d['clock']), tz=timezone.utc) for d in data]
                    y_vals = [float(d['value']) for d in data]

                if not y_vals:
                    continue

                all_memory_values.extend(y_vals)

                # Divide em segmentos contínuos
                segments = []
                current_segment = {'x': [], 'y': []}
                for i in range(len(x_vals)):
                    if i > 0 and (x_vals[i] - x_vals[i-1]) > threshold:
                        segments.append(current_segment)
                        current_segment = {'x': [], 'y': []}
                    current_segment['x'].append(x_vals[i])
                    current_segment['y'].append(y_vals[i])
                if current_segment['x']:
                    segments.append(current_segment)

                fill_type = 'tozeroy' if primeiro_item_mem else 'tonexty'
                primeiro_item_mem = False

                for seg in segments:
                    fig.add_trace(go.Scatter(
                        x=seg['x'],
                        y=seg['y'],
                        mode='lines',
                        name=item_name if seg == segments[0] else "",
                        line=dict(color='#00FF00', width=1),
                        fill=fill_type,
                        fillcolor='rgba(103,103,103,0.3)',
                        stackgroup='memory',
                        showlegend=(seg == segments[0])
                    ))

            # Linha tracejada em 100%
            fig.add_shape(type="line", xref="paper", yref="y", x0=0, x1=1, y0=100, y1=100, line=dict(color="orange", width=2, dash="dot"))

            # Configura layout do gráfico de memória
            fig.update_layout(
                title=dict(
                    text="H.São Paulo - Oracle Prod: Memória usada em %",
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

            # Adiciona setas ao gráfico
            fig.add_shape(type="path", path="M 0,1.04 L 0.00144,1 L -0.00144,1 Z", fillcolor="white", line=dict(width=0), xref="paper", yref="paper")
            fig.add_shape(type="path", path="M 1.0075,0 L 1.001,0.0125 L 1.001,-0.0125 Z", fillcolor="white", line=dict(width=0), xref="paper", yref="paper")

            # Configura eixo Y dinamicamente
            if all_memory_values:
                y_min_val = min(all_memory_values)
                y_max_val = max(all_memory_values)
                percent_ticks = [50, 60, 70, 80, 90, 100]
                tickvals = []
                ticktext = []
                for p in percent_ticks:
                    mapped_val = y_min_val + ((p - 50) / 50) * (y_max_val - y_min_val)
                    tickvals.append(mapped_val)
                    ticktext.append(f"{p}%")
                fig.update_yaxes(
                    tickmode='array',
                    tickvals=tickvals,
                    ticktext=ticktext,
                    range=[y_min_val, y_max_val],
                    showgrid=True,
                    gridcolor='gray',
                    griddash="dot",
                    gridwidth=1,
                    linecolor='gray',
                    mirror=True
                )
            else:
                fig.update_yaxes(
                    showgrid=True,
                    gridcolor='gray',
                    griddash="dot",
                    gridwidth=1,
                    linecolor='gray',
                    mirror=True
                )

        # **Layout Geral**
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

        # Salva o gráfico
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if "cpu - utilização" in nome_grafico:
            file_name = "CPU___utilizacao_plotly.png"
        elif "uso de memória" in nome_grafico or "uso de memoria" in nome_grafico:
            file_name = "Uso_de_memoria_plotly.png"
        else:
            safe_name = "".join([c if c.isalnum() else "_" for c in graph['name']])
            file_name = f"{safe_name}_plotly.png"

        file_path = os.path.join(OUTPUT_DIR, file_name)
        fig.write_image(file_path)
        logging.info(f"Gráfico Plotly salvo: {file_path}")

    except Exception as e:
        logging.error(f"Falha ao gerar gráfico Plotly para '{graph['name']}': {str(e)}")

### Função de Processamento

def processar_graficos():
    """Conecta ao Zabbix e processa os gráficos de CPU e memória."""
    try:
        zapi = ZabbixAPI(validar_url_zabbix())
        zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
        logging.info("Autenticação API realizada com sucesso.")
        hostid = obter_hostid_do_json()

        # Obtém os gráficos do host
        graphs = zapi.graph.get(
            hostids=hostid,
            output=["name", "graphid"],
            selectGraphItems="extend"
        )

        # Filtra gráficos relevantes
        graphs_relevantes = [
            g for g in graphs
            if ('CPU - utilização' in g['name']) or ('Uso de memória' in g['name'])
        ]
        if not graphs_relevantes:
            logging.error("Nenhum gráfico relevante encontrado (CPU - utilização / Uso de memória).")
            return

        # Define período de 30 dias
        dt_fim = datetime.now(timezone.utc)
        dt_inicio = dt_fim - timedelta(days=30)
        dt_inicio = dt_inicio.replace(hour=0, minute=0, second=0, microsecond=0)

        # Gera os gráficos
        for graph in graphs_relevantes:
            generate_plotly_graph(zapi, graph, dt_inicio, dt_fim)

    except Exception as e:
        logging.error(f"Erro crítico: {str(e)}")
        print(f"Erro: {str(e)}")

### Execução

if __name__ == '__main__':
    processar_graficos()