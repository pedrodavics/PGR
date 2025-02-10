import paramiko
import shutil
from datetime import datetime
from flask import Flask, jsonify
import os
import json
from dotenv import load_dotenv

print("Carregando variáveis de ambiente...")
load_dotenv()

app = Flask(__name__)

print("Lendo informações do cliente a partir do JSON...")
with open("../PGR/client_info.json", "r") as json_file:
    client_info = json.load(json_file)

ip = client_info.get("ip")
port = client_info.get("portassh")

username = os.getenv("USER_OS")
password = os.getenv("PASS_OS")

print(f"Configurações de conexão carregadas: IP={ip}, Port={port}, User={username}")

output_file = "result_os.txt"
commands_file = "src/scripts/executable/commands.sh"

def read_commands_from_file(filename):
    print(f"Lendo comandos do arquivo: {filename}")
    try:
        with open(filename, "r") as file:
            commands = [line.strip() for line in file.readlines() if line.strip() and not line.startswith("#")]
        print(f"Comandos carregados: {commands}")
        return commands
    except Exception as e:
        print(f"Erro ao ler o arquivo de comandos: {e}")
        return []

commands = read_commands_from_file(commands_file)

def run_remote_command(ssh_client, command):
    print(f"Executando comando remotamente: {command}")
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    if output:
        print(f"Saída do comando: {output}")
    if error:
        print(f"Erro do comando: {error}")
    return output if output else error

def process_command(ssh_client, command):
    print(f"Processando comando: {command}")
    command = command.strip()
    if command and not command.startswith("#"):
        result = run_remote_command(ssh_client, command)
        print(f"Resultado do comando processado: {result}")
        return f"{result}\n\n"  
    return ""

def generate_file():
    print("Iniciando a geração do arquivo...")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  #

    try:
        print(f"Conectando ao servidor SSH {ip}:{port} com o usuário {username}...")
        ssh_client.connect(hostname=ip, port=port, username=username, password=password)
        print("Conexão SSH bem-sucedida.")

        print("Executando comandos sequencialmente...")
        with open(output_file, "w") as output:
            for command in commands:
                result = process_command(ssh_client, command)
                output.write(result)

        print(f"Resultados salvos no arquivo: {output_file}")
        return True
    except paramiko.AuthenticationException:
        print("Erro de autenticação. Verifique o usuário e a senha.")
        return False
    except Exception as e:
        print(f"Erro ao conectar ou executar comandos: {e}")
        return False
    finally:
        print("Encerrando a conexão SSH...")
        ssh_client.close()
        print("Conexão SSH encerrada.")


output_directory = "./output"

@app.route('/executar_comandos', methods=["GET"])
def executar_comandos():
    print("Recebida solicitação para executar comandos.")
    if generate_file():
        print("Arquivo gerado com sucesso. Preparando para mover para o diretório de saída...")
        txt_results_directory = os.path.join(output_directory, "reports")
        os.makedirs(txt_results_directory, exist_ok=True)
    
        target_path = os.path.join(txt_results_directory, output_file)
        shutil.move(output_file, target_path)
        print(f"Arquivo movido para: {target_path}")

        return jsonify({
            "mensagem": "Arquivo gerado com sucesso.",
            "caminho_arquivo": target_path
        }), 200
    
    print("Falha ao gerar o arquivo.")
    return jsonify({"erro": "Falha ao gerar o arquivo."}), 500

if __name__ == '__main__':
        print("Executando comandos automaticamente...")
        if generate_file():
            print("Arquivo gerado com sucesso.")
            txt_results_directory = os.path.join(output_directory, "reports")
            os.makedirs(txt_results_directory, exist_ok=True)

            target_path = os.path.join(txt_results_directory, output_file)
            shutil.move(output_file, target_path)
            print(f"Arquivo movido para: {target_path}")
        else:
            print("Falha ao gerar o arquivo.")
