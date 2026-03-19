import fitz
import os
import re
import markdown
import subprocess

from src.config import PDF_FONT_NORMAL, PDF_FONT_BOLD, PDF_FONT_ITALIC, GS_PDF_SETTINGS

def create_pdf_from_markdown(markdown_files, output_pdf_path):
    """
    Creates a final PDF using PyMuPDF from a list of markdown files containing text and images.
    Uses the 'markdown' python library to convert text to HTML and fitz.Story with
    fitz.DocumentWriter to render proper text formatting (bold, headers, italics) 
    and image embeddings seamlessly.
    """
    print(f"[INFO] Generating final PDF: {output_pdf_path}")
    
    page_width = 595
    page_height = 842
    margin = 50
    page_rect = fitz.Rect(0, 0, page_width, page_height)
    content_rect = fitz.Rect(margin, margin, page_width - margin, page_height - margin)

    # Basic CSS for formatting the HTML story
    css = f"""
    * {{ font-family: {PDF_FONT_NORMAL}; }}
    body {{ font-size: 13pt; line-height: 1.5; color: #333; }}
    h1 {{ font-size: 20pt; font-weight: bold; font-family: {PDF_FONT_BOLD}; margin-top: 1.5em; margin-bottom: 0.5em; }}
    h2 {{ font-size: 18pt; font-weight: bold; font-family: {PDF_FONT_BOLD}; margin-top: 1.2em; margin-bottom: 0.5em; }}
    h3 {{ font-size: 16pt; font-weight: bold; font-family: {PDF_FONT_BOLD}; margin-top: 1em; margin-bottom: 0.5em; }}
    p {{ margin-bottom: 10pt; text-align: justify; }}
    img {{ max-width: 100%; margin-top: 10pt; margin-bottom: 10pt; }}
    strong {{ font-weight: bold; font-family: {PDF_FONT_BOLD}; }}
    em {{ font-style: italic; font-family: {PDF_FONT_ITALIC}; }}
    """

    total_files = len([f for f in markdown_files if os.path.exists(f)])
    print(f"[INFO] Iniciando generación de PDF: {total_files} archivos Markdown a procesar.")
    print(f"[INFO] Ruta de salida: {output_pdf_path}")

    writer = fitz.DocumentWriter(output_pdf_path)
    pages_written = 0

    for i, md_file in enumerate(markdown_files, 1):
        if not os.path.exists(md_file):
            print(f"[WARN] [{i}/{total_files}] Archivo no encontrado, omitiendo: {md_file}")
            continue

        print(f"[INFO] [{i}/{total_files}] Renderizando: {os.path.basename(md_file)}...", end=" ", flush=True)
            
        with open(md_file, "r", encoding="utf-8") as f:
            md_text = f.read()

        # Convert relative image paths to absolute paths to ensure Story can find them
        def repl(match):
            alt = match.group(1)
            path = os.path.abspath(match.group(2))
            return f'![{alt}]({path})'
            
        md_text = re.sub(r'!\[([^\]]*)\]\((.*?)\)', repl, md_text)
        
        # Recopilar todos los directorios únicos de imágenes para el Archive
        # (fitz.Archive necesita saber dónde buscar los archivos de imagen)
        img_dirs = set()
        img_paths_found = re.findall(r'!\[([^\]]*)\]\((.*?)\)', md_text)
        for _, img_path in img_paths_found:
            abs_path = os.path.abspath(img_path)
            if os.path.exists(abs_path):
                img_dirs.add(os.path.dirname(abs_path))
        
        # Convertir Markdown a HTML
        # El markdown library usa rutas tal cual, así que debemos usar el basename en el HTML
        # y dejar que Archive resuelva la ruta completa
        def repl_html(match):
            alt = match.group(1)
            path = os.path.abspath(match.group(2))
            # Pasar solo el nombre del archivo; Archive buscará en los directorios registrados
            return f'<img src="{os.path.basename(path)}" alt="{alt}"/>'
        
        html_content = markdown.markdown(md_text, extensions=['extra', 'tables'])
        # Reemplazar tags de img que el markdown generó con versiones que usan solo el basename
        html_content = re.sub(
            r'<img ([^>]*)src="([^"]+)"([^>]*)>',
            lambda m: f'<img {m.group(1)}src="{os.path.basename(m.group(2))}"{m.group(3)}>',
            html_content
        )
        html_doc = f"<html><body>{html_content}</body></html>"
        
        # Usar la clase Story de PyMuPDF para renderizar el HTML con formato
        try:
            # Crear un Archive que apunte a todos los directorios donde hay imágenes
            archive = fitz.Archive()
            for img_dir in img_dirs:
                archive.add(img_dir)

            story = fitz.Story(html=html_doc, user_css=css, archive=archive)
            more = 1
            page_count = 0
            MAX_PAGES_PER_MD = 50  # límite de seguridad anti-bucle infinito

            while more and page_count < MAX_PAGES_PER_MD:
                device = writer.begin_page(page_rect)
                more, _ = story.place(content_rect)
                story.draw(device, None)
                writer.end_page()
                page_count += 1

            if page_count >= MAX_PAGES_PER_MD and more:
                print(f"AVISO (límite {MAX_PAGES_PER_MD} páginas alcanzado, contenido truncado)")
            else:
                print(f"OK ({page_count} página(s) de PDF generada(s))")

            pages_written += 1

        except Exception as e:
            print(f"ERROR")
            print(f"[ERROR] Fallo al renderizar {os.path.basename(md_file)}: {e}")
            # Insertar página en blanco para no perder paginación
            device = writer.begin_page(page_rect)
            writer.end_page()

    try:
        writer.close()
    except Exception as e:
        print(f"[ERROR] Fallo al cerrar el DocumentWriter: {e}")
        raise

    print(f"\n[INFO] PDF generado exitosamente. {pages_written}/{total_files} páginas renderizadas correctamente.")
    print(f"[INFO] Archivo guardado en: {output_pdf_path}")


def compress_pdf(input_path, output_path):
    """
    Comprime un PDF usando Ghostscript.
    Requiere que 'gs' esté instalado en el sistema.
    """
    print(f"\n[INFO] Comprimiendo PDF con Ghostscript (modo {GS_PDF_SETTINGS})...")
    
    cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={GS_PDF_SETTINGS}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[INFO] Compresión finalizada correctamente.")
            return True
        else:
            print(f"[ERROR] Ghostscript falló: {result.stderr}")
            return False
    except FileNotFoundError:
        print("[ERROR] Ghostscript ('gs') no está instalado en el sistema.")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado durante la compresión: {e}")
        return False
