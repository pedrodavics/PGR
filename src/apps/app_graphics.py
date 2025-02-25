import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
dotenv_path = '/home/tauge/Documents/tauge/PGR/.env'
load_dotenv(dotenv_path=dotenv_path)

# Configurações do Zabbix
ZABBIX_URL = os.getenv("URL_ZBX")
ZABBIX_USER = os.getenv("USER_ZBX")
ZABBIX_PASSWORD = os.getenv("PASS_ZBX")

# Diretório onde os gráficos serão salvos
OUTPUT_DIR = "/home/tauge/Documents/tauge/PGR/output/graphics"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# IDs dos itens cujos gráficos desejamos baixar
items = {
    "memoria_utilizada": 55981,
    "cpu_utilizacao": 55998
}

# Sessão de requests para manter a autenticação
session = requests.Session()

def login():
    """
    Realiza o login no Zabbix e mantém a sessão autenticada.
    """
    login_url = f"{ZABBIX_URL}/index.php"
    payload = {
        "name": ZABBIX_USER,
        "password": ZABBIX_PASSWORD,
        "enter": "Sign in"
    }
    response = session.post(login_url, data=payload)
    if "zbx_sessionid" in session.cookies:
        print("Login realizado com sucesso.")
    else:
        print("Falha no login.")
        exit()

def download_graph(item_name, item_id):
    """
    Baixa o gráfico correspondente ao item_id e salva como PNG.
    """
    graph_url = f"{ZABBIX_URL}/chart.php?period=2592000&itemids[]={item_id}"
    response = session.get(graph_url)
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        output_path = os.path.join(OUTPUT_DIR, f"{item_name}.png")
        image.save(output_path)
        print(f"Gráfico '{item_name}' salvo em: {output_path}")
    else:
        print(f"Falha ao baixar o gráfico '{item_name}'. Status code: {response.status_code}")

if __name__ == "__main__":
    login()
    for name, item_id in items.items():
        download_graph(name, item_id)
