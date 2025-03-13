import jaydebeapi
import jinja2
import pdfkit
import os
import json
import logging
import pandas as pd  # Importa o pandas para formatação da tabela, se necessário
from dotenv import load_dotenv
import io
import re

load_dotenv()

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações JDBC (obtidas do .env)
jdbc_user = os.getenv("USER_JDBC")
jdbc_password = os.getenv("PASS_JDBC")
jdbc_jar = os.getenv("JAR_JDBC")

# Caminho do template HTML
template_path = "static/assets/pgr.html"

# Caminho do arquivo de armazenamento
storage_file = 'client_info.json'

def carregar_configuracoes_do_storage():
    """Carrega configurações do cliente a partir de client_info.json"""
    if os.path.exists(storage_file):
        with open(storage_file, 'r') as f:
            data = json.load(f)
            ip = data.get('ip')
            db_name = data.get('nomebanco')
            port_jdbc = data.get('portabanco')
            
            if not all([ip, db_name, jdbc_user, jdbc_password]):
                raise ValueError("Informações incompletas no arquivo de armazenamento.")
            
            jdbc_url = f"jdbc:oracle:thin:@{ip}:{port_jdbc}/{db_name}"
            logging.info(f"String de conexão montada: {jdbc_url}")
            return jdbc_url, jdbc_user, jdbc_password, db_name
    else:
        raise FileNotFoundError("Arquivo 'client_info.json' não encontrado.")

def obter_dados_do_banco():
    """
    Lê os conteúdos dos arquivos TXT e retorna um dicionário com os dados formatados.
    As chaves são mapeadas para os seguintes arquivos:
        - "versao_do_banco_de_dados"      -> /home/tauge/Documents/tauge/PGR/output/info_db_consulta.txt
        - "maiores_tabelas"               -> /home/tauge/Documents/tauge/PGR/output/biggest_tables_consulta.txt
        - "top_sql"                       -> /home/tauge/Documents/tauge/PGR/output/top_queries_consulta.txt
        - "print_backup"                  -> /home/tauge/Documents/tauge/PGR/output/backups_consulta.txt
    """
    def ler_arquivo(caminho):
        try:
            with open(caminho, "r") as file:
                return file.read()
        except Exception as e:
            logging.error(f"Erro ao ler arquivo {caminho}: {e}")
            return "Não disponível"

    dados = {}
    dados["versao_do_banco_de_dados"] = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/info_db_consulta.txt")
    dados["maiores_tabelas"] = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/biggest_tables_consulta.txt")
    
    # Para top_sql: formata os blocos separados por '{"rank":"'
    conteudo_top_sql = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/top_queries_consulta.txt")
    blocos_top_sql = re.split(r'(?=\{"rank":")', conteudo_top_sql)
    blocos_top_sql = blocos_top_sql[:10]  # Garante que sejam apenas 10 partes, se houver mais
    
    blocos_formatados = []
    for i, bloco in enumerate(blocos_top_sql, 1):
        # Remove espaços e substitui as quebras de linha literais por <br>
        bloco_formatado = bloco.strip().replace("\\r\\n", "<br><br><br><br>")
        # Encapsula cada bloco em um parágrafo (<p>) para garantir a linha em branco entre eles
        blocos_formatados.append(f"<p>{i}) {bloco_formatado}</p>")
    # Junta os parágrafos; cada <p> já gera a separação desejada
    dados["top_sql"] = "\n".join(blocos_formatados)
    
    # Para print_backup, converte o conteúdo em uma tabela HTML usando pandas
    conteudo_print_backup = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/backups_consulta.txt")
    try:
        df = pd.read_csv(io.StringIO(conteudo_print_backup), header=None)
        if df.shape[1] != 7:
            raise ValueError("Número de colunas inesperado")
        df.columns = ["START_TIME", "END_TIME", "MBYTES", "STATUS", "INPUT_TYPE", "DOW", "SECONDS TAKEN"]
        dados["print_backup"] = df.to_html(classes="tabela_cinza", index=False, border=0, justify="center")
    except Exception as e:
        logging.error(f"Erro ao converter print_backup para HTML: {e}")
        dados["print_backup"] = f"<p>Erro ao formatar os dados: {conteudo_print_backup}</p>"
        
    return dados

def gerar_pdf(dados):
    """Gera um PDF a partir do template preenchido"""
    template_loader = jinja2.FileSystemLoader('./')
    template_env = jinja2.Environment(loader=template_loader)

    try:
        template = template_env.get_template(template_path)
    except jinja2.exceptions.TemplateNotFound:
        logging.error("Erro: O template 'pgr.html' não foi encontrado.")
        exit(1)

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

    # Define o diretório de destino para o PDF
    output_dir = "/home/tauge/Documents/tauge/PGR/output/pdf temp"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_file = os.path.join(output_dir, "pgr_final.pdf")

    pdfkit.from_string(output_text, output_file, configuration=config, options=options)
    print("PDF gerado com sucesso em:", output_file)

if __name__ == "__main__":
    dados_extraidos = obter_dados_do_banco()
    gerar_pdf(dados_extraidos)
