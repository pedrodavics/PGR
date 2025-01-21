import tkinter as tk
import os
from tkinter import messagebox
import psycopg2
import json
import subprocess
from dotenv import load_dotenv
import shutil

load_dotenv()
host = os.getenv("HOST_DB")
port = os.getenv("PORT_DB")
dbname = os.getenv("NAME_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")

# Função para conectar ao banco de dados
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

# Função para buscar os clientes no banco de dados
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

# Função para buscar os dados de um cliente
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

# Função para salvar as informações do cliente
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

# Função para limpar arquivos temporários
def clean():
    try:
        # Apagando arquivos e pastas temporárias
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

        # Apagando os logs
        if os.path.exists("logs/zabbix.log"):
            os.remove("logs/zabbix.log")
            print("Arquivo 'zabbix.log' apagado com sucesso!")

        if os.path.exists("logs/pdf.log"):
            os.remove("logs/pdf.log")
            print("Arquivo 'pdf.log' apagado com sucesso!")

    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao limpar arquivos temporários: {e}")

# Função para executar os scripts
def execute_scripts():
    try:
        subprocess.run(["python", "src/apps/app_graphics.py"], check=True)
        subprocess.run(["python", "src/apps/app_jdbc.py"], check=True)
        subprocess.run(["python", "src/apps/app_os.py"], check=True)
        subprocess.run(["python", "src/generator/pdf.py"], check=True)
        messagebox.showinfo("Sucesso", "Scripts executados com sucesso!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro", f"Erro ao executar os scripts: {e}")

# Função para gerar o relatório
def generate_report(client_id):
    client_data = fetch_client_data(client_id)
    if client_data:
        save_client_info(client_data)
        execute_scripts()
        clean()
        messagebox.showinfo("Sucesso", "Relatório gerado com sucesso!")
    else:
        messagebox.showerror("Erro", "Cliente não encontrado.")

# Função principal para a interface gráfica
def main():
    root = tk.Tk()
    root.title("Clientes")
    root.geometry("500x400")

    clients = fetch_clients()
    listbox = tk.Listbox(root, height=10, width=50)
    for client in clients:
        listbox.insert(tk.END, client[1])  
    listbox.pack()

    def on_select(event):
        selected_index = listbox.curselection()
        if selected_index:
            client_name = listbox.get(selected_index)
            client_id = next((client[0] for client in clients if client[1] == client_name), None)
            if client_id:
                generate_report(client_id)

    listbox.bind("<<ListboxSelect>>", on_select)
    tk.Button(root, text="Gerar Relatório", command=lambda: on_select(None)).pack()

    root.mainloop()

if __name__ == "__main__":
    main()
