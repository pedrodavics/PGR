# Análise de Dependências e Tecnologias do PGR

## Bibliotecas Python

Com base no arquivo `requirements.txt` e na análise do código, as seguintes bibliotecas são utilizadas:

1. **pandas**: Manipulação e análise de dados, especialmente para formatação de tabelas nos relatórios
2. **numpy**: Computação numérica, utilizada em conjunto com pandas e plotly
3. **pyzabbix**: Cliente API para integração com o sistema de monitoramento Zabbix
4. **flask**: Framework web para possível interface web (não utilizado nos fluxos principais analisados)
5. **jaydebeapi**: Conector JDBC para Python, utilizado para conexão com bancos Oracle
6. **pdfkit**: Ferramenta para conversão de HTML para PDF usando wkhtmltopdf
7. **psycopg2-binary**: Driver PostgreSQL para Python, usado para conexão com o banco de configuração
8. **python-dotenv**: Carregamento de variáveis de ambiente a partir de arquivos .env
9. **tkinterweb**: Extensão do Tkinter para exibição de conteúdo web em aplicações desktop
10. **plotly**: Biblioteca para criação de gráficos interativos
11. **kaleido**: Engine para exportação de gráficos plotly para formatos estáticos
12. **scipy**: Biblioteca para computação científica, usada para cálculos estatísticos
13. **paramiko**: Implementação do protocolo SSH em Python, usado para conexão remota
14. **jinja2**: Engine de templates para Python, usado na geração de HTML
15. **pypdf**: Biblioteca para manipulação de arquivos PDF
16. **playwright**: Automação de navegadores web, possivelmente para captura de screenshots

## Ferramentas e Dependências Externas

1. **wkhtmltopdf**: Ferramenta de linha de comando para renderizar HTML em PDF (chamada pelo pdfkit)
2. **Java Runtime Environment (JRE)**: Necessário para o funcionamento do JDBC
3. **Oracle JDBC Driver**: Driver JAR para conexão com bancos Oracle
4. **PostgreSQL**: Banco de dados para armazenamento de configurações e informações dos clientes
5. **Zabbix Server**: Sistema de monitoramento para coleta de métricas de desempenho

## Ambiente e Configuração

1. **Python 3**: Linguagem de programação principal
2. **Ambiente Virtual Python**: Utilizado para isolamento de dependências
3. **Variáveis de Ambiente**: Configuradas via arquivo .env para armazenar credenciais e configurações
4. **VPN**: Necessária para conexão com os servidores dos clientes
5. **VM Dedicada**: Ambiente onde o código é executado, conectado à VPN

## Estrutura de Arquivos

1. **Arquivos Principais**:
   - `main.py`: Aplicação principal para bancos Oracle
   - `main copy.py`: Aplicação adaptada para SQL Server
   - `setup.sh`: Script de configuração do ambiente

2. **Diretórios**:
   - `src/`: Código-fonte dos módulos auxiliares
   - `static/assets/`: Recursos estáticos como templates HTML
   - `output/`: Diretório para armazenamento dos relatórios gerados
   - `logs/`: Arquivos de log da aplicação

## Requisitos de Sistema

1. **Sistema Operacional**: Linux (testado em ambiente Ubuntu)
2. **Memória**: Suficiente para processar relatórios PDF e executar consultas SQL
3. **Armazenamento**: Espaço para armazenar relatórios gerados e arquivos temporários
4. **Rede**: Acesso à VPN para conexão com servidores dos clientes
5. **Permissões**: Acesso SSH aos servidores dos clientes e permissões de leitura nos bancos de dados

## Processo de Instalação

O processo de instalação é gerenciado pelo script `setup.sh`, que realiza as seguintes etapas:

1. Criação de um ambiente virtual Python: `python3 -m venv .venv`
2. Ativação do ambiente virtual: `source .venv/bin/activate`
3. Instalação das dependências: `python -m pip install -r requirements.txt`

Além disso, é necessário:
1. Configurar o arquivo `.env` com as credenciais necessárias
2. Garantir que o wkhtmltopdf esteja instalado no sistema
3. Configurar o driver JDBC para Oracle
4. Garantir acesso à VPN para conexão com os servidores dos clientes
