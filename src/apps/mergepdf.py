from pypdf import PdfReader, PdfWriter
import os

def main():
    # Caminhos absolutos dos arquivos
    template_pdf_path = '/home/tauge/Documents/tauge/PGR/static/assets/template pgr final.pdf'
    pgr_final_pdf_path = '/home/tauge/Documents/tauge/PGR/output/pdf temp/pgr_final.pdf'
    
    # Verifica se os arquivos existem
    if not os.path.isfile(template_pdf_path):
        print(f"Erro: O arquivo do template não foi encontrado: {template_pdf_path}")
        return
    if not os.path.isfile(pgr_final_pdf_path):
        print(f"Erro: O arquivo pgr_final não foi encontrado: {pgr_final_pdf_path}")
        return
    
    # Abre os PDFs
    template_reader = PdfReader(template_pdf_path)
    pgr_final_reader = PdfReader(pgr_final_pdf_path)
    
    writer = PdfWriter()
    
    # Mapeamento de substituições
    replacements = {
        3: 0,   # Página 4 do template -> Página 1 do pgr_final
        9: 1,   # Página 10 do template -> Página 2 do pgr_final
        10: 2,  # Página 11 do template -> Página 3 do pgr_final
        11: 3   # Página 12 do template -> Página 4 do pgr_final
    }
    
    # Adiciona as 12 primeiras páginas do template (páginas 1 a 12)
    for i in range(12):  # índices 0 a 11 correspondem às páginas 1 a 12
        if i in replacements:
            writer.add_page(pgr_final_reader.pages[replacements[i]])
        else:
            writer.add_page(template_reader.pages[i])
    
    # Insere a página 5 do pgr_final.pdf (índice 4) como página 13 do relatorio.pdf
    writer.add_page(pgr_final_reader.pages[4])
    
    # Adiciona o restante das páginas do template
    # A partir da página 13 do template (índice 12)
    for i in range(12, len(template_reader.pages)):
        writer.add_page(template_reader.pages[i])
    
    # Define o caminho da pasta de saída e cria-a, se não existir
    output_dir = '/home/tauge/Documents/tauge/PGR/output'
    os.makedirs(output_dir, exist_ok=True)
    output_pdf_path = os.path.join(output_dir, 'relatorio.pdf')
    
    # Salva o novo PDF
    with open(output_pdf_path, 'wb') as f:
        writer.write(f)
    
    print("PDF gerado com sucesso:", output_pdf_path)

if __name__ == '__main__':
    main()
