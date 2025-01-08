import os
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import re

def criar_subpasta_pdf():
    output_dir = "./output/pdf"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def limpar_texto(texto):
    # Remover quebras de linha extras e espaços no início e no final
    texto_limpo = texto.replace("\n", " ").strip()
    # Remover múltiplos espaços consecutivos
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    return texto_limpo

def mapear_sessoes_pdf(caminho_pdf, sessoes_mapear):
    try:
        reader = PdfReader(caminho_pdf)
        sessoes = {}
        for i, page in enumerate(reader.pages):
            texto = page.extract_text()
            if texto:  # Verificar se o texto foi extraído
                texto_limpo = limpar_texto(texto)  # Limpeza do texto extraído
                print(f"Texto da página {i}: {texto_limpo[:300]}...")  # Exibir uma parte do texto limpo para depuração
                for sessao in sessoes_mapear:
                    if sessao.lower() in texto_limpo.lower():  # Ignorar maiúsculas/minúsculas
                        sessoes[sessao] = i
        return sessoes
    except Exception as e:
        print(f"Erro ao mapear sessões: {e}")
        return {}

def adicionar_informacoes(caminho_pdf, sessoes, arquivos_txt):
    output_dir = criar_subpasta_pdf()
    pdf_path = os.path.join(output_dir, "relatorio_atualizado.pdf")
    
    try:
        reader = PdfReader(caminho_pdf)
        writer = PdfWriter()
        
        for i, page in enumerate(reader.pages):
            writer.add_page(page)
            if i in sessoes.values():
                # Adicionar novas informações a partir do arquivo .txt
                sessao_nome = list(sessoes.keys())[list(sessoes.values()).index(i)]
                arquivo_txt = arquivos_txt.get(sessao_nome)

                if arquivo_txt:
                    with open(arquivo_txt, "r", encoding="utf-8") as file:
                        conteudo = file.readlines()

                    # Criar o canvas para adicionar o texto
                    c = canvas.Canvas(pdf_path, pagesize=letter)
                    c.setFont("Helvetica", 12)
                    c.setFillColor(colors.black)
                    
                    # Encontre a posição da sessão mapeada
                    texto_pagina = page.extract_text()
                    texto_limpo = limpar_texto(texto_pagina)
                    posicao_sessao = texto_limpo.lower().find(sessao_nome.lower())
                    
                    # Calcula o ponto de inserção para o novo texto (logo abaixo da sessão)
                    y_position = 600  # Posição inicial ajustada
                    if posicao_sessao != -1:
                        # Ajustar a posição vertical
                        y_position -= 40  # Ajustar para o começo da sessão

                    # Desenha o texto adicional
                    for linha in conteudo:
                        c.drawString(72, y_position, linha.strip())
                        y_position -= 20  # Desce a linha

                        # Verifique se o conteúdo excede a página e diminua o tamanho da fonte
                        if y_position < 72:  # Se o conteúdo ultrapassar a margem
                            c.setFont("Helvetica", 10)  # Reduzir o tamanho da fonte
                            y_position = 600  # Voltar para a posição inicial na mesma página
                            c.drawString(72, y_position, linha.strip())  # Adiciona a linha na nova posição
                            y_position -= 20  # Desce a linha novamente

                    c.showPage()
                    c.save()
                    writer.append(pdf_path)

        with open(pdf_path, "wb") as output_file:
            writer.write(output_file)

        print(f"PDF atualizado gerado com sucesso: {pdf_path}")
        return pdf_path
   
    except Exception as e:
        print(f"Erro ao adicionar informações: {e}")
        return None

def manipular_pdf():
    caminho_pdf = "./static/assets/Template de relatorio tauge.pdf"
    
    sessoes_mapear = ["INFORMAÇÕES DE SERVIDOR"]
    arquivos_txt = {
        "INFORMAÇÕES DE SERVIDOR": "./output/txt_results/result_os.txt",
    }

    sessoes = mapear_sessoes_pdf(caminho_pdf, sessoes_mapear)
    
    if not sessoes:
        print("Nenhuma sessão mapeada no PDF.")
        return
    
    pdf_atualizado = adicionar_informacoes(caminho_pdf, sessoes, arquivos_txt)
    
    if pdf_atualizado:
        print(f"Arquivo gerado: {pdf_atualizado}")
    else:
        print("Erro ao gerar o arquivo atualizado.")

if __name__ == "__main__":
    manipular_pdf()