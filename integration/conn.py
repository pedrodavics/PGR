import os
import pandas as pd
import psycopg2
import subprocess

# Configurações do banco de dados
host = "10.85.104.6"
port = "5432"
dbname = "dbreport"
user = "tgreport"
password = "tgreport"
csv_file = "./static/csv/base de clientes.csv"
db_folder = "integration/.db/"

# Garantir que a pasta db dentro de integration seja criada
os.makedirs(db_folder, exist_ok=True)

try:
    # Conectar ao banco de dados
    connection = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )
    cursor = connection.cursor()

    # Criar tabela nome_do_cliente
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nome_do_cliente (
            nome_do_cliente TEXT PRIMARY KEY,
            chave_de_ip TEXT,
            grupo_id INTEGER,
            porta_ssh INTEGER
        );
    """)
    connection.commit()

    # Carregar dados do arquivo CSV
    df = pd.read_csv(csv_file)
    print("Colunas no arquivo CSV:", df.columns.tolist())

    # Renomear colunas para o padrão esperado pelo banco de dados
    df.rename(columns={
        "Nome do cliente": "nome_do_cliente",
        "Chave de IP": "chave_de_ip",
        "Grupo ID": "grupo_id",
        "Porta SSH": "porta_ssh"
    }, inplace=True)

    df.drop(columns={

        
    }})

    print("Colunas após renomeação:", df.columns.tolist())

    # Verificar se todas as colunas necessárias estão presentes
    required_columns = ["nome_do_cliente", "chave_de_ip", "grupo_id", "porta_ssh"]
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"As colunas obrigatórias estão ausentes no CSV. Esperado: {required_columns}")

    # Inserir dados no banco de dados
    for _, row in df.iterrows():
        insert_query = """
        INSERT INTO nome_do_cliente (nome_do_cliente, chave_de_ip, grupo_id, porta_ssh)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (nome_do_cliente) DO NOTHING;
        """
        cursor.execute(
            insert_query,
            (row["nome_do_cliente"], row["chave_de_ip"], row["grupo_id"], row["porta_ssh"])
        )
    connection.commit()

    # Exibir os dados da tabela
    cursor.execute("SELECT * FROM nome_do_cliente;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

except Exception as e:
    print(f"Erro durante a execução: {e}")

finally:
    # Fechar a conexão com o banco de dados
    if 'connection' in locals() and connection:
        connection.close()

# Exportar o banco de dados para a pasta db dentro de integration
backup_file = os.path.join(db_folder, f"{dbname}_backup.sql")
export_command = f"pg_dump -h {host} -p {port} -U {user} -F c -b -v -f {backup_file} {dbname}"

try:
    subprocess.run(export_command, shell=True, check=True, env={"PGPASSWORD": password})
    print(f"Backup exportado com sucesso para: {backup_file}")
except subprocess.CalledProcessError as e:
    print(f"Erro ao exportar o banco de dados: {e}")
