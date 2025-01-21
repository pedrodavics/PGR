import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import ipaddress

load_dotenv()

# Carregar variáveis de ambiente
host = os.getenv("HOST_DB")
port = os.getenv("PORT_DB")
dbname = os.getenv("NAME_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")
csv_file_path = os.getenv("PATH_CSV")

# Função para verificar se o IP é válido
def is_valid_ip(ip):
    try:
        # Tenta criar um objeto IP, se for válido retorna True
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        # Se lançar uma exceção, o IP é inválido
        return False

# Função para carregar dados do CSV
def fetch_data_from_csv(csv_file_path):
    try:
        df = pd.read_csv(csv_file_path)
        return df
    except Exception as e:
        print(f"Error loading data from CSV: {e}")
        return pd.DataFrame()

# Função para criar uma restrição de unicidade, se necessário
def create_unique_constraint_if_needed(cursor):
    cursor.execute("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'tb_cliente'::regclass AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'tb_cliente'::regclass AND attname = 'nome')];
    """)
    constraint = cursor.fetchone()

    if constraint is None:
        cursor.execute("""
            ALTER TABLE tb_cliente ADD CONSTRAINT unique_nome UNIQUE (nome);
        """)
        print("Unique constraint on 'nome' column added.")
    else:
        print("Unique constraint already exists on 'nome' column.")


def allow_null_on_nomebanco(cursor):
    cursor.execute("""
        ALTER TABLE tb_cliente ALTER COLUMN nomebanco DROP NOT NULL;
    """)
    print("Column 'nomebanco' now allows NULL values.")

def load_data_into_db(df):
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

        # Exibir dados após a inserção/atualização
        cursor.execute("SELECT * FROM tb_cliente;")
        rows = cursor.fetchall()

        print("Data in tb_cliente:")
        for row in rows:
            print(row)

        # Criar a restrição de unicidade, se necessário
        create_unique_constraint_if_needed(cursor)

        # Permitir NULL em nomebanco, caso necessário
        allow_null_on_nomebanco(cursor)

        # Agora, insira ou atualize os dados
        for _, row in df.iterrows():
            # Validar o IP antes de tentar inserir
            if not is_valid_ip(row["ip"]):
                print(f"Invalid IP address: {row['ip']}")
                continue  # Pula a linha com IP inválido

            query = """
                INSERT INTO tb_cliente (nome, ip, portassh, tpbanco, nomebanco, portabanco, idhostzbx)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (nome) DO UPDATE
                SET ip = EXCLUDED.ip,
                    portassh = EXCLUDED.portassh,
                    tpbanco = EXCLUDED.tpbanco,
                    nomebanco = EXCLUDED.nomebanco,
                    portabanco = EXCLUDED.portabanco,
                    idhostzbx = EXCLUDED.idhostzbx;
            """
            cursor.execute(query, (
                row["nome"], row["ip"], row["portassh"], row["tpbanco"], 
                row["nomebanco"], row["portabanco"], row["idhostzbx"]
            ))

        # Commit e fechamento da conexão
        connection.commit()
        connection.close()

        print("Data successfully inserted/updated in the database!")

    except Exception as e:
        print(f"Error inserting/updating data in the database: {e}")


# Função principal
if __name__ == "__main__":
    df = fetch_data_from_csv(csv_file_path)

    if not df.empty:
        load_data_into_db(df)
    else:
        print("No data found in the CSV file.")
