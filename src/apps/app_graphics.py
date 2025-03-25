# src/apps/app_graphics.py
import os
import logging
import re
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv(dotenv_path='/home/tauge/Documents/tauge/PGR/.env')

# Configuração do log
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'zabbix.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configurações do Zabbix (as variáveis ZABBIX_URL, ZABBIX_USER e ZABBIX_PASSWORD continuam disponíveis)
ZABBIX_URL = os.getenv("URL_ZBX")
ZABBIX_USER = os.getenv("USER_ZBX")
ZABBIX_PASSWORD = os.getenv("PASS_ZBX")
OUTPUT_DIR = "/home/tauge/Documents/tauge/PGR/output/graphics"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def login_zabbix(page):
    """
    Realiza o login no Zabbix.
    Página de login: {ZABBIX_URL}/
      - Campo de usuário: input com id "name"
      - Campo de senha: input com id "password"
      - Botão de login: button com id "enter"
    Após o login, o Zabbix redireciona para uma URL contendo "zabbix.php?action=dashboard.view".
    """
    login_url = f"{ZABBIX_URL}/"
    logging.info(f"Iniciando login na URL: {login_url}")
    
    page.goto(login_url, wait_until="networkidle")
    
    # Aguarda e preenche os campos de login
    page.wait_for_selector("input#name", timeout=15000)
    page.fill("input#name", ZABBIX_USER)
    page.fill("input#password", ZABBIX_PASSWORD)
    
    # Aguarda o botão de login e clica nele, esperando a navegação para o dashboard
    page.wait_for_selector("button#enter", timeout=15000)
    with page.expect_navigation(url=re.compile(r".*zabbix\.php\?action=dashboard\.view.*"), timeout=30000):
        page.click("button#enter")
    
    logging.info(f"Login realizado com sucesso. URL atual: {page.url}")

def set_date_and_capture(page, url, output_filename):
    """
    Acessa a URL do gráfico, altera o período para "now-30d" a "now",
    clica no botão Apply, aguarda 7 segundos e captura a imagem do gráfico.
    """
    logging.info(f"Acessando URL: {url}")
    page.goto(url, wait_until="networkidle")
    
    # Aguarda os campos de data e botão de apply
    page.wait_for_selector("input#from", timeout=15000)
    page.wait_for_selector("input#to", timeout=15000)
    page.wait_for_selector("button#apply", timeout=15000)
    
    # Define o período de 30 dias
    page.fill("input#from", "now-30d")
    page.fill("input#to", "now")
    page.click("button#apply")
    
    # Aguarda 7 segundos para que o gráfico seja atualizado
    page.wait_for_timeout(7000)
    
    # Aguarda que o elemento do gráfico esteja visível
    page.wait_for_selector("img#historyGraph", timeout=15000)
    
    # Captura apenas o elemento do gráfico
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    page.locator("img#historyGraph").screenshot(path=output_path)
    logging.info(f"Screenshot do gráfico salvo com sucesso em: {output_path}")

def capture_pages():
    # Carrega as URLs do arquivo JSON (localizado na raiz da aplicação)
    json_file = 'ulrzbx.json'
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        url_cpu = data.get("urlcpu")
        url_memoria = data.get("urlmemoria")
        logging.info("URLs carregadas do arquivo JSON com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao ler o arquivo JSON: {e}")
        print(f"Erro ao ler o arquivo JSON: {e}")
        return

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # Efetua o login no Zabbix
            login_zabbix(page)
            
            # Captura do gráfico de CPU (após alterar para 30 dias)
            set_date_and_capture(page, url_cpu, "full_page_cpu.png")
            
            # Captura do gráfico de Memória (após alterar para 30 dias)
            set_date_and_capture(page, url_memoria, "full_page_memoria.png")
            
            print("Imagens capturadas com sucesso!")
        except PlaywrightTimeoutError as e:
            logging.error(f"Timeout ao aguardar o estado da página: {e}")
            print(f"Timeout ao aguardar o estado da página: {e}")
        except Exception as e:
            logging.error(f"Erro durante a execução: {e}")
            print(f"Erro durante a execução: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    capture_pages()
