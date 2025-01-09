import psycopg2
from psycopg2 import sql

host = "10.85.104.6"        # Use 'localhost' se o banco estiver na mesma máquina
port = "5432"             # Porta padrão do PostgreSQL
dbname = "dbreport"       # Nome do banco de dados
user = "tgreport"         # Usuário do banco de dados
password = "tgreport"     # Senha do usuário

try:
    connection = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )
    print("Conexão com o banco de dados realizada com sucesso!")

    cursor = connection.cursor()

    # Executa um comando para verificar a versão do PostgreSQL
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f"Versão do PostgreSQL: {db_version[0]}")

    cursor.close()

except psycopg2.Error as e:
    print(f"Erro ao conectar ao banco de dados: {e}")

finally:
    # Certifique-se de fechar a conexão corretamente
    try:
        connection.close()
        print("Conexão com o banco de dados encerrada.")
    except NameError:
        print("A conexão não foi criada. Nada para encerrar.")
