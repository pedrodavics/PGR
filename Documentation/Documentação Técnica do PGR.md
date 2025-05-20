# Documentação Técnica do PGR

## Introdução

A **Plataforma de Gestão de Relatório (PGR)** é uma aplicação desenvolvida pela Tauge para automatizar a geração de relatórios situacionais para seus clientes. Esta documentação técnica detalha a arquitetura, os componentes, os fluxos de trabalho e os requisitos técnicos do sistema.

## Arquitetura do Sistema

### Visão Geral

O PGR é uma aplicação Python que utiliza uma arquitetura modular para coletar, processar e apresentar dados de diferentes fontes. A aplicação é executada em uma VM conectada à VPN da Tauge, permitindo acesso seguro aos servidores dos clientes.

### Componentes Principais

#### 1. Interface de Usuário

- Implementada com **Tkinter** e **TkinterWeb**
- Permite a seleção de clientes a partir de uma lista carregada do banco de dados
- Registra o usuário que está gerando o relatório para fins de auditoria
- Exibe feedback visual durante o processo de geração de relatórios

#### 2. Módulo de Coleta de Dados

**Para bancos Oracle (main.py):**
- Conexão SSH via **Paramiko** para execução de comandos no servidor remoto
- Conexão JDBC via **JayDeBeApi** para execução de consultas SQL no banco Oracle
- Integração com a API do Zabbix via **PyZabbix** para obtenção de gráficos de monitoramento

**Para bancos SQL Server (main copy.py):**
- Coleta de dados diretamente via API do Zabbix usando rotinas pré-configuradas
- Leitura de arquivos de consulta gerados por rotinas do Zabbix

#### 3. Módulo de Processamento de Dados

- **Pandas** e **NumPy** para manipulação e análise de dados
- **Plotly** e **Kaleido** para geração e exportação de gráficos
- **Jinja2** para renderização de templates HTML com os dados coletados

#### 4. Módulo de Geração de PDF

- **pdfkit** para conversão de HTML para PDF (requer **wkhtmltopdf**)
- **PyPDF** para mesclagem do PDF gerado com um template pré-existente
- Formatação e estilização via CSS no template HTML

#### 5. Banco de Dados de Configuração

- **PostgreSQL** para armazenamento de configurações e informações dos clientes
- Tabelas para clientes, servidores, URLs do Zabbix e registro de atividades

## Fluxos de Trabalho Detalhados

### Fluxo para Bancos Oracle

1. **Inicialização e Autenticação**
   - O usuário inicia a aplicação através do `main.py`
   - A interface gráfica é carregada com a lista de clientes do PostgreSQL
   - O usuário seleciona um cliente e fornece seu nome de usuário

2. **Coleta de Dados do Servidor**
   - O sistema estabelece conexão SSH com o servidor do cliente
   - Comandos como `hostname`, `ifconfig`, `cat /etc/*release`, `df -h` e `free -h` são executados
   - Os resultados são salvos em arquivos de texto para processamento posterior

3. **Coleta de Dados do Banco Oracle**
   - Conexão JDBC é estabelecida com o banco Oracle
   - Consultas SQL são executadas para obter:
     - Versão do banco de dados
     - Maiores tabelas e índices
     - Top SQL com maior tempo de processamento
     - Informações de backup
     - Dados de crescimento da base

4. **Obtenção de Gráficos do Zabbix**
   - Conexão com a API do Zabbix é estabelecida
   - Gráficos de CPU e memória RAM do último mês são obtidos
   - Os gráficos são salvos como imagens PNG

5. **Processamento e Formatação**
   - O script `app_graphics.py` processa os gráficos do Zabbix
   - O script `formatter.py` formata os dados coletados em HTML usando Jinja2
   - O HTML é convertido para PDF usando pdfkit/wkhtmltopdf

6. **Finalização do Relatório**
   - O script `mergepdf.py` combina o PDF gerado com um template pré-existente
   - O arquivo final é renomeado com o nome do cliente e mês atual
   - Arquivos temporários são removidos

### Fluxo para Bancos SQL Server

1. **Inicialização e Autenticação**
   - O usuário inicia a aplicação através do `main copy.py`
   - A interface gráfica é carregada com a lista de clientes do PostgreSQL
   - O usuário seleciona um cliente e fornece seu nome de usuário

2. **Coleta de Dados via Zabbix**
   - O sistema obtém dados diretamente via API do Zabbix
   - Consultas específicas são executadas com base nos IDs armazenados
   - Os resultados são salvos em arquivos de texto para processamento posterior

3. **Processamento e Formatação**
   - O script `formatter_sqlserver.py` processa os dados coletados
   - Os dados são formatados em HTML usando Jinja2 e pandas
   - O HTML é convertido para PDF usando pdfkit/wkhtmltopdf

4. **Finalização do Relatório**
   - O script `mergepdf.py` combina o PDF gerado com um template pré-existente
   - O arquivo final é renomeado com o nome do cliente e mês atual
   - Arquivos temporários são removidos

## Estrutura de Banco de Dados

### Tabela tb_cliente

Armazena informações dos clientes e credenciais de acesso:

| Campo      | Tipo    | Descrição                                |
|------------|---------|------------------------------------------|
| idcliente  | INTEGER | Identificador único do cliente           |
| nome       | TEXT    | Nome do cliente                          |
| ip         | TEXT    | Endereço IP do servidor                  |
| portassh   | INTEGER | Porta SSH                                |
| tpbanco    | TEXT    | Tipo de banco (Oracle, SQL Server)       |
| nomebanco  | TEXT    | Nome do banco de dados                   |
| portabanco | INTEGER | Porta do banco de dados                  |
| idhostzbx  | TEXT    | ID do host no Zabbix                     |
| userssh    | TEXT    | Usuário SSH                              |
| senhassh   | TEXT    | Senha SSH                                |
| db_type    | TEXT    | Tipo de banco (usado em main copy.py)    |

### Tabela tb_servidor

Armazena informações detalhadas dos servidores:

| Campo       | Tipo    | Descrição                                |
|-------------|---------|------------------------------------------|
| id          | INTEGER | Identificador único do servidor          |
| nome        | TEXT    | Nome do servidor (referência ao cliente) |
| hostname    | TEXT    | Nome do host                             |
| ip          | TEXT    | Endereço IP                              |
| os_version  | TEXT    | Versão do sistema operacional            |
| disk_space  | TEXT    | Espaço em disco                          |
| memory      | TEXT    | Memória RAM                              |

### Tabela tb_urlzbx

Armazena URLs e IDs de itens do Zabbix:

| Campo       | Tipo    | Descrição                                |
|-------------|---------|------------------------------------------|
| id          | INTEGER | Identificador único                      |
| nome        | TEXT    | Nome do cliente (referência)             |
| item_id_1   | TEXT    | ID do item 1 no Zabbix                   |
| item_id_2   | TEXT    | ID do item 2 no Zabbix                   |
| ...         | ...     | ...                                      |

### Tabela tb_autentificacao

Registra atividades dos usuários:

| Campo       | Tipo      | Descrição                                |
|-------------|-----------|------------------------------------------|
| id          | INTEGER   | Identificador único                      |
| username    | TEXT      | Nome do usuário                          |
| ipmaquina   | TEXT      | IP da máquina do usuário                 |
| horario     | TIMESTAMP | Data e hora da atividade                 |
| cliente     | TEXT      | Cliente selecionado                      |

## Requisitos Técnicos Detalhados

### Requisitos de Software

- **Python 3.x**
- **Java Runtime Environment (JRE)** versão 8 ou superior
- **wkhtmltopdf** versão 0.12.6 ou superior
- **PostgreSQL** versão 10 ou superior
- **Oracle JDBC Driver** (ojdbc8.jar)
- **Acesso à VPN** da Tauge

### Requisitos de Hardware

- **VM dedicada** com pelo menos 4GB de RAM
- **Espaço em disco** de pelo menos 10GB para armazenamento de relatórios e arquivos temporários
- **Conexão de rede** estável para acesso aos servidores dos clientes

### Variáveis de Ambiente

O arquivo `.env` deve conter as seguintes variáveis:

```
# Banco de dados PostgreSQL (configuração)
HOST_DB=localhost
PORT_DB=5432
NAME_DB=pgr_db
USER_DB=pgr_user
PASS_DB=pgr_password

# Zabbix
URL_ZBX=https://zabbix.example.com
USER_ZBX=api_user
PASS_ZBX=api_password

# JDBC (para Oracle)
USER_JDBC=jdbc_user
PASS_JDBC=jdbc_password
JAR_JDBC=/path/to/ojdbc8.jar

# Tabelas PostgreSQL
CLIENT_TABLE=tb_cliente
SERV_TABLE=tb_servidor
URLZBX_TABLE=tb_urlzbx
```

## Estrutura de Diretórios Detalhada

```
PGR/
├── src/                  # Código-fonte dos módulos auxiliares
│   └── apps/             # Scripts auxiliares
│       ├── app_graphics.py  # Processamento de gráficos do Zabbix
│       ├── formatter.py     # Formatação de dados para Oracle
│       ├── formatter_sqlserver.py  # Formatação de dados para SQL Server
│       └── mergepdf.py      # Mesclagem de PDFs
├── static/               # Recursos estáticos
│   └── assets/           # Templates e recursos
│       ├── pgr.html         # Template HTML para o relatório
│       └── template pgr final.pdf  # Template PDF base
├── output/               # Diretório para relatórios gerados
│   ├── graphics/         # Gráficos gerados
│   ├── pdf temp/         # PDFs temporários
│   └── reports/          # Relatórios de consultas
├── logs/                 # Arquivos de log
│   ├── zabbix.log        # Logs da integração com Zabbix
│   └── pdf.log           # Logs da geração de PDF
├── main.py               # Aplicação principal para Oracle
├── main copy.py          # Aplicação adaptada para SQL Server
├── requirements.txt      # Dependências Python
└── setup.sh              # Script de configuração
```

## Manutenção e Extensão

### Adição de Novos Clientes

Para adicionar um novo cliente, é necessário inserir seus dados nas tabelas do PostgreSQL:

1. Inserir informações básicas na tabela `tb_cliente`
2. Inserir informações do servidor na tabela `tb_servidor`
3. Inserir IDs dos itens do Zabbix na tabela `tb_urlzbx`

### Modificação de Consultas SQL

As consultas SQL estão definidas nos arquivos `formatter.py` e `formatter_sqlserver.py`. Para modificar ou adicionar novas consultas:

1. Editar a função `obter_dados_do_banco()` no arquivo correspondente
2. Adicionar a nova consulta ao dicionário `consultas`
3. Atualizar o template HTML (`pgr.html`) para exibir os novos dados

### Personalização do Relatório

O layout do relatório é definido no arquivo `pgr.html`. Para personalizar o relatório:

1. Editar o arquivo HTML e os estilos CSS
2. Atualizar as referências aos placeholders no template Jinja2
3. Ajustar o script `mergepdf.py` se necessário para mesclar corretamente as páginas

## Solução de Problemas

### Problemas de Conexão SSH

- Verificar se a VM está conectada à VPN da Tauge
- Confirmar se as credenciais SSH no banco de dados estão corretas
- Verificar se a porta SSH está aberta no firewall do servidor

### Problemas de Conexão JDBC

- Verificar se o driver JDBC está corretamente configurado
- Confirmar se o caminho para o arquivo JAR está correto no `.env`
- Verificar se as credenciais do banco de dados estão corretas

### Problemas na Geração de PDF

- Verificar se o wkhtmltopdf está instalado corretamente
- Confirmar se os caminhos para as imagens no HTML são absolutos
- Verificar os logs em `logs/pdf.log` para mensagens de erro específicas

### Problemas na API do Zabbix

- Verificar se a URL da API está correta no `.env`
- Confirmar se as credenciais do Zabbix estão corretas
- Verificar os logs em `logs/zabbix.log` para mensagens de erro específicas

## Conclusão

O PGR é uma ferramenta poderosa para automatizar a geração de relatórios situacionais para os clientes da Tauge. Com sua arquitetura modular e fluxos de trabalho bem definidos, o sistema pode ser facilmente mantido e estendido para atender a novos requisitos e tipos de banco de dados.
