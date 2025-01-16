import jaydebeapi
import concurrent.futures
from flask import Flask, jsonify
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_SQL = "scripts/sql/queries.sql"
OUTPUT_DIRECTORY = "./output"
TXT_RESULTS_DIRECTORY = os.path.join(OUTPUT_DIRECTORY, "txt_results")
ARQUIVO_SAIDA = os.path.join(TXT_RESULTS_DIRECTORY, "result_jdbc.txt")
JDBC_JAR = "./static/assets/ojdbc11.jar"
URL = "jdbc:oracle:thin:@10.0.1.4:1521/WINT"
USER = "zbxtauge"
PASSWORD = "zbxtauge"

def criar_diretorio_resultados():
    """Cria o diretório 'txt_results' caso não exista."""
    os.makedirs(TXT_RESULTS_DIRECTORY, exist_ok=True)
    logging.info(f"Diretório '{TXT_RESULTS_DIRECTORY}' verificado/criado.")

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

def executar_sql_e_conectar_oracle(arquivo_sql, arquivo_saida, jdbc_jar, url, user, password):
    criar_diretorio_resultados()
    
    with open(arquivo_sql, 'r', encoding='utf-8') as f:
        comandos_sql = [comando.strip() for comando in f.read().split(';') if comando.strip()]

    try:
        conexao = jaydebeapi.connect('oracle.jdbc.driver.OracleDriver', url, [user, password], jdbc_jar)

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
        executar_sql_e_conectar_oracle(ARQUIVO_SQL, ARQUIVO_SAIDA, JDBC_JAR, URL, USER, PASSWORD)
        return jsonify({"mensagem": "Arquivo gerado com sucesso.", "caminho_arquivo": ARQUIVO_SAIDA}), 200
    except Exception as e:
        logging.error(f"Erro ao executar SQL: {e}")
        return jsonify({"erro": "Erro ao executar SQL"}), 500
    
if __name__ == '__main__':
    logging.info("Iniciando servidor Flask...")
    app.run(debug=True)
