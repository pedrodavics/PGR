import os
import pandas as pd
import psycopg2
import subprocess

# Configurações de conexão com o banco
host = "10.85.104.6"
port = "5432"
dbname = "dbreport"
user = "tgreport"
password = "tgreport"
csv_file = "./static/csv/base de clientes - IP _ ID_ SSH.csv"
db_folder = "./db"

# Criar a pasta para o backup, se não existir
os.makedirs(db_folder, exist_ok=True)
print(f"Pasta '{db_folder}' criada ou já existente.")

try:
    # Conexão com o banco
    connection = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )
    print("Conexão com o banco de dados realizada com sucesso!")
    cursor = connection.cursor()

    tables_to_keep = ["nome_do_cliente", "chave_de_ip", "grupo_id", "porta_ssh"]
    cursor.execute(
        """
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public';
        """
    )
    all_tables = [row[0] for row in cursor.fetchall()]
    tables_to_drop = [table for table in all_tables if table not in tables_to_keep]
    
    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        print(f"Tabela '{table}' removida.")
    connection.commit()

    # Ajustar tabelas: dropar colunas desnecessárias
    for table in tables_to_keep:
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}';")
        columns = [row[0] for row in cursor.fetchall()]
        for column in columns:
            if column not in ["id", "nome_do_cliente", "chave_de_ip", "grupo_id", "porta_ssh"]:
                cursor.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column};")
                print(f"Coluna '{column}' removida da tabela '{table}'.")
    connection.commit()

    # Carregar dados do CSV e inserir no banco
    df = pd.read_csv(csv_file)
    print(f"Arquivo CSV '{csv_file}' carregado com sucesso!")
    
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
    print("Dados do CSV inseridos com sucesso!")

except Exception as e:
    print(f"Erro durante a execução: {e}")

finally:
    if 'connection' in locals() and connection:
        connection.close()
        print("Conexão com o banco de dados encerrada.")

# Exportar o banco de dados atualizado
backup_file = os.path.join(db_folder, f"{dbname}_backup.sql")
export_command = f"pg_dump -h {host} -p {port} -U {user} -F c -b -v -f {backup_file} {dbname}"

try:
    print(f"Exportando banco de dados para '{backup_file}'...")
    subprocess.run(export_command, shell=True, check=True, env={"PGPASSWORD": password})
    print(f"Banco de dados exportado com sucesso para '{backup_file}'.")
except subprocess.CalledProcessError as e:
    print(f"Erro ao exportar o banco de dados: {e}")
