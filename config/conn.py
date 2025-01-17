import os
import pandas as pd
import psycopg2
from tkinter import Tk, Label, Button, StringVar, OptionMenu, messagebox
from dotenv import load_dotenv, set_key

# Carregar variáveis do .env
load_dotenv()

host = os.getenv("HOST_DB")
port = os.getenv("PORT_DB")
dbname = os.getenv("NAME_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")

def fetch_client_names():
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        cursor = connection.cursor()
        cursor.execute("SELECT nome FROM tb_cliente;")
        client_names = [row[0] for row in cursor.fetchall()]
        connection.close()
        return client_names
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao conectar ao banco de dados: {e}")
        return []

def fetch_client_details(selected_client):
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        cursor = connection.cursor()
        query = "SELECT ip, portassh, idhostzbx FROM tb_cliente WHERE nome = %s;"
        cursor.execute(query, (selected_client,))
        details = cursor.fetchone()
        connection.close()
        return details if details else None
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao buscar detalhes do cliente: {e}")
        return None

def update_env_file(ip, port, id_zabbix):
    """Atualiza as variáveis no arquivo .env"""
    set_key(".env", "HOST_OS", ip)
    set_key(".env", "PORT_OS", str(port))  
    set_key(".env", "ID_ZABBIX", str(id_zabbix))  
    load_dotenv()

def on_select_client(*args):
    selected_client = selected_client_var.get()
    if selected_client:
        details = fetch_client_details(selected_client)
        if details:
            ip, port, id_zabbix = details
            update_env_file(ip, port, id_zabbix)

            details_text = f"IP: {ip}\nPorta: {port}\nID Zabbix: {id_zabbix}"
            messagebox.showinfo("Detalhes do Cliente", details_text)
        else:
            messagebox.showwarning("Aviso", f"Cliente '{selected_client}' não encontrado.")

root = Tk()
root.title("Clientes do Banco de Dados")

selected_client_var = StringVar(root)
selected_client_var.set("Selecione um cliente")

client_names = fetch_client_names()

if client_names:
    Label(root, text="Clientes disponíveis:").pack(pady=10)
    client_menu = OptionMenu(root, selected_client_var, *client_names)
    client_menu.pack(pady=10)

    Button(root, text="Exibir Detalhes e Atualizar .env", command=on_select_client).pack(pady=20)
else:
    Label(root, text="Nenhum cliente disponível no banco de dados.").pack(pady=20)

root.mainloop()
