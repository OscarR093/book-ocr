import fitz  # PyMuPDF
import os

def extract_pages_as_images(pdf_path, output_dir):
    """
    Extracts all pages from the PDF as images and saves them to the output directory.
    Returns a list of tuples containing (page_number, image_path).
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"[INFO] Extracting pages from {pdf_path} into images...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    page_images = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Determine the resolution. dpi=300 is usually good for OCR.
        pix = page.get_pixmap(dpi=300)
        
        image_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
        pix.save(image_path)
        
        page_images.append((page_num + 1, image_path))
        print(f"[INFO] Saved page {page_num + 1} to {image_path}")
        
    doc.close()
    return page_images
