
import os
import json
import logging
import requests
import time
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

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
    """Garante que a URL do Zabbix está correta"""
    parsed = urlparse(ZABBIX_URL)
    if not parsed.path.endswith('/api_jsonrpc.php'):
        new_path = parsed.path.rstrip('/') + '/api_jsonrpc.php'
        return parsed._replace(path=new_path).geturl()
    return ZABBIX_URL

def criar_sessao_web():
    """Cria sessão autenticada via login web"""
    try:
        session = requests.Session()
        login_url = ZABBIX_URL.replace('api_jsonrpc.php', 'index.php')
        
        # Dados de login
        login_data = {
            'name': ZABBIX_USER,
            'password': ZABBIX_PASSWORD,
            'enter': 'Sign in'
        }
        
        # Headers para simular navegador
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Referer': login_url
        })
        
        # Faz login
        response = session.post(login_url, data=login_data, verify=False)
        response.raise_for_status()
        
        if 'sign in' in response.text.lower():
            raise Exception("Falha na autenticação web")
            
        return session
    except Exception as e:
        logging.error(f"Erro de autenticação web: {str(e)}")
        raise

def get_periodo_30_dias():
    """Retorna período de 30 dias em timestamps UNIX"""
    hoje = datetime.now()
    inicio = hoje - timedelta(days=30)
    return (
        int(inicio.timestamp()),
        int(hoje.timestamp())
    )

def download_grafico(session, graphid, graph_name):
    """Baixa um gráfico específico usando sessão web"""
    try:
        stime, etime = get_periodo_30_dias()
        chart_url = ZABBIX_URL.replace('api_jsonrpc.php', 'chart2.php')
        
        params = {
            'graphid': graphid,
            'stime': stime,
            'etime': etime,
            'width': 1200,
            'height': 300
        }
        
        response = session.get(
            chart_url,
            params=params,
            stream=True,
            verify=False
        )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:200]}...")
            
        if 'image/png' not in response.headers.get('Content-Type', ''):
            raise Exception("Resposta não é uma imagem PNG")
        
        # Cria nome seguro para o arquivo
        safe_name = "".join([c if c.isalnum() else "_" for c in graph_name])
        file_path = os.path.join(OUTPUT_DIR, f"{safe_name}.png")
        
        # Salva o arquivo
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        
        logging.info(f"Gráfico salvo: {file_path}")
        return file_path
        
    except Exception as e:
        logging.error(f"Falha no download de {graph_name}: {str(e)}")
        return None

def processar_graficos():
    try:
        zapi = ZabbixAPI(validar_url_zabbix())
        zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
        logging.info("Autenticação API realizada com sucesso")

        hostid = obter_hostid_do_json()
        
        # Obtém gráficos disponíveis
        graphs = zapi.graph.get(
            hostids=hostid,
            output=["name", "graphid"]
        )
        
        # Filtra gráficos relevantes
        graphs_relevantes = [
            g for g in graphs 
            if any(kw in g['name'] for kw in ['CPU', 'memória', 'RAM'])
        ]
        
        if not graphs_relevantes:
            logging.error("Nenhum gráfico relevante encontrado")
            return

        # Cria sessão web separada
        web_session = criar_sessao_web()
        
        # Processamento paralelo
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    download_grafico,
                    web_session,
                    graph['graphid'],
                    graph['name']
                )
                for graph in graphs_relevantes
            ]
            
            resultados = [
                future.result()
                for future in futures
                if future.result() is not None
            ]
            
        logging.info(f"Total de gráficos baixados: {len(resultados)}")

    except Exception as e:
        logging.error(f"Erro crítico: {str(e)}")
        print(f"Erro: {str(e)}")

if __name__ == '__main__':
    processar_graficos()