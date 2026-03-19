import sys
import os
import shutil

from src.ollama_manager import (
    prepare_ocr_phase,
    switch_to_refiner_phase,
    finalize
)
from src.pdf_processor import extract_pages_as_images
from src.ocr_engine import analyze_layout, extract_markdown, refine_italics
from src.layout_engine import parse_layout_and_crop, integrate_images_to_markdown
from src.converter import create_pdf_from_markdown, compress_pdf


def _ocr_path(output_dir, page_num):
    return os.path.join(output_dir, f"page_{page_num}_ocr.md")

def _refined_path(output_dir, page_num):
    return os.path.join(output_dir, f"page_{page_num}.md")

def _img_path(output_dir, page_num):
    return os.path.join(output_dir, f"page_{page_num}.png")


def _ask_yes_no(question: str, default: bool = True) -> bool:
    """Pregunta al usuario una pregunta de sí/no. Devuelve True para 'sí'."""
    hint = "[S/n]" if default else "[s/N]"
    while True:
        answer = input(f"{question} {hint}: ").strip().lower()
        if answer == "":
            return default
        if answer in ("s", "si", "sí", "y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Por favor responde 's' (sí) o 'n' (no).")


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 main.py <archivo.pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    if not os.path.exists(input_pdf):
        print(f"[ERROR] Archivo no encontrado: {input_pdf}")
        sys.exit(1)

    pdf_filename = os.path.basename(input_pdf)
    pdf_name_no_ext, _ = os.path.splitext(pdf_filename)

    output_base_dir = "output"
    output_dir = os.path.join(output_base_dir, pdf_name_no_ext)
    os.makedirs(output_dir, exist_ok=True)

    final_output_pdf = os.path.join(output_base_dir, f"{pdf_name_no_ext}_final_ocr.pdf")

    # ─────────────────────────────────────────────
    # PREGUNTAS INICIALES DE CONFIGURACIÓN
    # ─────────────────────────────────────────────
    print("\n=== Configuración del proceso ===")
    run_phase2 = _ask_yes_no("¿Deseas ejecutar la Fase 2 (refinamiento con LLM / Qwen)?")
    keep_temp_files = _ask_yes_no("¿Deseas conservar los archivos temporales al finalizar?", default=False)
    print()

    # ─────────────────────────────────────────────
    # DETECTAR ESTADO — ¿desde dónde continuamos?
    # ─────────────────────────────────────────────
    # Reunir qué páginas hay en el directorio temporal
    import re as _re
    # Solo páginas escaneadas: page_N.png (ignorar page_N_img_X.png)
    existing_images = sorted([
        f for f in os.listdir(output_dir)
        if _re.match(r'^page_\d+\.png$', f)
    ], key=lambda f: int(_re.search(r'\d+', f).group()))
    total_pages = len(existing_images)

    existing_ocr = set(
        int(f.replace("page_", "").replace("_ocr.md", ""))
        for f in os.listdir(output_dir) if f.endswith("_ocr.md")
    )
    existing_refined = set(
        int(f.replace("page_", "").replace(".md", ""))
        for f in os.listdir(output_dir)
        if f.endswith(".md") and not f.endswith("_ocr.md")
    )

    if total_pages > 0:
        print(f"\n[INFO] Directorio temporal encontrado con {total_pages} imágenes.")
        print(f"[INFO] Páginas con OCR completado: {len(existing_ocr)}/{total_pages}")
        print(f"[INFO] Páginas con refinamiento completado: {len(existing_refined)}/{total_pages}")
        if len(existing_refined) == total_pages:
            print("[INFO] Todas las páginas ya están procesadas. Saltando directamente a generación de PDF.")
        elif len(existing_ocr) == total_pages:
            print("[INFO] Fase 1 completa. Retomando desde la Fase 2 (refinamiento con Qwen).")
        else:
            print("[INFO] Retomando proceso desde donde se interrumpió.")
    else:
        print(f"\n[INFO] No se encontraron archivos temporales. Iniciando proceso completo.")

    # ─────────────────────────────────────────────
    # FASE 1 — OCR con DeepSeek-OCR
    # ─────────────────────────────────────────────
    pages_needing_ocr = []

    if total_pages == 0:
        # Convertir PDF a imágenes primero
        print("\n--- [1] Inicializando Ollama y cargando DeepSeek-OCR ---")
        prepare_ocr_phase()

        print("\n--- [2] Extracción de PDF a Imágenes ---")
        page_images = extract_pages_as_images(input_pdf, output_dir)
        total_pages = len(page_images)
        pages_needing_ocr = page_images
    else:
        # Las imágenes ya existen, reconstruir lista de páginas
        page_images = []
        for img_file in existing_images:
            page_num = int(img_file.replace("page_", "").replace(".png", ""))
            page_images.append((page_num, os.path.join(output_dir, img_file)))
        page_images.sort(key=lambda x: x[0])

        pages_needing_ocr = [
            (pn, ip) for pn, ip in page_images if pn not in existing_ocr and pn not in existing_refined
        ]

    if pages_needing_ocr:
        print(f"\n--- [3] OCR con DeepSeek-OCR ({len(pages_needing_ocr)} páginas pendientes) ---")
        prepare_ocr_phase()

        for page_num, img_path in pages_needing_ocr:
            print(f"\n>> OCR Página {page_num}/{total_pages}...")

            layout_text = analyze_layout(img_path)
            cropped_images = parse_layout_and_crop(img_path, layout_text, output_dir, page_num)
            markdown_text = extract_markdown(img_path)

            # Guardar como _ocr.md (diferenciado del refinado)
            with open(_ocr_path(output_dir, page_num), "w", encoding="utf-8") as f:
                f.write(markdown_text)

            # Guardar una lista de imágenes recortadas en un archivo auxiliar
            crops_file = os.path.join(output_dir, f"page_{page_num}_crops.txt")
            with open(crops_file, "w", encoding="utf-8") as f:
                f.write("\n".join(cropped_images))

            existing_ocr.add(page_num)
    else:
        print("\n[INFO] Fase 1 (OCR) ya completa. Sin páginas pendientes.")

    # ─────────────────────────────────────────────
    # FASE 2 — Refinamiento con Qwen (opcional)
    # ─────────────────────────────────────────────
    if not run_phase2:
        print("\n[INFO] Fase 2 (refinamiento con LLM) omitida por el usuario.")
        # Usar los archivos _ocr.md directamente como archivo final cuando no hay refinamiento
        for page_num, _ in page_images:
            if page_num not in existing_refined:
                ocr_file = _ocr_path(output_dir, page_num)
                if os.path.exists(ocr_file):
                    with open(ocr_file, "r", encoding="utf-8") as f:
                        raw_markdown = f.read()
                    crops_file = os.path.join(output_dir, f"page_{page_num}_crops.txt")
                    cropped_images = []
                    if os.path.exists(crops_file):
                        with open(crops_file, "r", encoding="utf-8") as f:
                            cropped_images = [line.strip() for line in f if line.strip()]
                    final_md_text = integrate_images_to_markdown(raw_markdown, cropped_images)
                    with open(_refined_path(output_dir, page_num), "w", encoding="utf-8") as f:
                        f.write(final_md_text)
                    existing_refined.add(page_num)
    else:
        pages_needing_refine = [
            pn for pn, _ in page_images if pn not in existing_refined
        ]

        if pages_needing_refine:
            print(f"\n--- [4] Cambiando a Qwen 2.5 para refinamiento ({len(pages_needing_refine)} páginas) ---")
            switch_to_refiner_phase()

            for page_num, _ in [(pn, None) for pn, _ in page_images if pn in pages_needing_refine]:
                print(f"\n>> Refinando página {page_num}/{total_pages}...")

                # Leer raw OCR
                ocr_file = _ocr_path(output_dir, page_num)
                if not os.path.exists(ocr_file):
                    print(f"[WARN] No se encontró archivo OCR para página {page_num}. Saltando.")
                    continue

                with open(ocr_file, "r", encoding="utf-8") as f:
                    raw_markdown = f.read()

                # Leer lista de imágenes recortadas
                crops_file = os.path.join(output_dir, f"page_{page_num}_crops.txt")
                cropped_images = []
                if os.path.exists(crops_file):
                    with open(crops_file, "r", encoding="utf-8") as f:
                        cropped_images = [line.strip() for line in f if line.strip()]

                refined_markdown = refine_italics(raw_markdown, page_num)
                final_md_text = integrate_images_to_markdown(refined_markdown, cropped_images)

                with open(_refined_path(output_dir, page_num), "w", encoding="utf-8") as f:
                    f.write(final_md_text)

                existing_refined.add(page_num)
        else:
            print("\n[INFO] Fase 2 (refinamiento) ya completa. Sin páginas pendientes.")

    # ─────────────────────────────────────────────
    # FASE 3 — Compilación de PDF Final
    # ─────────────────────────────────────────────
    md_files = [_refined_path(output_dir, pn) for pn, _ in sorted(page_images, key=lambda x: x[0])]

    print(f"\n--- [6] Generando PDF Final ({len(md_files)} páginas) ---")
    create_pdf_from_markdown(md_files, final_output_pdf)

    # ─────────────────────────────────────────────
    # COMPRESIÓN DE PDF
    # ─────────────────────────────────────────────
    compressed_pdf = final_output_pdf.replace(".pdf", "_compressed.pdf")
    if compress_pdf(final_output_pdf, compressed_pdf):
        # Si la compresión tuvo éxito, reemplazamos el original
        try:
            os.remove(final_output_pdf)
            os.rename(compressed_pdf, final_output_pdf)
            print(f"[INFO] PDF comprimido reemplazó al original.")
        except Exception as e:
            print(f"[WARN] No se pudo reemplazar el PDF original con el comprimido: {e}")
    else:
        print("[WARN] Se mantendrá el PDF original sin comprimir.")

    print("\n--- [7] Descargando todos los modelos de la VRAM ---")
    finalize()

    if keep_temp_files:
        print(f"\n[INFO] Archivos temporales conservados en: {output_dir}")
    else:
        print("\n--- [8] Limpiando archivos temporales ---")
        try:
            shutil.rmtree(output_dir)
            print(f"[INFO] Archivos temporales eliminados en {output_dir}")
        except Exception as e:
            print(f"[WARN] No se pudo limpiar la carpeta temporal: {e}")

    print(f"\n[ÉXITO] Proceso completado. Archivo final: {final_output_pdf}")


if __name__ == "__main__":
    main()
