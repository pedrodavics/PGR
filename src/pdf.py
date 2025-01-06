import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak, Image, HRFlowable
)
from reportlab.lib.units import inch
from reportlab.lib import colors
from PyPDF2 import PdfMerger

def remover_tags_html(texto):
    return re.sub(r'<.*?>', '', texto)

def desenhar_rodape(canvas_obj, doc):
    canvas_obj.setFont("Helvetica", 10)
    page_num = doc.page
    text = f"Página {page_num + 1}" 
    canvas_obj.drawRightString(letter[0] - 50, 30, text)
    canvas_obj.drawString(50, 30, "Tauge Tecnologia")

def criar_capa(output_path):
    from reportlab.pdfgen import canvas

    largura, altura = letter
    c = canvas.Canvas(output_path, pagesize=letter)

    # Título principal
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(largura / 2, altura - 200, "Relatório Situacional")
    c.setFont("Helvetica", 16)
    c.setFillColor(colors.grey)

    # Logotipo
    try:
        img_path = "tauge.jpeg"
        c.drawImage(img_path, largura / 2 - 2.5 * inch, altura / 2 - 1.25 * inch, width=5 * inch, height=2.5 * inch)
    except FileNotFoundError:
        c.setFont("Helvetica", 12)
        c.setFillColor("red")
        c.drawCentredString(largura / 2, altura / 2, "Erro: Imagem da empresa não encontrada.")

    c.showPage()
    c.save()

def adicionar_sessao(titulo, arquivo, pdf_content):
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'titulo',
        fontSize=20,
        leading=22,
        fontName="Helvetica-Bold",
        textColor=colors.black,
        alignment=1,  # Centralizado
        spaceAfter=10
    )
    titulo_formatado = Paragraph(titulo, titulo_style)
    pdf_content.append(titulo_formatado)
    pdf_content.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    pdf_content.append(Spacer(1, 12))

    with open(arquivo, "r", encoding="utf-8") as file:
        linhas = file.readlines()
        for linha in linhas:
            if not linha.strip().startswith("Comando:"):
                linha_limpa = remover_tags_html(linha.strip())
                paragrafo = Paragraph(linha_limpa, styles['Normal'])
                pdf_content.append(paragrafo)
                pdf_content.append(Spacer(1, 6))

def adicionar_graficos(pdf_content):
    styles = getSampleStyleSheet()
    titulo = Paragraph("<font size=18><b>Gráficos</b></font>", styles['Heading2'])
    pdf_content.append(titulo)
    pdf_content.append(Spacer(1, 12))

    graficos = ["grafico1.jpeg"]
    imagem_size = 5 * inch

    for grafico in graficos:
        try:
            img = Image(grafico, width=imagem_size, height=imagem_size)
            img.hAlign = 'CENTER'
            pdf_content.append(img)
            pdf_content.append(Spacer(1, 12))
        except FileNotFoundError:
            erro = Paragraph(f"<font size=12 color='red'>Erro: Arquivo {grafico} não encontrado.</font>", styles['Normal'])
            pdf_content.append(erro)

def gerar_pdf():
    capa_path = "relatorio_capa.pdf"
    output_path = "relatorio.pdf"

    # Cria a capa
    criar_capa(capa_path)

    # Configura o documento principal
    doc = BaseDocTemplate(output_path, pagesize=letter)

    # Frames e Templates
    frame = Frame(
        doc.leftMargin, doc.bottomMargin + 0.5 * inch,
        doc.width, doc.height - 0.5 * inch, id='normal'
    )
    conteudo_template = PageTemplate(id='Conteudo', frames=frame, onPage=desenhar_rodape)
    doc.addPageTemplates([conteudo_template])

    pdf_content = []

    # Conteúdo
    adicionar_sessao("1 - Informações do Sistema Operacional", "sistema_info.txt", pdf_content)
    pdf_content.append(PageBreak())
    adicionar_sessao("2 - Resultados de Consultas Oracle", "resultado_consulta.txt", pdf_content)
    pdf_content.append(PageBreak())
    adicionar_graficos(pdf_content)

    # Constrói o PDF
    doc.build(pdf_content)

    # Junta capa e conteúdo
    merger = PdfMerger()
    merger.append(capa_path)
    merger.append(output_path)
    merger.write(output_path)
    merger.close()

    print(f"PDF gerado com sucesso: {output_path}")


if __name__ == "__main__":
    gerar_pdf()  
