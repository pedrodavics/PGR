from tkinterweb import HtmlFrame
import tkinter as tk
import os
import psycopg2
import json
import subprocess
from dotenv import load_dotenv
import shutil
from tkinter import messagebox
from tkinter import ttk
import socket
from datetime import datetime

load_dotenv()

host = os.getenv("HOST_DB")
port = os.getenv("PORT_DB")
dbname = os.getenv("NAME_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")

master = os.getenv("USER_MAIN")
key = os.getenv("PASS_MAIN")

def connect_db():
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        return connection
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao conectar ao banco de dados: {e}")
        return None
    
def fetch_clients():
    connection = connect_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT idcliente, nome FROM tb_cliente;")
            return cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao buscar dados: {e}")
            return []
        finally:
            cursor.close()
            connection.close()
    return []

def fetch_client_data(client_id):
    connection = connect_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM tb_cliente WHERE idcliente = %s;", (client_id,))
            return cursor.fetchone()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao buscar dados do cliente: {e}")
            return None
        finally:
            cursor.close()
            connection.close()
    return None

def save_user_data(username, client_name):
    user_ip = get_ip_address()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    connection = connect_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO tb_autentificacao (username, ipmaquina, horario, cliente)
                VALUES (%s, %s, %s, %s);
            """, (username, user_ip, timestamp, client_name))
            connection.commit()
            print("Dados do usuário salvos no banco de dados com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar os dados do usuário no banco: {e}")
        finally:
            cursor.close()
            connection.close()

def get_ip_address():
    return socket.gethostbyname(socket.gethostname())

def save_client_info(client_data):
    client_info = {
        "idcliente": client_data[0],
        "nome": client_data[1],
        "ip": client_data[2],
        "portassh": client_data[3],
        "tpbanco": client_data[4],
        "nomebanco": client_data[5],
        "portabanco": client_data[6],
        "idhostzbx": client_data[7]
    }
    with open('client_info.json', 'w') as json_file:
        json.dump(client_info, json_file)

def clean():
    try:
        os.remove('client_info.json')
        print("Arquivo client_info.json apagado com sucesso!")
        
        if os.path.exists("output/images"):
            shutil.rmtree("output/images")
            print("Pasta 'images' apagada com sucesso!")

        if os.path.exists("output/reports/pdf/relatorio.pdf"):
            shutil.move("output/reports/pdf/relatorio.pdf", "output/relatorio.pdf")
            print("Relatório movido para a pasta 'output' com sucesso!")
        else:
            messagebox.showerror("Erro", "Falha ao encontrar o relatório para mover.")

        if os.path.exists("output/reports"):
            shutil.rmtree("output/reports")
            print("Pasta 'reports' apagada com sucesso!")

        if os.path.exists("logs/zabbix.log"):
            os.remove("logs/zabbix.log")
            print("Arquivo 'zabbix.log' apagado com sucesso!")

        if os.path.exists("logs/pdf.log"):
            os.remove("logs/pdf.log")
            print("Arquivo 'pdf.log' apagado com sucesso!")

    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao limpar arquivos temporários: {e}")

def execute_scripts():
    try:
        subprocess.run(["python", "src/apps/app_graphics.py"], check=True)
        subprocess.run(["python", "src/apps/app_jdbc.py"], check=True)
        subprocess.run(["python", "src/apps/app_os.py"], check=True)
        subprocess.run(["python", "src/generator/pdf.py"], check=True)
        messagebox.showinfo("Sucesso", "Scripts executados com sucesso!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Erro ao executar os scripts: {e}")

def generate_report(client_id, username):
    client_data = fetch_client_data(client_id)
    if client_data:
        save_client_info(client_data)
        save_user_data(username, client_data[1]) 
        execute_scripts()
        clean()
        messagebox.showinfo("Sucesso", "Relatório gerado com sucesso!")
    else:
        messagebox.showerror("Erro", "Cliente não encontrado.")

def authenticate_user(username, password):
    if username == master and password == key:
        return True
    else:
        return False
    
def show_client_selection(root):
    root.destroy()
    client_root = tk.Tk()
    client_root.title("Gerador de Relatórios")

    tk.Label(client_root, text="Selecione um cliente:").pack(pady=10)
    clients = fetch_clients()
    client_names = [client[1] for client in clients]
    client_var = tk.StringVar()
    client_dropdown = ttk.Combobox(client_root, textvariable=client_var, values=client_names, state="readonly")
    client_dropdown.pack(pady=5)

    tk.Label(client_root, text="Seu nome de usuário:").pack(pady=10)
    username_entry = tk.Entry(client_root)
    username_entry.pack(pady=5)

    def on_generate():
        selected_client_name = client_var.get()
        username = username_entry.get()
        if not selected_client_name or not username:
            messagebox.showerror("Erro", "Por favor, preencha todos os campos.")
            return
        selected_client = next((client for client in clients if client[1] == selected_client_name), None)
        if selected_client:
            generate_report(selected_client[0], username)
        else:
            messagebox.showerror("Erro", "Cliente selecionado não encontrado.")

    tk.Button(client_root, text="Gerar Relatório", command=on_generate).pack(pady=20)
    client_root.mainloop()

def main():
    auth_root = tk.Tk()
    auth_root.title("Autenticação")

    tk.Label(auth_root, text="Usuário:").pack(pady=10)
    username_entry = tk.Entry(auth_root)
    username_entry.pack(pady=5)

    tk.Label(auth_root, text="Senha:").pack(pady=10)
    password_entry = tk.Entry(auth_root, show="*")
    password_entry.pack(pady=5)

    def on_authenticate():
        username = username_entry.get()
        password = password_entry.get()
        if authenticate_user(username, password):
            show_client_selection(auth_root)
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")

    tk.Button(auth_root, text="Entrar", command=on_authenticate).pack(pady=20)
    auth_root.mainloop()

if __name__ == "__main__":
    main()
