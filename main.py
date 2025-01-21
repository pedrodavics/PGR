import tkinter as tk
import os
from tkinter import messagebox
import psycopg2
import json
from dotenv import load_dotenv

load_dotenv()

# Carregar variáveis de ambiente
host = os.getenv("HOST_DB")
port = os.getenv("PORT_DB")
dbname = os.getenv("NAME_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")

# Função para buscar todos os clientes do banco de dados
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

# Função para gerar relatório com as informações do cliente
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
            messagebox.showinfo("Sucesso", "Relatório gerado com sucesso!")
        else:
            messagebox.showerror("Erro", "Cliente não encontrado.")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

# Função principal para criar a interface gráfica
def main():
    # Criando a janela principal
    root = tk.Tk()
    root.title("Clientes")
    root.geometry("500x400")

    # Criando um Listbox para mostrar os clientes
    clients = fetch_clients()
    listbox = tk.Listbox(root, height=10, width=50)
    for client in clients:
        listbox.insert(tk.END, client[1])  # Exibindo o nome dos clientes
    listbox.pack()

    # Função para lidar com a seleção de um cliente
    def on_select(event):
        selected_index = listbox.curselection()
        if selected_index:
            client_name = listbox.get(selected_index)
            cursor = fetch_clients()
            # Encontrar o idcliente correspondente
            client_id = next((client[0] for client in cursor if client[1] == client_name), None)
            if client_id:
                generate_report(client_id)

    # Bind da seleção
    listbox.bind("<<ListboxSelect>>", on_select)

    # Botão para gerar o relatório
    tk.Button(root, text="Gerar Relatório", command=lambda: on_select(None)).pack()

    root.mainloop()

if __name__ == "__main__":
    main()
