import os
import io
import re
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def criar_subpasta_pdf(output_dir="./output/pdf"):
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def criar_log_dir(log_dir="./logs"):
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def salvar_log(log_path, mensagem):
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(mensagem + "\n")

def limpar_texto(texto):
    texto_limpo = texto.replace("\n", " ").strip()
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    return texto_limpo

def mapear_sessoes_pdf(caminho_pdf, sessoes_mapear, log_path):
    try:
        reader = PdfReader(caminho_pdf)
        sessoes = {}
        for i, page in enumerate(reader.pages):
            texto = page.extract_text()
            if texto:
                texto_limpo = limpar_texto(texto)
                for sessao in sessoes_mapear:
                    if sessao.lower() in texto_limpo.lower():
                        sessoes[sessao] = i
                        salvar_log(log_path, f"Sessão '{sessao}' encontrada na página {i + 1}")
        return sessoes
    except Exception as e:
        salvar_log(log_path, f"Erro ao mapear sessões: {e}")
        return {}

def adicionar_texto_ao_pdf(c, texto, x_start, y_start):
    for linha in texto:
        c.drawString(x_start, y_start, linha.strip())
        y_start -= 12
        if y_start < 50:  # Evitar que o texto ultrapasse o limite da página
            break
    return y_start

def adicionar_imagem_ao_pdf(c, img_path, x_start, y_start, img_width=200, img_height=250, log_path=None):
    try:
        if y_start - img_height - 20 < 50:  # Checar se a imagem cabe na página
            mensagem = f"Espaço insuficiente para a imagem {img_path}. Ajuste o layout."
            if log_path:
                salvar_log(log_path, mensagem)
            return y_start
        c.drawImage(img_path, x_start, y_start - img_height - 20, width=img_width, height=img_height)
        if log_path:
            salvar_log(log_path, f"Imagem {img_path} adicionada com sucesso.")
        return y_start - img_height - 30
    except Exception as e:
        mensagem = f"Erro ao adicionar imagem {img_path}: {e}"
        if log_path:
            salvar_log(log_path, mensagem)
        return y_start

def adicionar_informacoes(caminho_pdf, sessoes, arquivos_txt, output_dir, log_path):
    pdf_final_path = os.path.join(output_dir, "relatorio.pdf")

    try:
        reader = PdfReader(caminho_pdf)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=letter)
            c.setFont("Helvetica", 10)

            sessoes_na_pagina = [sessao for sessao, pagina in sessoes.items() if pagina == i]

            if sessoes_na_pagina:
                salvar_log(log_path, f"Processando página {i + 1} com sessões: {', '.join(sessoes_na_pagina)}")
                y_position = 680

                for sessao_nome in sessoes_na_pagina:
                    salvar_log(log_path, f"Processando sessão: {sessao_nome}")
                    arquivo_txt = arquivos_txt.get(sessao_nome)

                    if arquivo_txt and os.path.exists(arquivo_txt):
                        with open(arquivo_txt, "r", encoding="utf-8") as file:
                            conteudo = file.readlines()
                        y_position = adicionar_texto_ao_pdf(c, conteudo, x_start=72, y_start=y_position)
                        salvar_log(log_path, f"Texto da sessão '{sessao_nome}' adicionado com sucesso.")

                    if sessao_nome == "9.1 Memória":
                        salvar_log(log_path, f"Tentando adicionar gráfico de memória.")
                        y_position = adicionar_imagem_ao_pdf(
                            c,
                            "./output/graficos_38/H.São Paulo - New Oracle Prod/grafico_4656.png",
                            x_start=72,
                            y_start=y_position,
                            img_width=500,
                            img_height=160,
                            log_path=log_path
                        )
                    elif sessao_nome == "9.2 CPU":
                        salvar_log(log_path, f"Tentando adicionar gráfico de CPU.")
                        y_position = adicionar_imagem_ao_pdf(
                            c,
                            "./output/graficos_38/H.São Paulo - New Oracle Prod/grafico_4652.png",
                            x_start=72,
                            y_start=y_position,
                            img_width=500,
                            img_height=150,
                            log_path=log_path
                        )

            c.save()
            packet.seek(0)

            overlay_reader = PdfReader(packet)
            overlay_page = overlay_reader.pages[0]
            page.merge_page(overlay_page)

            writer.add_page(page)

        with open(pdf_final_path, "wb") as output_file:
            writer.write(output_file)

        salvar_log(log_path, f"PDF atualizado gerado com sucesso: {pdf_final_path}")
        return pdf_final_path
    except Exception as e:
        salvar_log(log_path, f"Erro ao adicionar informações: {e}")
        return None

def manipular_pdf():
    caminho_pdf = "./static/assets/Template relatorio tauge.pdf"
    log_dir = criar_log_dir()
    log_path = os.path.join(log_dir, "pdf.log")

    sessoes_mapear = ["INFORMAÇÕES DE SERVIDOR", "9.1 Memória", "9.2 CPU"]

    arquivos_txt = {
        "INFORMAÇÕES DE SERVIDOR": "./output/txt_results/result_os.txt",
    }

    output_dir = criar_subpasta_pdf()
    sessoes = mapear_sessoes_pdf(caminho_pdf, sessoes_mapear, log_path)

    if not sessoes:
        salvar_log(log_path, "Nenhuma sessão mapeada no PDF.")
        return

    pdf_atualizado = adicionar_informacoes(caminho_pdf, sessoes, arquivos_txt, output_dir, log_path)

    if pdf_atualizado:
        salvar_log(log_path, f"Arquivo gerado: {pdf_atualizado}")
    else:
        salvar_log(log_path, "Erro ao gerar o arquivo atualizado.")

if __name__ == "__main__":
    manipular_pdf()
