import os
from dotenv import load_dotenv
from app_graphics import login_zabbix

# Carrega o .env utilizando o caminho absoluto
load_dotenv(dotenv_path='/home/tauge/Documents/tauge/PGR/.env')

print("URL:", os.getenv("URL_ZBX"))
print("Usuário:", os.getenv("USER_ZBX"))

try:
    token = login_zabbix()
    print("Token:", token)
except Exception as e:
    print("Erro:", e)
