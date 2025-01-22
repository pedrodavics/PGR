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
    user_data = {
        "user": username,
        "ip": get_ip_address(),
        "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "selected_client": client_name
    }

    try:
        if os.path.exists('user_data.json'):
            with open('user_data.json', 'r') as json_file:
                existing_data = json.load(json_file)
        else:
            existing_data = []

        existing_data.append(user_data)

        with open('user_data.json', 'w') as json_file:
            json.dump(existing_data, json_file, indent=4)
        print("Dados do usuário salvos com sucesso!")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao salvar os dados do usuário: {e}")


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

# Filter and update the client listbox
def update_listbox(filtered_clients):
    listbox.delete(0, tk.END)
    for client in filtered_clients:
        listbox.insert(tk.END, client[1])

# Filter clients based on the search query
def filter_clients(event):
    query = search_var.get().lower()
    filtered_clients = [client for client in clients if query in client[1].lower()]
    update_listbox(filtered_clients)

# Autocomplete function to complete the query on 'Tab'
def autocomplete(event):
    query = search_var.get().lower()
    matching_clients = [client[1] for client in clients if query in client[1].lower()]
    if matching_clients:
        search_var.set(matching_clients[0])

def on_hover(event, listbox):
    index = listbox.nearest(event.y)
    listbox.itemconfig(index, {'bg': 'black', 'fg': 'white'})

def on_leave(event, listbox):
    index = listbox.nearest(event.y)
    listbox.itemconfig(index, {'bg': 'white', 'fg': 'black'})

def login():
    username = username_var.get()
    password = password_var.get()
    
    if username == master and password == key:
        login_frame.pack_forget()
        run_main_app(username)  
    else:
        messagebox.showerror("Erro", "Usuário ou senha incorretos!")

def run_main_app(username):
    global clients, listbox, search_var

    root = tk.Tk()
    root.title("Clientes")
    root.geometry("600x500")
    root.config(bg="#f0f0f0")

    search_var = tk.StringVar()

    search_label = tk.Label(root, text="Pesquisar Cliente:", font=("Arial", 14), bg="#f0f0f0")
    search_label.pack(pady=10)

    search_bar = tk.Entry(root, textvariable=search_var, font=("Arial", 12), width=40)
    search_bar.pack(pady=5)
    search_bar.bind("<KeyRelease>", filter_clients)
    search_bar.bind("<Tab>", autocomplete)  # Bind 'Tab' key to autocomplete function

    clients = fetch_clients()

    listbox_frame = tk.Frame(root, bg="#f0f0f0")
    listbox_frame.pack(pady=20)

    listbox = tk.Listbox(listbox_frame, height=10, width=50, font=("Arial", 12), bd=0, selectmode=tk.SINGLE)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH)

    scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)

    for client in clients:
        listbox.insert(tk.END, client[1])

    listbox.bind("<Motion>", lambda event: on_hover(event, listbox))
    listbox.bind("<Leave>", lambda event: on_leave(event, listbox))

    def on_select(event):
        selected_index = listbox.curselection()
        if selected_index:
            client_name = listbox.get(selected_index)
            client_id = next((client[0] for client in clients if client[1] == client_name), None)
            if client_id:
                generate_report(client_id, username)

    listbox.bind("<<ListboxSelect>>", on_select)

    root.mainloop()

root = tk.Tk()
root.title("Login")
root.geometry("400x250")
root.config(bg="#f0f0f0")

login_frame = tk.Frame(root, bg="#f0f0f0")
login_frame.pack(pady=50)

username_var = tk.StringVar()
password_var = tk.StringVar()

username_label = tk.Label(login_frame, text="Usuário:", font=("Arial", 12), bg="#f0f0f0")
username_label.grid(row=0, column=0, padx=10, pady=10)

username_entry = tk.Entry(login_frame, textvariable=username_var, font=("Arial", 12))
username_entry.grid(row=0, column=1, padx=10, pady=10)

password_label = tk.Label(login_frame, text="Senha:", font=("Arial", 12), bg="#f0f0f0")
password_label.grid(row=1, column=0, padx=10, pady=10)

password_entry = tk.Entry(login_frame, textvariable=password_var, font=("Arial", 12), show="*")
password_entry.grid(row=1, column=1, padx=10, pady=10)

def toggle_password():
    if password_entry.cget('show') == "*":
        password_entry.config(show="")
        toggle_password_button.config(text="Ocultar")
    else:
        password_entry.config(show="*")
        toggle_password_button.config(text="Mostrar")

toggle_password_button = tk.Button(login_frame, text="Mostrar", font=("Arial", 12), command=toggle_password, relief=tk.FLAT, bg="#f0f0f0")
toggle_password_button.grid(row=1, column=2, padx=10, pady=10)

login_button = tk.Button(login_frame, text="Entrar", font=("Arial", 12), command=login)
login_button.grid(row=2, column=0, columnspan=2, pady=20)

root.mainloop()
