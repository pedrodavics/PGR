import jaydebeapi
import concurrent.futures
from flask import Flask, jsonify
import logging
import os
import json
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("USER_JDBC")
password = os.getenv("PASS_JDBC")
jdbc_jar = os.getenv("JAR_JDBC")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sql_file = "src/scripts/sql/queries.sql"
output_directory = "./output"
reports_directory = os.path.join(output_directory, "reports")
output_file = os.path.join(reports_directory, "result_jdbc.txt")

storage_file = 'client_info.json'  

def criar_diretorio_resultados():
    """Cria o diretório 'txt_results' caso não exista."""
    os.makedirs(reports_directory, exist_ok=True)
    logging.info(f"Diretório '{reports_directory}' verificado/criado.")

def carregar_configuracoes_do_storage():
    """Carrega as configurações de conexão do armazenamento local."""
    if os.path.exists(storage_file):
        with open(storage_file, 'r') as f:

            data = json.load(f)
            ip = data.get('ip')
            db_name = data.get('nomebanco')
            port = data.get('portabanco')

            if not all([ip, db_name, user, password]):
                raise ValueError("Informações incompletas no arquivo de armazenamento.")

            jdbc_url = f"jdbc:oracle:thin:@{ip}:{port}/{db_name}"
            logging.info(f"String de conexão montada: {jdbc_url}")
            return jdbc_url, user, password
    else:
        raise FileNotFoundError("Arquivo de armazenamento 'client_info.json' não encontrado.")

def executar_comando_sql(conexao, comando, arquivo_saida):
    cursor = conexao.cursor()
    try:
        logging.info(f"Executando: {comando}")
        cursor.execute(comando)
        with open(arquivo_saida, 'a', encoding='utf-8') as f_saida:
            if cursor.description:
                nomes_colunas = [col[0] for col in cursor.description]
                f_saida.write('\t'.join(nomes_colunas) + '\n')
                for linha in cursor.fetchall():
                    f_saida.write('\t'.join(map(str, linha)) + '\n')

    except jaydebeapi.DatabaseError as e:
        logging.error(f"Erro: {e}")
        with open(arquivo_saida, 'a', encoding='utf-8') as f_saida:
            f_saida.write(f"Erro: {e}\n")

    finally:
        cursor.close()

def executar_sql_e_conectar_oracle(sql_file, arquivo_saida, jdbc_jar):
    criar_diretorio_resultados()

    jdbc_url, user, password = carregar_configuracoes_do_storage()

    with open(sql_file, 'r', encoding='utf-8') as f:
        comandos_sql = [comando.strip() for comando in f.read().split(';') if comando.strip()]

    try:
        conexao = jaydebeapi.connect('oracle.jdbc.driver.OracleDriver', jdbc_url, [user, password], jdbc_jar)

        with open(arquivo_saida, 'w', encoding='utf-8') as f_saida:
            f_saida.write("")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(executar_comando_sql, conexao, comando, arquivo_saida) for comando in comandos_sql]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Erro ao processar o comando SQL: {e}")

        logging.info(f"Arquivo '{arquivo_saida}' gerado com sucesso.")
    except jaydebeapi.DatabaseError as e:
        logging.error(f"Erro ao executar o script SQL: {e}")
    finally:
        if 'conexao' in locals() and conexao:
            conexao.close()

app = Flask(__name__)

@app.route('/executar_sql', methods=['GET'])
def executar_sql():
    """Rota para executar o script SQL e gerar o arquivo."""
    logging.info("Rota '/executar_sql' chamada.")
    try:
        executar_sql_e_conectar_oracle(sql_file, output_file, jdbc_jar)
        return jsonify({"mensagem": "Arquivo gerado com sucesso.", "caminho_arquivo": output_file}), 200
    except Exception as e:
        logging.error(f"Erro ao executar SQL: {e}")
        return jsonify({"erro": "Erro ao executar SQL"}), 500

def executar_sql_automaticamente():
    """Executa o SQL automaticamente ao iniciar o servidor Flask."""
    logging.info("Executando SQL automaticamente no início.")
    try:
        executar_sql_e_conectar_oracle(sql_file, output_file, jdbc_jar)
    except Exception as e:
        logging.error(f"Erro ao executar SQL automaticamente: {e}")

if __name__ == '__main__':
    executar_sql_automaticamente()

