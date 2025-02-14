import os
import json
import logging
import requests
import time
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv

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

# Caminho para salvar os gráficos
OUTPUT_DIR = "/home/tauge/Documents/tauge/PGR/output/graphics"

def obter_hostid_do_json():
    try:
        with open('client_info.json', 'r') as file:
            return json.load(file)['idhostzbx']
    except Exception as e:
        logging.error(f"Erro ao ler client_info.json: {e}")
        raise

def listar_graficos_disponiveis(zapi, hostid):
    """Lista todos os gráficos disponíveis para o host."""
    try:
        graphs = zapi.graph.get(
            hostids=hostid,
            output=["name", "graphid"]
        )
        logging.info("Gráficos disponíveis:")
        for graph in graphs:
            logging.info(f"ID: {graph['graphid']}, Nome: {graph['name']}")
        return graphs
    except Exception as e:
        logging.error(f"Erro ao listar gráficos: {e}")
        raise

def baixar_grafico(zapi, graphid, graph_name):
    """Baixa um gráfico específico do Zabbix."""
    try:
        # Gera timestamps para os últimos 30 dias
        now = int(time.time())
        period_from = now - (30 * 86400)  # 30 dias em segundos

        # Parâmetros obrigatórios
        params = {
            "graphid": graphid,
            "width": 1200,
            "from": period_from,
            "to": now,
            "profile": "web"
        }

        # Configura a sessão com autenticação correta
        session = requests.Session()
        session.cookies['zbx_session'] = zapi.auth  # Cookie correto para Zabbix 7.x

        # URL do gráfico
        graph_url = f"{ZABBIX_URL.replace('api_jsonrpc.php', 'chart.php')}"

        # Faz o download
        response = session.get(graph_url, params=params)
        
        if response.status_code == 200:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            safe_name = "".join(c if c.isalnum() else "_" for c in graph_name)
            file_path = os.path.join(OUTPUT_DIR, f"{safe_name}.png")
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            logging.info(f"Gráfico salvo: {file_path}")
        else:
            logging.error(f"Erro HTTP {response.status_code}: {response.text}")

    except Exception as e:
        logging.error(f"Erro ao baixar {graph_name}: {str(e)}")
        raise

def gerar_grafico():
    try:
        zapi = ZabbixAPI(ZABBIX_URL)
        zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
        logging.info("Login realizado com sucesso")

        hostid = obter_hostid_do_json()
        graphs = listar_graficos_disponiveis(zapi, hostid)

        for graph in graphs:
            if any(keyword in graph['name'] for keyword in ['CPU', 'memória', 'RAM']):
                logging.info(f"Processando: {graph['name']}")
                baixar_grafico(zapi, graph['graphid'], graph['name'])

    except Exception as e:
        logging.error(f"Erro crítico: {str(e)}")
        print(f"Erro: {str(e)}")

if __name__ == '__main__':
    gerar_grafico()