# src/apps/app_graphics.py
import os
import logging
import re
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

# Configurações do Zabbix
ZABBIX_URL = os.getenv("URL_ZBX")  # Exemplo: "http://10.85.104.5"
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
    
    # Acessa a página de login e aguarda o estado networkidle
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

def capture_pages():
    # URLs dos gráficos de CPU e Memória
    url_cpu = f"{ZABBIX_URL}/history.php?action=showgraph&itemids%5B%5D=92350"
    url_memoria = f"{ZABBIX_URL}/history.php?action=showgraph&itemids%5B%5D=92366"

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # Realiza o login no Zabbix
            login_zabbix(page)
            
            # Captura da página de CPU:
            logging.info(f"Acessando página de CPU: {url_cpu}")
            page.goto(url_cpu, wait_until="networkidle")
            # Aguarda que um elemento que contenha o gráfico esteja visível.
            # Aqui usamos "img" como exemplo; se o gráfico for renderizado em canvas, troque para "canvas".
            page.wait_for_selector("img", timeout=15000)
            # Alternativamente, pode-se aguardar alguns segundos:
            # page.wait_for_timeout(3000)
            cpu_path = os.path.join(OUTPUT_DIR, "full_page_cpu.png")
            page.screenshot(path=cpu_path, full_page=True)
            logging.info(f"Screenshot da página de CPU salvo com sucesso em: {cpu_path}")
            
            # Captura da página de Memória:
            logging.info(f"Acessando página de Memória: {url_memoria}")
            page.goto(url_memoria, wait_until="networkidle")
            page.wait_for_selector("img", timeout=15000)
            mem_path = os.path.join(OUTPUT_DIR, "full_page_memoria.png")
            page.screenshot(path=mem_path, full_page=True)
            logging.info(f"Screenshot da página de Memória salvo com sucesso em: {mem_path}")
            
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
