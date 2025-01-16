import paramiko
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from flask import Flask, send_file, jsonify, request
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

host = os.getenv("HOST")
port = os.getenv("PORT")
username = os.getenv("USER_OS")
password = os.getenv("PASS_OS")

output_file = "result_os.txt"
commands_file = "src/scripts/executable/commands.sh"  

def read_commands_from_file(filename):
    try:
        with open(filename, "r") as file:
            commands = [line.strip() for line in file.readlines() if line.strip() and not line.startswith("#")]
        return commands
    except Exception as e:
        print(f"Erro ao ler o arquivo de comandos: {e}")
        return []

commands = read_commands_from_file(commands_file)

def run_remote_command(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    return output if output else error

def process_command(ssh_client, command):
    command = command.strip()
    if command and not command.startswith("#"):
        print(f"Executando comando: {command}")
        result = run_remote_command(ssh_client, command)
        return f"{result}\n\n"  
    return ""

def generate_file():
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(hostname=host, port=port, username=username, password=password)
        print(f"Conectado com sucesso a {host}:{port}")

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
        ssh_client.close()
        print("Conexão SSH encerrada.")

output_directory = "./output"

@app.route('/executar_comandos', methods=["GET"])
def executar_comandos():
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
