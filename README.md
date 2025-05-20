# 📊 Plataforma de Gestão de Relatório (PGR)

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue.svg" alt="Python 3.x">
  <img src="https://img.shields.io/badge/Zabbix-API-red.svg" alt="Zabbix API">
  <img src="https://img.shields.io/badge/Oracle-JDBC-orange.svg" alt="Oracle JDBC">
  <img src="https://img.shields.io/badge/SQL%20Server-Support-green.svg" alt="SQL Server">
  <img src="https://img.shields.io/badge/PDF-Reports-lightgrey.svg" alt="PDF Reports">
</div>

## 📚 Descrição do Projeto

A **Plataforma de Gestão de Relatório (PGR)** é um sistema desenvolvido para automatizar a geração de relatórios situacionais a partir de dados coletados diretamente dos bancos de dados, servidores e gráficos gerados pelo Zabbix. Ele visa otimizar o processo de coleta, organização e apresentação de informações para os clientes da Tauge.

O PGR foi projetado para atender às necessidades de sustentação de banco de dados, máquinas e infraestrutura, permitindo a geração de relatórios mensais que apresentam o estado atual dos sistemas dos clientes, incluindo métricas de desempenho, informações de backup e dados de crescimento de bases.

---

## ⚙️ Funcionalidades Principais

- **🤖 Automatização da Geração de Relatórios**: A plataforma coleta dados situacionais de diferentes fontes e os organiza em relatórios formatados.
- **🔒 Conexão Segura**: Utiliza conexões seguras via SSH e HTTPS para coletar dados.
- **📈 Download de Gráficos**: Integra-se ao Zabbix para obter gráficos de CPU e memória RAM do último mês.
- **🔍 Análise de Banco de Dados**: Coleta informações sobre versão, maiores tabelas, índices e consultas mais lentas.
- **💾 Monitoramento de Backup**: Verifica e reporta o status dos backups realizados.
- **📋 Interface Gráfica Intuitiva**: Interface desktop para seleção de clientes e geração de relatórios.
- **📝 Registro de Atividades**: Registra os usuários que geram relatórios para fins de auditoria.
- **🔄 Suporte a Múltiplos SGBDs**: Compatível com Oracle e SQL Server.

---

## 🛠️ Como Funciona

A PGR realiza a coleta de dados a partir de diferentes fontes e organiza essas informações em relatórios PDF prontos para serem revisados e enviados aos clientes.

### 1. Coleta de Dados

A coleta de dados é feita a partir de três métodos diferentes:

#### 📂 1.1 Coleta de Dados de Bancos de Dados

- Conexão via **JDBC (Java Database Connector)** para Oracle.
- Coleta direta via API do Zabbix para SQL Server.
- O sistema executa consultas SQL predefinidas e retorna as informações em arquivos estruturados.

#### 🖥️ 1.2 Execução de Comandos no Sistema Operacional

- Conexão via **SSH** em servidores remotos.
- O sistema executa comandos como `hostname`, `ifconfig`, `cat /etc/*release`, `df -h` e `free -h`.
- Os resultados são salvos para inclusão no relatório final.

#### 📊 1.3 Requisições ao Zabbix

- Utilização do **PyZabbix** para interagir com a API do Zabbix.
- Download de gráficos de CPU e memória RAM do último mês.
- Obtenção de métricas de desempenho para análise.

### 2. Processamento de Dados

- **🔄 Formatação**: Os dados coletados são processados e formatados.
- **📊 Geração de Tabelas**: Utiliza pandas para criar tabelas HTML formatadas.
- **🎨 Renderização de Templates**: Usa Jinja2 para aplicar os dados ao template HTML.

### 3. Geração de PDF

- **📄 Conversão HTML para PDF**: Utiliza pdfkit/wkhtmltopdf para converter o HTML em PDF.
- **📑 Mesclagem com Template**: Combina o PDF gerado com um template pré-existente.
- **📋 Relatório Final**: Gera o relatório final com o nome do cliente e mês atual.

---

## 📄 Apresentação dos Dados

Após a coleta e processamento, o sistema gera um relatório PDF completo contendo:

- **👤 Informações do Administrador de Banco de Dados (DBA)**
- **🖥️ Informações do Servidor Produtivo**
- **🔢 Versão do Banco de Dados**
- **📊 Maiores Tabelas e Índices**
- **⏱️ Top SQL com Maior Tempo de Processamento**
- **📈 Gráficos de Monitoramento de CPU e Memória**
- **📊 Crescimento da Base de Dados**
- **💾 Status e Histórico de Backups**

O relatório fica disponível para que o **Gerente de Projetos** possa revisá-lo e personalizá-lo antes de encaminhar aos clientes.

---

## 🚀 Tecnologias Utilizadas

### 🐍 Python e Bibliotecas

- **pandas**: Manipulação e análise de dados
- **numpy**: Computação numérica
- **pyzabbix**: Cliente API para Zabbix
- **flask**: Framework web
- **jaydebeapi**: Conector JDBC para Python
- **pdfkit**: Conversão de HTML para PDF
- **psycopg2-binary**: Driver PostgreSQL
- **python-dotenv**: Carregamento de variáveis de ambiente
- **tkinterweb**: Extensão do Tkinter para conteúdo web
- **plotly**: Criação de gráficos
- **kaleido**: Exportação de gráficos plotly
- **scipy**: Computação científica
- **paramiko**: Implementação SSH
- **jinja2**: Engine de templates
- **pypdf**: Manipulação de PDFs
- **playwright**: Automação de navegadores

### 🔧 Ferramentas e Dependências Externas

- **☕ Java Runtime Environment (JRE)**: Para JDBC
- **🌐 wkhtmltopdf**: Conversão de HTML para PDF
- **🗄️ PostgreSQL**: Banco de dados de configuração
- **📊 Zabbix Server**: Sistema de monitoramento
- **🔒 SSH**: Comunicação segura com servidores

---

## 🔧 Requisitos de Sistema

### 💻 Software

- **Python 3.x**
- **Java Runtime Environment (JRE)** para JDBC
- **wkhtmltopdf** para conversão de HTML para PDF
- **PostgreSQL** para armazenamento de configurações
- **Acesso à VPN** para conexão com servidores dos clientes

### 🖥️ Hardware

- **VM dedicada** conectada à VPN da Tauge
- **Memória suficiente** para processamento de relatórios
- **Espaço em disco** para armazenamento de relatórios e arquivos temporários

---

## 📥 Instalação e Configuração

### 1. Preparação do Ambiente

```bash
# Clone o repositório
git clone https://github.com/pedrodavics/PGR.git
cd PGR

# Execute o script de setup
chmod +x setup.sh
./setup.sh
```

### 2. Configuração do Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

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

---

## 🖱️ Uso da Aplicação

### Para Bancos Oracle

```bash
python main.py
```

### Para Bancos SQL Server

```bash
python "main copy.py"
```

### Fluxo de Uso

1. **👤 Selecione um cliente** da lista carregada do banco de dados
2. **✏️ Forneça seu nome de usuário** para registro de atividade
3. **⏳ Aguarde** enquanto o sistema coleta e processa os dados
4. **📄 Acesse o relatório gerado** na pasta `output`

---

## 📁 Estrutura de Diretórios

```
PGR/
├── src/                            # Código-fonte dos módulos auxiliares
│   └── apps/                       # Scripts auxiliares
│       ├── app_graphics.py         # Processamento de gráficos do Zabbix
│       ├── formatter.py            # Formatação de dados para Oracle
│       ├── formatter_sqlserver.py  # Formatação para SQL Server
│       └── mergepdf.py             # Mesclagem de PDFs
├── static/                         # Recursos estáticos
│   └── assets/                     # Templates e recursos
│       ├── pgr.html                # Template HTML para o relatório
│       └── template pgr final.pdf  # Template PDF base
├── output/                         # Diretório para relatórios gerados
├── logs/                           # Arquivos de log
├── main.py                         # Aplicação principal para Oracle
├── main copy.py                    # Aplicação adaptada para SQL Server
├── requirements.txt                # Dependências Python
└── setup.sh                        # Script de configuração
```

---

## 🔍 Fluxos Detalhados

### 🔶 Fluxo para Bancos Oracle (main.py)

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

### 🔷 Fluxo para Bancos SQL Server (main copy.py)

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

---

## 🔧 Manutenção e Suporte

### 👥 Adição de Novos Clientes

Para adicionar um novo cliente, é necessário inserir seus dados nas tabelas do PostgreSQL:

1. Inserir informações básicas na tabela `tb_cliente`
2. Inserir informações do servidor na tabela `tb_servidor`
3. Inserir IDs dos itens do Zabbix na tabela `tb_urlzbx`

### 🔍 Solução de Problemas Comuns

- **Problemas de Conexão SSH**: Verificar VPN, credenciais e firewall
- **Problemas de Conexão JDBC**: Verificar driver, caminho do JAR e credenciais
- **Problemas na Geração de PDF**: Verificar wkhtmltopdf e caminhos das imagens
- **Problemas na API do Zabbix**: Verificar URL, credenciais e logs

---

## 📋 Estrutura de Banco de Dados

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

---

## 📧 Contato

Para mais informações ou suporte, entre em contato com a equipe de desenvolvimento da Tauge:

- **👨‍💻 Pedro Davi Capistrano de Sá**: [davi.capistrano@tauge.com.br](mailto:davi.capistrano@tauge.com.br)
- **👨‍💻 Arthur Veras**: [arthur.veras@tauge.com.br](mailto:arthur.veras@tauge.com.br)

---

<div align="center">
  <p>© 2025 Tauge - Todos os direitos reservados</p>
</div>
