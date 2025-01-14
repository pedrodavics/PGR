import os
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import re


def criar_subpasta_pdf():
    output_dir = "./output/pdf"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def limpar_texto(texto):
    texto_limpo = texto.replace("\n", " ").strip()
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
    return texto_limpo


def mapear_sessoes_pdf(caminho_pdf, sessoes_mapear):
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
        return sessoes
    except Exception as e:
        print(f"Erro ao mapear sessões: {e}")
        return {}


def adicionar_informacoes(caminho_pdf, sessoes, arquivos_txt):
    output_dir = criar_subpasta_pdf()
    pdf_final_path = os.path.join(output_dir, "relatorio_atualizado.pdf")
    
    try:
        reader = PdfReader(caminho_pdf)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            # Criar um canvas temporário para sobrepor texto
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=letter)
            c.setFont("Helvetica", 10)

            if i in sessoes.values():
                sessao_nome = list(sessoes.keys())[list(sessoes.values()).index(i)]
                arquivo_txt = arquivos_txt.get(sessao_nome)
                
                if arquivo_txt:
                    with open(arquivo_txt, "r", encoding="utf-8") as file:
                        conteudo = file.readlines()
                    
                    # Coordenadas para inserir o texto no PDF
                    x_start = 72
                    y_start = 680
                    
                    # Adicionar texto linha por linha
                    for linha in conteudo:
                        c.drawString(x_start, y_start, linha.strip())
                        y_start -= 12
                        if y_start < 50:  # Evitar ultrapassar os limites da página
                            break
            
            c.save()
            packet.seek(0)

            # Mesclar a página original com o overlay
            overlay_reader = PdfReader(packet)
            overlay_page = overlay_reader.pages[0]
            page.merge_page(overlay_page)

            writer.add_page(page)
        
        with open(pdf_final_path, "wb") as output_file:
            writer.write(output_file)

        print(f"PDF atualizado gerado com sucesso: {pdf_final_path}")
        return pdf_final_path
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
