import jaydebeapi
import jinja2
import pdfkit
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações JDBC
user = os.getenv("USER_JDBC")
password = os.getenv("PASS_JDBC")
jdbc_jar = os.getenv("JAR_JDBC")

# Caminho do template HTML
template_path = "static/assets/pgr.html"

# Carregar configurações do cliente
storage_file = 'client_info.json'


def carregar_configuracoes_do_storage():
    """Carrega configurações do cliente a partir de client_info.json"""
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
        raise FileNotFoundError("Arquivo 'client_info.json' não encontrado.")


def executar_consulta(conexao, query):
    """Executa uma consulta e retorna o resultado"""
    cursor = conexao.cursor()
    try:
        cursor.execute(query)
        resultado = cursor.fetchall()
        return resultado
    except jaydebeapi.DatabaseError as e:
        logging.error(f"Erro ao executar a query: {e}")
        return None
    finally:
        cursor.close()


def obter_dados_do_banco():
    """Executa as consultas e retorna um dicionário com os dados formatados"""
    jdbc_url, user, password = carregar_configuracoes_do_storage()
    
    try:
        conexao = jaydebeapi.connect('oracle.jdbc.driver.OracleDriver', jdbc_url, [user, password], jdbc_jar)

        consultas = {
            "versao_do_banco_de_dados": "SELECT version FROM PRODUCT_COMPONENT_VERSION WHERE product LIKE 'Oracle Database%'",
            "maiores_tabelas": """SELECT table_name, bytes/1024/1024/1024 AS tamanho_gb 
                                  FROM dba_segments WHERE segment_type = 'TABLE'
                                  ORDER BY tamanho_gb DESC FETCH FIRST 1 ROWS ONLY""",
            "top_sql": """SELECT sql_text FROM v$sqlarea ORDER BY elapsed_time DESC FETCH FIRST 1 ROWS ONLY""",
            "monitoramento_memoria": """SELECT resource_name, current_utilization FROM v$resource_limit WHERE resource_name = 'processes'""",
            "monitoramento_cpu": """SELECT resource_name, current_utilization FROM v$resource_limit WHERE resource_name = 'sessions'""",
            "crescimento_base": """SELECT round(sum(used.bytes) / 1024 / 1024 / 1024) || ' GB' AS tamanho
                                   FROM (SELECT bytes FROM v$datafile UNION ALL
                                         SELECT bytes FROM v$tempfile UNION ALL
                                         SELECT bytes FROM v$log) used""",
            "desvios_backup": """SELECT COUNT(*) FROM v$RMAN_BACKUP_JOB_DETAILS WHERE status != 'COMPLETED'""",
            "data_backup": """SELECT MAX(start_time) FROM v$RMAN_BACKUP_JOB_DETAILS""",
            "desvio_backup": """SELECT status FROM v$RMAN_BACKUP_JOB_DETAILS WHERE ROWNUM = 1 ORDER BY start_time DESC""",
            "acao_backup": """SELECT time_taken_display FROM v$RMAN_BACKUP_JOB_DETAILS WHERE ROWNUM = 1 ORDER BY start_time DESC""",
            "status_backup": """SELECT DISTINCT status FROM v$RMAN_BACKUP_JOB_DETAILS""",
        }

        dados = {}
        for chave, query in consultas.items():
            resultado = executar_consulta(conexao, query)
            if resultado:
                dados[chave] = resultado[0][0]  # Pegando o primeiro valor da primeira linha do resultado
            else:
                dados[chave] = "Não disponível"

        return dados
    except jaydebeapi.DatabaseError as e:
        logging.error(f"Erro ao conectar ao banco: {e}")
        return {}
    finally:
        if 'conexao' in locals() and conexao:
            conexao.close()


def gerar_pdf(dados):
    """Gera um PDF a partir do template preenchido"""
    template_loader = jinja2.FileSystemLoader('./')
    template_env = jinja2.Environment(loader=template_loader)

    try:
        template = template_env.get_template(template_path)
    except jinja2.exceptions.TemplateNotFound:
        logging.error("Erro: O template 'pgr.html' não foi encontrado.")
        exit(1)

    output_text = template.render(dados)

    config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")

    options = {
        "encoding": "UTF-8"
    }

    pdfkit.from_string(output_text, 'pgr_final.pdf', configuration=config, options=options)
    print("PDF gerado com sucesso!")


if __name__ == "__main__":
    dados_extraidos = obter_dados_do_banco()
    gerar_pdf(dados_extraidos)
