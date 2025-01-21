import tkinter as tk
import os
from tkinter import messagebox
import psycopg2
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()
host = os.getenv("HOST_DB")
port = os.getenv("PORT_DB")
dbname = os.getenv("NAME_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")

def fetch_clients():
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        cursor = connection.cursor()
        cursor.execute("SELECT idcliente, nome FROM tb_cliente;")
        clients = cursor.fetchall()
        return clients
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao buscar dados: {e}")
        return []
    finally:
        if connection:
            cursor.close()
            connection.close()

def generate_report(client_id):
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM tb_cliente WHERE idcliente = %s;", (client_id,))
        client_data = cursor.fetchone()
        
        if client_data:
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

            # Executando os scripts
            execute_scripts()

            # Verificando se o arquivo relatorio.pdf foi criado
            if os.path.exists("output/reports/pdf/relatorio.pdf"):
                messagebox.showinfo("Sucesso", "Relatório gerado com sucesso!")
            else:
                messagebox.showerror("Erro", "Falha ao gerar o relatório PDF.")

        else:
            messagebox.showerror("Erro", "Cliente não encontrado.")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

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
            cursor = fetch_clients()
            client_id = next((client[0] for client in cursor if client[1] == client_name), None)
            if client_id:
                generate_report(client_id)

    listbox.bind("<<ListboxSelect>>", on_select)

    tk.Button(root, text="Gerar Relatório", command=lambda: on_select(None)).pack()

    root.mainloop()

if __name__ == "__main__":
    main()
