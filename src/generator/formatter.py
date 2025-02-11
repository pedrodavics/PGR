import jinja2
import pdfkit

# Dados para preenchimento do template
informacoes_servidor = "exemplo1"
versao_do_banco_de_dados = "exemplo27"
maiores_tabelas = "exemplo28"
top_sql = "exemplo29"
monitoramento_memoria = "exemplo30"
monitoramento_cpu = "exemplo31"
crescimento_base = "exemplo32"
desvios_backup = "exemplo33"
nao_houveram_desvios = "exemplo34"  # Removido caractere especial
data_backup = "exemplo35"
desvio_backup = "exemplo36"
acao_backup = "exemplo37"
status_backup = "exemplo38"

# Criando o dicionário de contexto para o template
context = {
    'informacoes_servidor': informacoes_servidor,
    'versao_do_banco_de_dados': versao_do_banco_de_dados,
    'maiores_tabelas': maiores_tabelas,
    'top_sql': top_sql,
    'monitoramento_memoria': monitoramento_memoria,
    'monitoramento_cpu': monitoramento_cpu,
    'crescimento_base': crescimento_base,
    'desvios_backup': desvios_backup,
    'nao_houveram_desvios': nao_houveram_desvios,
    'data_backup': data_backup,
    'desvio_backup': desvio_backup,
    'acao_backup': acao_backup,
    'status_backup': status_backup,
}

# Configurando Jinja2 para carregar templates
template_loader = jinja2.FileSystemLoader('./')
template_env = jinja2.Environment(loader=template_loader)

try:
    template = template_env.get_template("static/assets/pgr.html")
except jinja2.exceptions.TemplateNotFound:
    print("Erro: O template 'pgr.html' não foi encontrado. Verifique o nome e o local do arquivo.")
    exit(1)

# Renderiza o template com os dados do contexto
output_text = template.render(context)

# Configuração correta do wkhtmltopdf para Linux (Debian)
config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")

# Definição de opções para geração do PDF
options = {
    "encoding": "UTF-8"
}

# Gerando o PDF
pdfkit.from_string(output_text, 'pgrdavi.pdf', configuration=config, options=options)

print("PDF gerado com sucesso!")
