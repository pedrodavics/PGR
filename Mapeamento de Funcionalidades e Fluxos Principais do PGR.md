# Mapeamento de Funcionalidades e Fluxos Principais do PGR

## Visão Geral

O PGR (Plataforma de Gestão de Relatório) é uma aplicação desenvolvida para automatizar a geração de relatórios situacionais para clientes da Tauge. A aplicação coleta dados de diferentes fontes (bancos de dados, servidores e Zabbix) e os organiza em relatórios PDF formatados.

## Fluxos Principais

### 1. Fluxo para Bancos Oracle (main.py)

1. **Autenticação e Seleção de Cliente**:
   - O usuário inicia a aplicação através da interface gráfica
   - Seleciona um cliente da lista carregada do banco de dados PostgreSQL
   - Fornece seu nome de usuário para registro de atividade

2. **Coleta de Dados**:
   - Conexão SSH com o servidor do cliente usando credenciais armazenadas
   - Execução de comandos no sistema operacional remoto para coletar informações do servidor
   - Conexão JDBC com o banco Oracle para executar consultas SQL
   - Integração com a API do Zabbix para obter gráficos de monitoramento (CPU e memória RAM)

3. **Processamento e Formatação**:
   - Execução do script app_graphics.py para processar os gráficos do Zabbix
   - Execução do script formatter.py para formatar os dados coletados em HTML
   - Conversão do HTML para PDF usando pdfkit/wkhtmltopdf

4. **Finalização**:
   - Execução do script mergepdf.py para combinar o PDF gerado com um template
   - Renomeação do arquivo final com o nome do cliente e mês atual
   - Limpeza de arquivos temporários

### 2. Fluxo para Bancos SQL Server (main copy.py)

1. **Autenticação e Seleção de Cliente**:
   - Similar ao fluxo Oracle, mas com interface adaptada para SQL Server
   - Seleção de cliente da lista carregada do banco de dados PostgreSQL
   - Fornecimento de nome de usuário para registro de atividade

2. **Coleta de Dados**:
   - Sem conexão SSH direta (diferente do fluxo Oracle)
   - Coleta de dados diretamente via API do Zabbix usando rotinas pré-configuradas
   - Leitura de arquivos de consulta gerados por rotinas do Zabbix

3. **Processamento e Formatação**:
   - Uso do script formatter_sqlserver.py para processar os dados coletados
   - Formatação dos dados em HTML usando templates Jinja2
   - Conversão do HTML para PDF usando pdfkit/wkhtmltopdf

4. **Finalização**:
   - Execução do script mergepdf.py para combinar o PDF gerado com um template
   - Renomeação do arquivo final com o nome do cliente e mês atual
   - Limpeza de arquivos temporários

### 3. Integração com Zabbix (ultima_consulta.py)

1. **Autenticação na API do Zabbix**:
   - Conexão com a API do Zabbix usando credenciais armazenadas em variáveis de ambiente
   - Validação e ajuste da URL da API

2. **Obtenção de Dados**:
   - Carregamento de informações do cliente a partir de arquivos JSON
   - Consulta de itens específicos na API do Zabbix usando IDs armazenados
   - Obtenção dos últimos valores registrados para cada item monitorado

3. **Processamento de Gráficos**:
   - Download de gráficos de CPU e memória RAM do último mês
   - Salvamento dos gráficos em formato PNG para inclusão no relatório

4. **Armazenamento de Resultados**:
   - Salvamento das consultas em arquivos de texto separados
   - Formatação dos dados para uso posterior pelos scripts de geração de PDF

### 4. Geração de PDF (formatter.py, formatter_sqlserver.py, mergepdf.py)

1. **Coleta e Formatação de Dados**:
   - Leitura dos arquivos de dados gerados nas etapas anteriores
   - Formatação dos dados em tabelas HTML usando pandas
   - Aplicação de estilos e formatação visual

2. **Renderização do Template**:
   - Uso do template HTML (pgr.html) com placeholders para os dados
   - Renderização do template usando Jinja2 com os dados coletados

3. **Conversão para PDF**:
   - Conversão do HTML renderizado para PDF usando pdfkit/wkhtmltopdf
   - Aplicação de configurações de página e margens

4. **Mesclagem com Template**:
   - Combinação do PDF gerado com um template PDF pré-existente
   - Substituição de páginas específicas do template com as páginas geradas
   - Geração do relatório final em formato PDF

## Componentes Principais

1. **Interface Gráfica**:
   - Implementada com Tkinter e TkinterWeb
   - Permite seleção de cliente e entrada de nome de usuário
   - Exibe progresso e mensagens durante a geração do relatório

2. **Banco de Dados de Configuração**:
   - PostgreSQL armazenando informações dos clientes
   - Tabelas para autenticação, clientes, servidores e URLs do Zabbix

3. **Módulos de Conexão**:
   - SSH via Paramiko para execução de comandos remotos
   - JDBC via JayDeBeApi para conexão com bancos Oracle
   - API Zabbix via PyZabbix para monitoramento

4. **Geração de Relatórios**:
   - Templates HTML com Jinja2
   - Conversão HTML para PDF com pdfkit
   - Manipulação de PDFs com PyPDF

5. **Utilitários**:
   - Logging para registro de atividades
   - Manipulação de arquivos JSON para armazenamento de configurações
   - Limpeza de arquivos temporários após processamento
