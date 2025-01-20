import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

# Carregar variáveis de ambiente
host = os.getenv("HOST_DB")
port = os.getenv("PORT_DB")
dbname = os.getenv("NAME_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")

# Variáveis do Google Sheets
sheet_url = os.getenv("URL_SHEET")
sheet_name = os.getenv("NAME_SHEET")

def fetch_data_from_sheets(sheet_url, sheet_name):
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_file("credenciais.json", scopes=scopes)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_records()

        df = pd.DataFrame(data)
        return df
    
    except Exception as e:
        print(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

def load_data_into_db(df):
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        cursor = connection.cursor()

        for _, row in df.iterrows():
            query = """
                INSERT INTO tb_cliente (nome, ip, portassh, tpbanco, portabanco, idhostzbx)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (nome) DO UPDATE
                SET ip = EXCLUDED.ip,
                    portassh = EXCLUDED.portassh,
                    tpbanco = EXCLUDED.tpbanco,
                    portabanco = EXCLUDED.portabanco,
                    idhostzbx = EXCLUDED.idhostzbx
                WHERE tb_cliente.ip != EXCLUDED.ip
                   OR tb_cliente.portassh != EXCLUDED.portassh
                   OR tb_cliente.tpbanco != EXCLUDED.tpbanco
                   OR tb_cliente.portabanco != EXCLUDED.portabanco
                   OR tb_cliente.idhostzbx != EXCLUDED.idhostzbx;
            """
            cursor.execute(query, (row["nome"], row["ip"], row["portassh"], row["tpbanco"], row["portabanco"], row["idhostzbx"]))

        connection.commit()
        connection.close()

        print("Dados inseridos/atualizados no banco de dados com sucesso!")

    except Exception as e:
        print(f"Erro ao inserir/atualizar dados no banco de dados: {e}")

if __name__ == "__main__":
    df = fetch_data_from_sheets(sheet_url, sheet_name)

    if not df.empty:
        load_data_into_db(df)
    else:
        print("Nenhum dado encontrado na planilha.")
