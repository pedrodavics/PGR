from tkinterweb import HtmlFrame
import tkinter as tk
import os
import psycopg2
import psycopg2.extras
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

client_table = os.getenv("CLIENT_TABLE")
serv_table = os.getenv("SERV_TABLE")  # Variável para a tabela de informações do servidor

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
            cursor.execute(f"SELECT idcliente, nome FROM {client_table};")
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
            # Utiliza RealDictCursor para retornar um dicionário com os nomes das colunas
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(f"SELECT * FROM {client_table} WHERE idcliente = %s;", (client_id,))
            return cursor.fetchone()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao buscar dados do cliente: {e}")
            return None
        finally:
            cursor.close()
            connection.close()
    return None

def fetch_serv_info(client_name):
    connection = connect_db()
    if connection:
        try:
            # Usa RealDictCursor para retornar um dicionário e filtra pela coluna "nome"
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(f"SELECT * FROM {serv_table} WHERE nome = %s;", (client_name,))
            return cursor.fetchone()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao buscar dados do servidor: {e}")
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
    # Salva as informações do cliente diretamente no JSON,
    # usando os nomes das colunas retornadas pela consulta.
    with open('client_info copy.json', 'w') as json_file:
        json.dump(client_data, json_file)

def save_serv_info(serv_data):
    if serv_data:
        with open('serv_info.json', 'w') as json_file:
            json.dump(serv_data, json_file)

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
        if os.path.exists('client_info copy.json'):
            with open('client_info copy.json', 'r') as f:
                client_info = json.load(f)
                nome_cliente = client_info.get("nome")
            os.remove('client_info copy.json')
            print("Arquivo 'client_info copy.json' apagado com sucesso!")
        else:
            print("Arquivo 'client_info copy.json' não encontrado para remoção.")
        
        # Remove o arquivo serv_info.json (com caminho completo se necessário)
        serv_info_path = "/home/tauge/Documents/tauge/PGR/serv_info.json"
        if os.path.exists(serv_info_path):
            os.remove(serv_info_path)
            print(f"Arquivo '{serv_info_path}' apagado com sucesso!")
        else:
            print(f"Arquivo '{serv_info_path}' não encontrado para remoção.")
        
        # Remove o arquivo idcliente_consulta.txt (com caminho completo se necessário)
        idcliente_path = "/home/tauge/Documents/tauge/PGR/output/idcliente_consulta.txt"
        if os.path.exists(idcliente_path):
            os.remove(idcliente_path)
            print(f"Arquivo '{idcliente_path}' apagado com sucesso!")
        else:
            print(f"Arquivo '{idcliente_path}' não encontrado para remoção.")
        
        if os.path.exists("output/images"):
            shutil.rmtree("output/images")
            print("Pasta 'images' apagada com sucesso!")
        
        # Renomeia o PDF gerado usando o nome do cliente selecionado na interface
        if os.path.exists("output/relatorio.pdf"):
            mes_atual = get_month_in_portuguese(datetime.now())
            nome_cliente = nome_cliente if nome_cliente else "Cliente"
            novo_nome_pdf = f"output/Relatório situacional {nome_cliente} de {mes_atual}.pdf"
            shutil.move("output/relatorio.pdf", novo_nome_pdf)
            print(f"Relatório movido para a pasta 'output' com o nome '{novo_nome_pdf}' com sucesso!")
        
        if os.path.exists("output/reports"):
            shutil.rmtree("output/reports")
            print("Pasta 'reports' apagada com sucesso!")
        
        # Limpeza dos arquivos e pastas temporários solicitados
        if os.path.exists("output/pdf temp"):
            shutil.rmtree("output/pdf temp")
            print("Pasta 'output/pdf temp' apagada com sucesso!")
        
        if os.path.exists("output/pdf temp/pgr_final.pdf"):
            os.remove("output/pdf temp/pgr_final.pdf")
            print("Arquivo 'output/pdf temp/pgr_final.pdf' apagado com sucesso!")
        
        if os.path.exists("output/backups_consulta.txt"):
            os.remove("output/backups_consulta.txt")
            print("Arquivo 'output/backups_consulta.txt' apagado com sucesso!")
        
        if os.path.exists("output/biggest_tables_consulta.txt"):
            os.remove("output/biggest_tables_consulta.txt")
            print("Arquivo 'output/biggest_tables_consulta.txt' apagado com sucesso!")
        
        if os.path.exists("output/db_type_consulta.txt"):
            os.remove("output/db_type_consulta.txt")
            print("Arquivo 'output/db_type_consulta.txt' apagado com sucesso!")
        
        if os.path.exists("output/info_db_consulta.txt"):
            os.remove("output/info_db_consulta.txt")
            print("Arquivo 'output/info_db_consulta.txt' apagado com sucesso!")
        
        if os.path.exists("output/Info_serv_prod.txt"):
            os.remove("output/Info_serv_prod.txt")
            print("Arquivo 'output/Info_serv_prod.txt' apagado com sucesso!")
        
        if os.path.exists("output/monitoring_type_consulta.txt"):
            os.remove("output/monitoring_type_consulta.txt")
            print("Arquivo 'output/monitoring_type_consulta.txt' apagado com sucesso!")
        
        if os.path.exists("output/nome_consulta.txt"):
            os.remove("output/nome_consulta.txt")
            print("Arquivo 'output/nome_consulta.txt' apagado com sucesso!")
        
        if os.path.exists("output/serv_prod_info_consulta.txt"):
            os.remove("output/serv_prod_info_consulta.txt")
            print("Arquivo 'output/serv_prod_info_consulta.txt' apagado com sucesso!")
        
        if os.path.exists("output/size_db_consulta.txt"):
            os.remove("output/size_db_consulta.txt")
            print("Arquivo 'output/size_db_consulta.txt' apagado com sucesso!")
        
        if os.path.exists("output/top_queries_consulta.txt"):
            os.remove("output/top_queries_consulta.txt")
            print("Arquivo 'output/top_queries_consulta.txt' apagado com sucesso!")
    
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao limpar arquivos temporários: {e}")

def execute_scripts():
    try:
        # Executa os scripts na sequência solicitada
        subprocess.run(["python", "src/apps/ultima_consulta.py"], check=True)
        subprocess.run(["python", "src/apps/formatter_sqlserver.py"], check=True)
        subprocess.run(["python", "src/apps/mergepdf.py"], check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Erro ao executar os scripts: {e}")

def generate_report_worker(client_id, username):
    client_data = fetch_client_data(client_id)
    if client_data:
        save_client_info(client_data)
        save_user_data(username, client_data.get("nome"))
        
        # Busca e salva as informações do servidor utilizando o nome do cliente
        serv_data = fetch_serv_info(client_data.get("nome"))
        save_serv_info(serv_data)
        
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
