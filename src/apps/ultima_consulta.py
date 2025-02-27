import os
import json
import logging
from pyzabbix import ZabbixAPI
from dotenv import load_dotenv
from urllib.parse import urlparse

# Configuração do log
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'zabbix.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Carrega variáveis de ambiente
load_dotenv(dotenv_path='/home/tauge/Documents/tauge/PGR/.env')
ZABBIX_URL = os.getenv("URL_ZBX")
ZABBIX_USER = os.getenv("USER_ZBX")
ZABBIX_PASSWORD = os.getenv("PASS_ZBX")
OUTPUT_DIR = "/home/tauge/Documents/tauge/PGR/output"

def validar_url_zabbix():
    """Valida e ajusta a URL do Zabbix para a API."""
    parsed = urlparse(ZABBIX_URL)
    if not parsed.path.endswith('/api_jsonrpc.php'):
        new_path = parsed.path.rstrip('/') + '/api_jsonrpc.php'
        return parsed._replace(path=new_path).geturl()
    return ZABBIX_URL

def obter_ultima_consulta(zapi):
    """Obtém a última informação do item 166562 e retorna seu valor."""
    try:
        # Obtém o tipo de valor do item
        itemid = "166562"
        item_details = zapi.item.get(itemids=itemid, output=["value_type"])
        if not item_details:
            logging.error("Item não encontrado.")
            raise Exception("Item não encontrado.")
        value_type = int(item_details[0]['value_type'])

        # Obtém o histórico (última entrada)
        history = zapi.history.get(
            itemids=itemid,
            history=value_type,
            sortfield="clock",
            sortorder="DESC",
            limit=1
        )
        if not history:
            logging.error("Nenhum dado histórico encontrado para o item.")
            raise Exception("Nenhum dado histórico encontrado.")

        return history[0]['value']

    except Exception as e:
        logging.error(f"Erro ao obter última consulta: {str(e)}")
        raise

def salvar_em_arquivo(valor):
    """Salva o valor em um arquivo de texto, formatando como JSON se possível."""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, "ultima_consulta_sql.txt")

        # Tenta formatar como JSON, caso contrário salva como texto puro
        try:
            json_data = json.loads(valor)
            formatted_value = json.dumps(json_data, indent=4, ensure_ascii=False)
        except json.JSONDecodeError:
            formatted_value = valor

        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(formatted_value)
        logging.info(f"Última informação salva em {output_file}")
        print(f"Informação salva com sucesso em {output_file}")

    except Exception as e:
        logging.error(f"Erro ao salvar arquivo: {str(e)}")
        raise

def main():
    """Função principal para executar o script."""
    try:
        # Autenticação na API do Zabbix
        zapi = ZabbixAPI(validar_url_zabbix())
        zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
        logging.info("Autenticação API realizada com sucesso.")

        # Obtém a última consulta
        ultima_consulta = obter_ultima_consulta(zapi)

        # Salva em arquivo
        salvar_em_arquivo(ultima_consulta)

    except Exception as e:
        logging.error(f"Erro no processo: {str(e)}")
        print(f"Erro: {str(e)}")

if __name__ == '__main__':
    main()