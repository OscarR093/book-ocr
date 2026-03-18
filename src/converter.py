import fitz
import os
import re
import markdown

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
    css = """
    * { font-family: sans-serif; }
    body { font-size: 11pt; line-height: 1.5; color: #333; }
    h1 { font-size: 18pt; font-weight: bold; margin-top: 1.5em; margin-bottom: 0.5em; }
    h2 { font-size: 16pt; font-weight: bold; margin-top: 1.2em; margin-bottom: 0.5em; }
    h3 { font-size: 14pt; font-weight: bold; margin-top: 1em; margin-bottom: 0.5em; }
    p { margin-bottom: 10pt; text-align: justify; }
    img { max-width: 100%; margin-top: 10pt; margin-bottom: 10pt; }
    strong { font-weight: bold; }
    em { font-style: italic; }
    """

    writer = fitz.DocumentWriter(output_pdf_path)

    for md_file in markdown_files:
        if not os.path.exists(md_file):
            continue
            
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
            
            while more:
                device = writer.begin_page(page_rect)
                more, _ = story.place(content_rect)
                story.draw(device, None)
                writer.end_page()
                    
        except Exception as e:
            print(f"[ERROR] Failed to render HTML story for {md_file}: {e}")
            # If an error occurs, insert at least a blank page or ignore
            device = writer.begin_page(page_rect)
            writer.end_page()

    writer.close()
    print(f"[INFO] Saved final PDF successfully.")
