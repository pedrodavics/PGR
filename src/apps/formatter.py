import jaydebeapi
import jinja2
import pdfkit
import os
import json
import logging
import paramiko
from dotenv import load_dotenv

load_dotenv()

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações JDBC
jdbc_user = os.getenv("USER_JDBC")
jdbc_password = os.getenv("PASS_JDBC")
jdbc_jar = os.getenv("JAR_JDBC")

# Configurações SO
ssh_user = os.getenv("USER_OS")
ssh_password = os.getenv("PASS_OS")

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
            port_jdbc = data.get('portabanco')
            port_ssh = data.get('portassh')

            if not all([ip, db_name, jdbc_user, jdbc_password]):
                raise ValueError("Informações incompletas no arquivo de armazenamento.")

            jdbc_url = f"jdbc:oracle:thin:@{ip}:{port_jdbc}/{db_name}"
            logging.info(f"String de conexão montada: {jdbc_url}")
            return jdbc_url, jdbc_user, jdbc_password
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

def obter_dados_do_servidor():
    """
    Executa os comandos solicitados via SSH e retorna os resultados
    agrupados na chave 'Informações do Servidor Produtivo', formatados com <br>.
    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        
        with open(storage_file, 'r') as f:
            data = json.load(f)
            ip = data.get('ip')
            port_ssh = data.get('portassh')
        
        ssh.connect(ip, port=int(port_ssh), username=ssh_user, password=ssh_password)

        comandos = [
            "hostname",
            "ifconfig | grep inet | awk '{ print $2 }'",
            "cat /etc/*release*",
            "free -m",
            "df -h",
            "free -h"
        ]

        output_total = ""
        for comando in comandos:
            stdin, stdout, stderr = ssh.exec_command(comando)
            saida = stdout.read().decode()
            erros = stderr.read().decode()
            # Se houver erro, mas for o comando "df -h" e a mensagem mencionar "gvfs", ignoramos-o
            if erros:
                if comando == "df -h" and "gvfs" in erros:
                    output_total += f"{comando}:\n{saida}\n"
                else:
                    logging.error(f"Erro ao executar comando {comando}: {erros}")
                    output_total += f"Erro ao executar comando {comando}: {erros}\n"
            else:
                output_total += f"{comando}:\n{saida}\n"
        
        ssh.close()
        # Formata as informações do servidor usando <br> em vez de <br><br>
        formatted_output = "<br>".join(output_total.splitlines())
        return {"Informações do Servidor Produtivo": formatted_output}
    except paramiko.SSHException as e:
        logging.error(f"Erro na conexão SSH: {e}")
        return {"Informações do Servidor Produtivo": "Erro na conexão SSH"}

def obter_dados_do_banco():
    """Executa as consultas e retorna um dicionário com os dados formatados"""
    jdbc_url, jdbc_user, jdbc_password = carregar_configuracoes_do_storage()
    
    try:
        conexao = jaydebeapi.connect(
            'oracle.jdbc.driver.OracleDriver',
            jdbc_url,
            [jdbc_user, jdbc_password],
            jdbc_jar
        )

        consultas = {
            # Consulta para a versão do Oracle
            "versao_do_banco_de_dados": """
                SELECT version 
                FROM PRODUCT_COMPONENT_VERSION 
                WHERE product LIKE 'Oracle Database%'
            """,
            # Consulta para as 20 maiores tabelas
            "maiores_tabelas": """
                SELECT * 
                FROM 
                    (SELECT owner, segment_name AS table_name, bytes/1024/1024/1024 AS "SIZE (GB)"
                     FROM dba_segments 
                     WHERE segment_type = 'TABLE'
                     AND segment_name NOT LIKE 'BIN%' 
                     ORDER BY 3 DESC) 
                WHERE rownum <= 20
            """,
            # Consulta para top 10 queries mais lentas
            "top_sql": """
                SELECT rownum AS rank, a.* 
                FROM 
                    (SELECT elapsed_Time/1000000 AS elapsed_time, executions, cpu_time, sql_id, sql_text
                     FROM v$sqlarea 
                     WHERE elapsed_time/1000000 > 5 
                     ORDER BY elapsed_time DESC) a 
                WHERE rownum < 11
            """,
            # Consulta para detalhes de backup do RMAN
            "print_backup": """
                SELECT
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
                    j.elapsed_seconds
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
                ORDER BY j.start_time
            """
        }

        dados = {}
        for chave, query in consultas.items():
            resultado = executar_consulta(conexao, query)
            if resultado:
                # Converte cada tupla em string, separando-as com <br><br>
                resultado_str = "<br><br>".join(str(item) for item in resultado)
                dados[chave] = resultado_str
            else:
                dados[chave] = "Não disponível"

        dados_servidor = obter_dados_do_servidor()
        dados.update(dados_servidor)

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

    # Atualiza informações do servidor no dicionário de dados
    info_servidor = obter_dados_do_servidor().get("Informações do Servidor Produtivo")
    dados["informacoes_servidor"] = info_servidor

    # Inserir as imagens no contexto para o template
    caminho_imagens = "/home/tauge/Documents/tauge/PGR/output/graphics"
    dados["monitoramento_cpu"] = f"file://{os.path.join(caminho_imagens, 'CPU___utilizacao_plotly.png')}"
    dados["monitoramento_memoria"] = f"file://{os.path.join(caminho_imagens, 'Uso_de_memoria_plotly.png')}"

    output_text = template.render(dados)

    config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
    options = {
        "encoding": "UTF-8",
        "enable-local-file-access": None,
        "margin-top": "0.3cm",
        "margin-right": "3cm",
        "margin-bottom": "1cm",
        "margin-left": "2cm"
    }

    pdfkit.from_string(output_text, 'pgr_final.pdf', configuration=config, options=options)
    print("PDF gerado com sucesso!")

if __name__ == "__main__":
    dados_extraidos = obter_dados_do_banco()
    gerar_pdf(dados_extraidos)
