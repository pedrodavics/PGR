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
import threading

load_dotenv()

host = os.getenv("HOST_DB")
port = os.getenv("PORT_DB")
dbname = os.getenv("NAME_DB")
user = os.getenv("USER_DB")
password = os.getenv("PASS_DB")

def center_window(win, width, height):
    win.update_idletasks()
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    win.geometry(f"{width}x{height}+{x}+{y}")

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
    user_ip = socket.gethostbyname(socket.gethostname())
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

def save_client_info(client_data):
    # A coluna "nome" será utilizada para formar o nome do PDF.
    # Conforme solicitado, "userssh" é a coluna 9 (índice 8) e "senhassh" é a coluna 10 (índice 9)
    client_info = {
        "idcliente": client_data[0],
        "nome": client_data[1],
        "ip": client_data[2],
        "portassh": client_data[3],
        "tpbanco": client_data[4],
        "nomebanco": client_data[5],
        "portabanco": client_data[6],
        "idhostzbx": client_data[7],
        "userssh": client_data[8],
        "senhassh": client_data[9]
    }
    with open('client_info.json', 'w') as json_file:
        json.dump(client_info, json_file)

def get_month_in_portuguese(dt):
    """Retorna o nome do mês em português (minúsculo) para o datetime informado."""
    months = {
        1: 'janeiro',
        2: 'fevereiro',
        3: 'março',
        4: 'abril',
        5: 'maio',
        6: 'junho',
        7: 'julho',
        8: 'agosto',
        9: 'setembro',
        10: 'outubro',
        11: 'novembro',
        12: 'dezembro'
    }
    return months[dt.month]

def clean():
    try:
        # Captura o valor da coluna "nome" antes de remover o arquivo de configurações
        nome_cliente = None
        if os.path.exists('client_info.json'):
            with open('client_info.json', 'r') as f:
                client_info = json.load(f)
                nome_cliente = client_info.get("nome")
            os.remove('client_info.json')
            print("Arquivo client_info.json apagado com sucesso!")
        else:
            print("Arquivo client_info.json não encontrado para remoção.")
        
        if os.path.exists("output/images"):
            shutil.rmtree("output/images")
            print("Pasta 'images' apagada com sucesso!")
        
        # Renomeia o PDF gerado.
        # O script mergepdf.py originalmente gera o arquivo em "output/relatorio.pdf"
        if os.path.exists("output/relatorio.pdf"):
            mes_atual = get_month_in_portuguese(datetime.now())
            # Se nome_cliente não foi encontrado, usa "Cliente" como padrão
            nome_cliente = nome_cliente if nome_cliente else "Cliente"
            novo_nome_pdf = f"output/Relatório situacional {nome_cliente} de {mes_atual}.pdf"
            shutil.move("output/relatorio.pdf", novo_nome_pdf)
            print(f"Relatório movido para a pasta 'output' com o nome '{novo_nome_pdf}' com sucesso!")
        
        if os.path.exists("output/reports"):
            shutil.rmtree("output/reports")
            print("Pasta 'reports' apagada com sucesso!")
        
        # Exclusão das pastas adicionais
        if os.path.exists("output/pdf temp"):
            shutil.rmtree("output/pdf temp")
            print("Pasta 'pdf temp' apagada com sucesso!")
        
        if os.path.exists("output/graphics"):
            shutil.rmtree("output/graphics")
            print("Pasta 'graphics' apagada com sucesso!")
        
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
    #    subprocess.run(["python", "src/apps/app_graphics.py"], check=True)
        subprocess.run(["python", "src/apps/formatter.py"], check=True)
        subprocess.run(["python", "src/apps/mergepdf.py"], check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Erro ao executar os scripts: {e}")

def generate_report_worker(client_id, username):
    client_data = fetch_client_data(client_id)
    if client_data:
        save_client_info(client_data)
        save_user_data(username, client_data[1])
        try:
            execute_scripts()
            clean()
            return True, "Relatório gerado com sucesso!"
        except Exception as e:
            return False, str(e)
    else:
        return False, "Cliente não encontrado."

def finish_report_generation(progress_win, client_root, success, msg):
    progress_win.destroy()
    if success:
        messagebox.showinfo("Sucesso", msg)
    else:
        messagebox.showerror("Erro", msg)

def thread_generate_report(client_id, username, progress_win, client_root):
    success, msg = generate_report_worker(client_id, username)
    client_root.after(0, lambda: finish_report_generation(progress_win, client_root, success, msg))

def show_client_selection(root):
    root.destroy()
    client_root = tk.Tk()
    client_root.title("Gerador de Relatórios")
    center_window(client_root, 400, 300)

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
            # Cria a janela de progresso
            progress_win = tk.Toplevel(client_root)
            progress_win.title("Aguarde...")
            center_window(progress_win, 300, 100)
            tk.Label(progress_win, text="Gerando relatório...").pack(pady=10, padx=10)
            progress_bar = ttk.Progressbar(progress_win, mode='indeterminate', length=250)
            progress_bar.pack(pady=10, padx=10)
            progress_bar.start()
            # Executa a geração do relatório em uma thread separada
            threading.Thread(
                target=thread_generate_report,
                args=(selected_client[0], username, progress_win, client_root),
                daemon=True
            ).start()
        else:
            messagebox.showerror("Erro", "Cliente selecionado não encontrado.")

    tk.Button(client_root, text="Gerar Relatório", command=on_generate).pack(pady=20)
    client_root.mainloop()

def main():
    # Abre diretamente a janela de seleção de cliente sem autenticação
    root = tk.Tk()
    root.withdraw()  # Oculta a janela principal
    show_client_selection(root)

if __name__ == "__main__":
    main()
