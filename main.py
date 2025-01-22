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

# Função para atualizar a listbox com clientes filtrados
def update_listbox(filtered_clients):
    listbox.delete(0, tk.END)
    for client in filtered_clients:
        listbox.insert(tk.END, client[1])

# Função para pesquisar clientes conforme a digitação
def filter_clients(event):
    query = search_var.get().lower()
    filtered_clients = [client for client in clients if query in client[1].lower()]
    update_listbox(filtered_clients)

# Função para alterar o fundo ao passar o mouse sobre um item da listbox
def on_hover(event, listbox):
    index = listbox.nearest(event.y)
    listbox.itemconfig(index, {'bg': 'black', 'fg': 'white'})

# Função para reverter a cor ao sair do item da listbox
def on_leave(event, listbox):
    index = listbox.nearest(event.y)
    listbox.itemconfig(index, {'bg': 'white', 'fg': 'black'})

# Função principal para a interface gráfica
def main():
    global clients, listbox, search_var

    root = tk.Tk()
    root.title("Clientes")
    root.geometry("600x500")
    root.config(bg="#f0f0f0")

    # Variável para busca
    search_var = tk.StringVar()

    # Criando a barra de pesquisa
    search_label = tk.Label(root, text="Pesquisar Cliente:", font=("Arial", 14), bg="#f0f0f0")
    search_label.pack(pady=10)

    search_bar = tk.Entry(root, textvariable=search_var, font=("Arial", 12), width=40)
    search_bar.pack(pady=5)
    search_bar.bind("<KeyRelease>", filter_clients)

    # Buscando os clientes
    clients = fetch_clients()

    # Criando a listbox
    listbox_frame = tk.Frame(root, bg="#f0f0f0")
    listbox_frame.pack(pady=20)

    listbox = tk.Listbox(listbox_frame, height=10, width=50, font=("Arial", 12), bd=0, selectmode=tk.SINGLE)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH)

    scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)

    # Adicionando os clientes à listbox
    for client in clients:
        listbox.insert(tk.END, client[1])

    # Configurando os eventos de hover
    listbox.bind("<Motion>", lambda event: on_hover(event, listbox))
    listbox.bind("<Leave>", lambda event: on_leave(event, listbox))

    # Evento de seleção na listbox
    def on_select(event):
        selected_index = listbox.curselection()
        if selected_index:
            client_name = listbox.get(selected_index)
            client_id = next((client[0] for client in clients if client[1] == client_name), None)
            if client_id:
                generate_report(client_id)

    listbox.bind("<<ListboxSelect>>", on_select)

    root.mainloop()

if __name__ == "__main__":
    main()
