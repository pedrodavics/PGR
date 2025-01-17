import jaydebeapi
import concurrent.futures
from flask import Flask, jsonify
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sql_file = "src/scripts/sql/queries.sql"
output_directory = "./output"
reports_directory = os.path.join(output_directory, "reports")
output_file = os.path.join(reports_directory, "result_jdbc.txt")
jdbc_jar = os.getenv("JAR_JDBC")
url = os.getenv("URL_JDBC")
user = os.getenv("USER_JDBC")
password = os.getenv("PASS_JDBC")

def criar_diretorio_resultados():
    """Cria o diretório 'txt_results' caso não exista."""
    os.makedirs(reports_directory, exist_ok=True)
    logging.info(f"Diretório '{reports_directory}' verificado/criado.")

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

def executar_sql_e_conectar_oracle(sql_file, arquivo_saida, jdbc_jar, url, user, password):
    criar_diretorio_resultados()
    
    with open(sql_file, 'r', encoding='utf-8') as f:
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
        executar_sql_e_conectar_oracle(sql_file, output_file, jdbc_jar, url, user, password)
        return jsonify({"mensagem": "Arquivo gerado com sucesso.", "caminho_arquivo": output_file}), 200
    except Exception as e:
        logging.error(f"Erro ao executar SQL: {e}")
        return jsonify({"erro": "Erro ao executar SQL"}), 500
    
if __name__ == '__main__':
    logging.info("Iniciando servidor Flask...")
    app.run(debug=True)
