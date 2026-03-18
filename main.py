import sys
import os
import shutil

from src.ollama_manager import load_ocr_model
from src.pdf_processor import extract_pages_as_images
from src.ocr_engine import analyze_layout, extract_markdown
from src.layout_engine import parse_layout_and_crop, integrate_images_to_markdown
from src.converter import create_pdf_from_markdown

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <archivo.pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    if not os.path.exists(input_pdf):
        print(f"[ERROR] Found no such file: {input_pdf}")
        sys.exit(1)

    pdf_filename = os.path.basename(input_pdf)
    pdf_name_no_ext, _ = os.path.splitext(pdf_filename)
    
    # 1. Setup output directory structure
    output_base_dir = "output"
    output_dir = os.path.join(output_base_dir, pdf_name_no_ext)
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Check and load Ollama
    print("\n--- [1] Inicializando Ollama y Modelos ---")
    load_ocr_model()
    
    # 3. PDF to Images
    print("\n--- [2] Extracción de PDF a Imágenes ---")
    page_images = extract_pages_as_images(input_pdf, output_dir)
    
    # 4. Process each page sequentially
    print("\n--- [3] Procesando páginas con DeepSeek-OCR ---")
    md_files = []
    
    for page_num, img_path in page_images:
        print(f"\n>> Procesando página {page_num}...")
        
        # 4a. Layout analysis
        layout_text = analyze_layout(img_path)
        
        # 4b. Crop images based on layout
        cropped_images = parse_layout_and_crop(img_path, layout_text, output_dir, page_num)
        
        # 4c. Extract text
        markdown_text = extract_markdown(img_path)
        
        # 4d. Integrate images
        final_md_text = integrate_images_to_markdown(markdown_text, cropped_images)
        
        # 4e. Save to temporary markdown file
        md_file_path = os.path.join(output_dir, f"page_{page_num}.md")
        with open(md_file_path, "w", encoding="utf-8") as f:
            f.write(final_md_text)
            
        md_files.append(md_file_path)

    # 5. Compile into final PDF
    print("\n--- [4] Generando PDF Final ---")
    final_output_pdf = os.path.join(output_base_dir, f"{pdf_name_no_ext}_final_ocr.pdf")
    create_pdf_from_markdown(md_files, final_output_pdf)
    
    # 6. Auto-cleanup temporary files
    print("\n--- [5] Limpiando archivos temporales ---")
    try:
        shutil.rmtree(output_dir)
        print(f"[INFO] Se eliminaron los archivos temporales en {output_dir}")
    except Exception as e:
        print(f"[WARN] No se pudo limpiar la carpeta temporal: {e}")

    print(f"\n[ÉXITO] Proceso completado. El archivo final está en: {final_output_pdf}")

if __name__ == "__main__":
    main()
