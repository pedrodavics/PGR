import paramiko
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from flask import Flask, jsonify
import os
import json
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("USER_OS")
passw = os.getenv("PASS_OS")

app = Flask(__name__)

# Caminho do arquivo JSON contendo informações do cliente
client_info_file = "client_info.json"

# Caminho do arquivo de saída
output_file = "result_os.txt"
commands_file = "src/scripts/executable/commands.sh"

def load_client_info():
    """Carrega as informações do cliente a partir do arquivo JSON."""
    try:
        with open(client_info_file, "r") as file:
            client_info = json.load(file)
            ip = client_info.get("ip")
            port = client_info.get("portassh")
            username = user
            password = passw

            if not ip or not port or not username or not password:
                raise ValueError("Informações de conexão incompletas no arquivo JSON.")

            return ip, int(port), username, password
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo {client_info_file} não encontrado.")
    except json.JSONDecodeError:
        raise ValueError(f"Erro ao decodificar o arquivo {client_info_file}.")
    except Exception as e:
        raise Exception(f"Erro ao carregar informações do cliente: {e}")

def read_commands_from_file(filename):
    """Lê os comandos de um arquivo."""
    try:
        with open(filename, "r") as file:
            commands = [line.strip() for line in file.readlines() if line.strip() and not line.startswith("#")]
        return commands
    except Exception as e:
        print(f"Erro ao ler o arquivo de comandos: {e}")
        return []

commands = read_commands_from_file(commands_file)

def run_remote_command(ssh_client, command):
    """Executa um comando remoto via SSH."""
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    return output if output else error

def process_command(ssh_client, command):
    """Processa um comando remoto e retorna o resultado."""
    command = command.strip()
    if command and not command.startswith("#"):
        print(f"Executando comando: {command}")
        result = run_remote_command(ssh_client, command)
        return f"{result}\n\n"
    return ""

def generate_file():
    """Conecta ao servidor SSH e executa os comandos."""
    try:
        ip, port, username, password = load_client_info()
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ip, port=port, username=username, password=password)
        print(f"Conectado com sucesso a {ip}:{port}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            with open(output_file, "w") as output:
                futures = [executor.submit(process_command, ssh_client, command) for command in commands]

                for future in futures:
                    output.write(future.result())

        print(f"Resultados salvos em {output_file}")
        return True
    except paramiko.AuthenticationException:
        print("Erro de autenticação. Verifique o usuário e a senha.")
        return False
    except Exception as e:
        print(f"Erro ao conectar ou executar comandos: {e}")
        return False
    finally:
        if 'ssh_client' in locals() and ssh_client:
            ssh_client.close()
            print("Conexão SSH encerrada.")

output_directory = "./output"

@app.route('/executar_comandos', methods=["GET"])
def executar_comandos():
    """Rota para executar os comandos remotos."""
    if generate_file():
        txt_results_directory = os.path.join(output_directory, "reports")
        os.makedirs(txt_results_directory, exist_ok=True)
    
        target_path = os.path.join(txt_results_directory, output_file)
        shutil.move(output_file, target_path)

        return jsonify({
            "mensagem": "Arquivo gerado com sucesso.",
            "caminho_arquivo": target_path
        }), 200
    
    return jsonify({"erro": "Falha ao gerar o arquivo."}), 500

if __name__ == '__main__':
    app.run(debug=True)
