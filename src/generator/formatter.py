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
            "versao_do_banco_de_dados": """SELECT version 
                                            FROM PRODUCT_COMPONENT_VERSION 
                                            WHERE product LIKE 'Oracle Database%'""",
            "maiores_tabelas": """SELECT * 
                                  FROM 
                                    (SELECT owner, segment_name AS table_name, bytes/1024/1024/1024 AS "SIZE (GB)"
                                     FROM dba_segments 
                                     WHERE segment_type = 'TABLE'
                                     AND segment_name NOT LIKE 'BIN%' 
                                     ORDER BY 3 DESC) 
                                  WHERE rownum <= 20""",

            "top_sql": """SELECT rownum AS rank, a.* 
                                        FROM 
                                          (SELECT elapsed_Time/1000000 AS elapsed_time, executions, cpu_time, sql_id, sql_text
                                           FROM v$sqlarea 
                                           WHERE elapsed_time/1000000 > 5 
                                           ORDER BY elapsed_time DESC) a 
                                        WHERE rownum < 11""",

            "print_backup": """SELECT
                                          TO_CHAR(j.start_time, 'yyyy-mm-dd hh24:mi:ss') AS start_time,
                                          TO_CHAR(j.end_time, 'yyyy-mm-dd hh24:mi:ss') AS end_time,
                                          (j.output_bytes/1024/1024) AS output_mbytes,
                                          j.status, 
                                          j.input_type,
                                          DECODE(TO_CHAR(j.start_time, 'd'), 
                                                 1, 'Sunday', 
                                                 2, 'Monday', 
                                                 3, 'Tuesday', 
                                                 4, 'Wednesday', 
                                                 5, 'Thursday', 
                                                 6, 'Friday', 
                                                 7, 'Saturday') AS dow,
                                          j.elapsed_seconds, 
                                          j.time_taken_display,
                                          x.cf, 
                                          x.df, 
                                          x.i0, 
                                          x.i1, 
                                          x.l,
                                          ro.inst_id AS output_instance
                                        FROM v$RMAN_BACKUP_JOB_DETAILS j
                                        LEFT OUTER JOIN 
                                          (SELECT 
                                             d.session_recid, 
                                             d.session_stamp,
                                             SUM(CASE WHEN d.controlfile_included = 'YES' THEN d.pieces ELSE 0 END) AS CF,
                                             SUM(CASE WHEN d.controlfile_included = 'NO' AND d.backup_type||d.incremental_level = 'D' THEN d.pieces ELSE 0 END) AS DF,
                                             SUM(CASE WHEN d.backup_type||d.incremental_level = 'D0' THEN d.pieces ELSE 0 END) AS I0,
                                             SUM(CASE WHEN d.backup_type||d.incremental_level = 'I1' THEN d.pieces ELSE 0 END) AS I1,
                                             SUM(CASE WHEN d.backup_type = 'L' THEN d.pieces ELSE 0 END) AS L
                                           FROM v$BACKUP_SET_DETAILS d
                                           JOIN v$BACKUP_SET s ON s.set_stamp = d.set_stamp AND s.set_count = d.set_count
                                           WHERE s.input_file_scan_only = 'NO'
                                           GROUP BY d.session_recid, d.session_stamp) x 
                                        ON x.session_recid = j.session_recid AND x.session_stamp = j.session_stamp
                                        LEFT OUTER JOIN 
                                          (SELECT o.session_recid, o.session_stamp, MIN(inst_id) AS inst_id
                                           FROM Gv$RMAN_OUTPUT o
                                           GROUP BY o.session_recid, o.session_stamp) ro 
                                        ON ro.session_recid = j.session_recid AND ro.session_stamp = j.session_stamp
                                        WHERE j.start_time > TRUNC(SYSDATE)-7
                                        ORDER BY j.start_time"""
        }

        dados = {}
        for chave, query in consultas.items():
            resultado = executar_consulta(conexao, query)
            if resultado:
                dados[chave] = resultado
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
