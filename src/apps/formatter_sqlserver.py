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

def ler_arquivo(caminho):
    """Lê o conteúdo de um arquivo de texto."""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Erro ao ler o arquivo {caminho}: {e}")
        return ""

def obter_dados_do_banco():
    """Extrai e formata os dados dos arquivos de entrada para o PDF."""
    dados = {}
    
    # 1) Versão do banco (extrai apenas números e pontos)
    conteudo_versao = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/info_db_consulta.txt").strip()
    match = re.findall(r"[0-9]+(?:\.[0-9]+)+", conteudo_versao)
    versao = match[0] if match else "Versão não disponível"
    dados["versao_do_banco_de_dados"] = versao

    # 2) Tabela de maiores_tabelas (biggest_tables_consulta.txt)
    conteudo_biggest_tables = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/biggest_tables_consulta.txt").strip()
    list_data = None
    try:
        # Tenta carregar como JSON
        list_data = json.loads(conteudo_biggest_tables)
        if isinstance(list_data, str):
            list_data = json.loads(list_data)
        if not isinstance(list_data, list):
            raise ValueError("O conteúdo não é uma lista.")
    except Exception as e:
        logging.error(f"Falha ao ler JSON diretamente: {e}")
        # Fallback: tratar o conteúdo como string formatada
        try:
            # Divide os itens pela vírgula
            entries = conteudo_biggest_tables.split(',')
            list_data = []
            for entry in entries:
                entry = entry.strip()
                if not entry:
                    continue
                # Supondo o formato: "dbo.TABELA: 77029.38 MB"
                parts = entry.split(':')
                if len(parts) < 2:
                    continue
                key_part = parts[0].strip()       # Ex: "dbo.PROCESS_DOCUMENTS"
                value_part = parts[1].strip()       # Ex: "77029.38 MB"
                # Remove a unidade "MB"
                value_str = value_part.replace("MB", "").strip()
                try:
                    size_mb = float(value_str)
                    size_gb = size_mb / 1024  # Converte de MB para GB
                except Exception as ex:
                    logging.error(f"Erro ao converter valor {value_str}: {ex}")
                    size_gb = value_str
                # Separa owner e table_name (supondo que estejam unidos por ponto)
                if '.' in key_part:
                    owner, table_name = key_part.split('.', 1)
                else:
                    owner = ""
                    table_name = key_part
                list_data.append({"owner": owner, "table_name": table_name, "size_gb": f"{size_gb:.2f}"})
        except Exception as ex:
            logging.error(f"Erro no fallback do parsing de biggest_tables_consulta: {ex}")
            list_data = []

    try:
        df_tables = pd.DataFrame(list_data)
        df_tables = df_tables.rename(columns={
            "owner": "Owner",
            "table_name": "TABLE_NAME",
            "size_gb": "SIZE (GB)"
        })
        dados["maiores_tabelas"] = df_tables.to_html(classes="tabela_cinza", index=False, border=0, justify="center")
    except Exception as e:
        logging.error(f"Erro ao converter biggest_tables_consulta para HTML: {e}")
        dados["maiores_tabelas"] = f"<p>Erro ao formatar os dados: {conteudo_biggest_tables}</p>"

    # 3) Conteúdo de top_sql (top_queries_consulta.txt)
    conteudo_top_sql = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/top_queries_consulta.txt").strip()
    try:
        # Parsear o JSON para uma lista de dicionários
        data_top_sql = json.loads(conteudo_top_sql)
        if isinstance(data_top_sql, str):
            data_top_sql = json.loads(data_top_sql)
        if not isinstance(data_top_sql, list):
            raise ValueError("O conteúdo do top_queries_consulta não é uma lista de dicionários.")
        
        # Formatar cada objeto JSON em uma linha compacta, sem espaços extras, e com uma linha em branco entre eles
        formatted_top_sql = "\n\n".join(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) for obj in data_top_sql)
        dados["top_sql"] = formatted_top_sql
    except Exception as e:
        logging.error(f"Erro ao formatar top_queries_consulta: {e}")
        dados["top_sql"] = f"<p>Erro ao formatar os dados: {conteudo_top_sql}</p>"

    # 4) Conteúdo de print_backup (backups_consulta.txt)
    conteudo_print_backup = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/backups_consulta.txt").strip()
    try:
        data_backup = json.loads(conteudo_print_backup)
        if isinstance(data_backup, str):
            data_backup = json.loads(data_backup)
        if not isinstance(data_backup, list):
            raise ValueError("O conteúdo do backup não é uma lista de dicionários.")
        df_backup = pd.DataFrame(data_backup)
        df_backup = df_backup.rename(columns={
            "StartTime": "START_TIME",
            "EndTime": "END_TIME",
            "TotalOutputMBytes": "MBYTES",
            "BackupStatus": "STATUS",
            "BackupType": "INPUT_TYPE",
            "DayOfWeek": "DOW",
            "ElapsedSeconds": "SECONDS TAKEN"
        })
        dados["print_backup"] = df_backup.to_html(classes="tabela_cinza", index=False, border=0, justify="center")
    except Exception as e:
        logging.error(f"Erro ao converter print_backup para HTML: {e}")
        dados["print_backup"] = f"<p>Erro ao formatar os dados: {conteudo_print_backup}</p>"

    # 5) Conteúdo de informações do servidor (Info_serv_prod.txt) com formatação específica
    conteudo_info_servidor = ler_arquivo("/home/tauge/Documents/tauge/PGR/output/Info_serv_prod.txt").strip()
    if conteudo_info_servidor:
        linhas = conteudo_info_servidor.splitlines()
        conteudo_formatado = ""
        for linha in linhas:
            if ':' in linha:
                chave, valor = linha.split(':', 1)
                chave = chave.strip()
                valor = valor.strip().strip('"')  # Remove aspas se presentes
                conteudo_formatado += f"{chave}:<br>\"{valor}\"<br><br>"
            else:
                conteudo_formatado += f"{linha}<br><br>"
        dados["informacoes_servidor"] = conteudo_formatado
    else:
        dados["informacoes_servidor"] = "Nenhuma informação do servidor disponível."
    
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

    output_dir = "/home/tauge/Documents/tauge/PGR/output/pdf temp"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_file = os.path.join(output_dir, "pgr_final.pdf")

    pdfkit.from_string(output_text, output_file, configuration=config, options=options)
    print("PDF gerado com sucesso em:", output_file)

if __name__ == "__main__":
    dados_extraidos = obter_dados_do_banco()
    gerar_pdf(dados_extraidos)
