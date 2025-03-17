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
CLIENT_INFO_FILE = "/home/tauge/Documents/tauge/PGR/client_info copy.json"
SERV_INFO_FILE = "/home/tauge/Documents/tauge/PGR/serv_info.json"

def validar_url_zabbix():
    """Valida e ajusta a URL do Zabbix para a API."""
    parsed = urlparse(ZABBIX_URL)
    if not parsed.path.endswith('/api_jsonrpc.php'):
        new_path = parsed.path.rstrip('/') + '/api_jsonrpc.php'
        return parsed._replace(path=new_path).geturl()
    return ZABBIX_URL

def carregar_json(caminho_arquivo):
    """Carrega as informações de um arquivo JSON."""
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as file:
            data = json.load(file)
        logging.info(f"Informações carregadas de {caminho_arquivo}")
        return data
    except Exception as e:
        logging.error(f"Erro ao carregar {caminho_arquivo}: {str(e)}")
        raise

def obter_valor_item(zapi, itemid):
    """
    Obtém a última informação do item com base em seu itemid.
    Retorna o valor encontrado.
    """
    try:
        # Obtém o tipo de valor do item
        item_details = zapi.item.get(itemids=itemid, output=["value_type"])
        if not item_details:
            logging.error(f"Item {itemid} não encontrado.")
            raise Exception(f"Item {itemid} não encontrado.")
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
            logging.error(f"Nenhum dado histórico encontrado para o item {itemid}.")
            raise Exception(f"Nenhum dado histórico encontrado para o item {itemid}.")
        return history[0]['value']

    except Exception as e:
        logging.error(f"Erro ao obter o valor do item {itemid}: {str(e)}")
        raise

def obter_consultas(zapi, info_dict):
    """
    Para cada chave do dicionário, tenta converter seu valor para inteiro.
    Se conseguir, realiza a consulta na API do Zabbix; caso contrário,
    utiliza o valor original.
    Retorna um dicionário com os resultados.
    """
    consultas = {}
    for key, value in info_dict.items():
        try:
            # Tenta converter para inteiro
            item_id = int(value)
            try:
                valor = obter_valor_item(zapi, str(item_id))
                consultas[key] = valor
                logging.info(f"Consulta obtida para '{key}' (ID: {item_id}).")
            except Exception as e:
                logging.error(f"Erro ao obter consulta para '{key}' (ID: {item_id}): {str(e)}")
                consultas[key] = f"Erro: {str(e)}"
        except (ValueError, TypeError):
            # Se não for conversível para inteiro, utiliza o valor original
            consultas[key] = value
            logging.info(f"Campo '{key}' não é numérico, valor mantido: {value}")
    return consultas

def salvar_consulta_em_arquivo(chave, valor):
    """
    Salva o valor da consulta em um arquivo separado, cujo nome é definido
    pela chave do JSON.
    Tenta formatar o conteúdo como JSON, caso contrário salva como texto puro.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"{chave}_consulta.txt"
        output_file = os.path.join(OUTPUT_DIR, filename)

        try:
            formatted_value = json.dumps(valor, indent=4, ensure_ascii=False)
        except Exception:
            formatted_value = str(valor)

        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(formatted_value)
        logging.info(f"Consulta '{chave}' salva em {output_file}")
        print(f"Consulta '{chave}' salva com sucesso em {output_file}")

    except Exception as e:
        logging.error(f"Erro ao salvar consulta '{chave}': {str(e)}")
        raise

def salvar_consultas_serv_em_unico_arquivo(resultado):
    """
    Salva todas as consultas do serv_info.json em um único arquivo Info_serv_prod.txt.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, "Info_serv_prod.txt")

        with open(output_file, 'w', encoding='utf-8') as file:
            for chave, valor in resultado.items():
                try:
                    formatted_value = json.dumps(valor, indent=4, ensure_ascii=False)
                except Exception:
                    formatted_value = str(valor)
                file.write(f"{chave}: {formatted_value}\n")
        logging.info(f"Todas as consultas de serv_info salvas em {output_file}")
        print(f"Todas as consultas de serv_info salvas com sucesso em {output_file}")

    except Exception as e:
        logging.error(f"Erro ao salvar consultas de serv_info: {str(e)}")
        raise

def main():
    """Função principal para executar o script."""
    try:
        # Carrega informações do cliente e do servidor
        client_info = carregar_json(CLIENT_INFO_FILE)
        serv_info = carregar_json(SERV_INFO_FILE)

        # Autenticação na API do Zabbix
        zapi = ZabbixAPI(validar_url_zabbix())
        zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
        logging.info("Autenticação API realizada com sucesso.")

        # Obtém as consultas para os itens definidos nos JSONs
        resultado_client = obter_consultas(zapi, client_info)
        resultado_serv = obter_consultas(zapi, serv_info)

        # Salva cada consulta do client_info em arquivos separados
        for chave, valor in resultado_client.items():
            salvar_consulta_em_arquivo(chave, valor)

        # Salva todas as consultas do serv_info em um único arquivo
        salvar_consultas_serv_em_unico_arquivo(resultado_serv)

    except Exception as e:
        logging.error(f"Erro no processo: {str(e)}")
        print(f"Erro: {str(e)}")

if __name__ == '__main__':
    main()