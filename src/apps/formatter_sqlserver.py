import jinja2
import pdfkit
import os
import logging
import pandas as pd  # Para formatação das tabelas
import io
import re
import json

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Caminho do template HTML
template_path = "static/assets/pgr.html"

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

    # Processa o arquivo de versão do banco: extrai apenas o valor da versão
    conteudo_versao = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/info_db_consulta.txt")
    try:
        data_version = json.loads(conteudo_versao)
        if isinstance(data_version, list) and len(data_version) > 0 and "version" in data_version[0]:
            versao = data_version[0]["version"]
        else:
            versao = conteudo_versao
    except Exception as e:
        logging.error(f"Erro ao converter info_db_consulta.txt para JSON: {e}")
        versao = conteudo_versao
    dados["versao_do_banco_de_dados"] = versao

    dados["maiores_tabelas"] = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/biggest_tables_consulta.txt")
    
    # Formatação do top_sql: divide o conteúdo em blocos e formata cada bloco em um parágrafo
    conteudo_top_sql = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/top_queries_consulta.txt")
    blocos_top_sql = re.split(r'(?=\{"rank":")', conteudo_top_sql)
    blocos_top_sql = blocos_top_sql[:10]  # Garante que sejam apenas 10 partes, se houver mais
    
    blocos_formatados = []
    for i, bloco in enumerate(blocos_top_sql, 1):
        bloco_formatado = bloco.strip().replace("\\r\\n", "<br><br><br><br>")
        blocos_formatados.append(f"<p>{i}) {bloco_formatado}</p>")
    dados["top_sql"] = "\n".join(blocos_formatados)
    
    # Processamento do print_backup: lê o conteúdo JSON e converte para uma tabela HTML usando pandas
    conteudo_print_backup = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/backups_consulta.txt")
    try:
        data_backup = json.loads(conteudo_print_backup)
        # Caso o conteúdo já tenha sido decodificado como string, decodifica novamente
        if isinstance(data_backup, str):
            data_backup = json.loads(data_backup)
        # Verifica se o resultado é uma lista
        if not isinstance(data_backup, list):
            raise ValueError("O conteúdo do backup não é uma lista de dicionários.")
        df = pd.DataFrame(data_backup)
        # Renomeia as colunas para os títulos esperados
        df = df.rename(columns={
            "StartTime": "START_TIME", 
            "EndTime": "END_TIME", 
            "TotalOutputMBytes": "MBYTES", 
            "BackupStatus": "STATUS", 
            "BackupType": "INPUT_TYPE", 
            "DayOfWeek": "DOW", 
            "ElapsedSeconds": "SECONDS TAKEN"
        })
        dados["print_backup"] = df.to_html(classes="tabela_cinza", index=False, border=0, justify="center")
    except Exception as e:
        logging.error(f"Erro ao converter print_backup para HTML: {e}")
        dados["print_backup"] = f"<p>Erro ao formatar os dados: {conteudo_print_backup}</p>"
        
    return dados

def gerar_pdf(dados):
    """Gera um PDF a partir do template HTML preenchido com os dados."""
    template_loader = jinja2.FileSystemLoader('./')
    template_env = jinja2.Environment(loader=template_loader)

    try:
        template = template_env.get_template(template_path)
    except jinja2.exceptions.TemplateNotFound:
        logging.error("Erro: O template 'pgr.html' não foi encontrado.")
        exit(1)

    # Inserir imagens no contexto para o template
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
