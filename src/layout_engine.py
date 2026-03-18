import os
import re
from PIL import Image

def parse_layout_and_crop(image_path, layout_text, output_dir, page_num):
    """
    Parses the layout text from DeepSeek-OCR to find image bounding boxes, crops them,
    and returns a modified markdown pointing to the cropped images.
    
    NOTE: DeepSeek-OCR grounding output is typically in the format:
    some text or description [[x1, y1, x2, y2]]
    or outputting specific <box> components.
    This implementation does a basic search for coordinates like [[x1, y1, x2, y2]]
    and crops those regions if they correspond to 'figure' or 'image' mentions.
    If the layout output is not standard, we might not crop anything.
    """
    img = Image.open(image_path)
    img_width, img_height = img.size
    
    cropped_images = []
    
    # Simple regex to find coordinate boxes like [[100, 200, 300, 400]]
    # or [100, 200, 300, 400] that DeepSeek might output.
    # Usually DeepSeek outputs normalized coordinates (0-1000)
    idx = 1
    
    # Buscar patrones generados por DeepSeek-OCR para imágenes o figuras
    # Ejemplo: <|ref|>figure<|/ref|><|det|>[[100, 200, 300, 400]]<|/det|>
    pattern = r'<\|ref\|>[^<]*?(?:figure|image|illustration|picture|table)[^<]*?<\|/ref\|>.*?<\|det\|>.*?(\d+),\s*(\d+),\s*(\d+),\s*(\d+).*?<\|/det\|>'
    bboxes = re.findall(pattern, layout_text, re.IGNORECASE)
         
    for bbox in bboxes:
        try:
            x1, y1, x2, y2 = map(int, bbox)
            
            # DeepSeek-OCR usually outputs coordinates on a 1000x1000 scale
            # We need to map them to the actual image size
            real_x1 = int((x1 / 1000.0) * img_width)
            real_y1 = int((y1 / 1000.0) * img_height)
            real_x2 = int((x2 / 1000.0) * img_width)
            real_y2 = int((y2 / 1000.0) * img_height)
            
            # Ensure valid bounds
            real_x1 = max(0, real_x1)
            real_y1 = max(0, real_y1)
            real_x2 = min(img_width, real_x2)
            real_y2 = min(img_height, real_y2)
            
            if real_x2 <= real_x1 or real_y2 <= real_y1:
                continue
                
            cropped_img = img.crop((real_x1, real_y1, real_x2, real_y2))
            
            crop_filename = f"page_{page_num}_img_{idx}.png"
            crop_path = os.path.join(output_dir, crop_filename)
            cropped_img.save(crop_path)
            
            cropped_images.append(crop_path)
            print(f"[INFO] Cropped image saved to {crop_path}")
            idx += 1
            
        except Exception as e:
            print(f"[ERROR] Failed to crop region {bbox}: {e}")
            
    return cropped_images

def integrate_images_to_markdown(markdown_text, cropped_images):
    """
    Appends the cropped images as markdown references at the end of the page text.
    Ideally, we would replace the exact bounding box reference in the text with the image link,
    but simply appending them ensures we don't lose the images.
    """
    updated_md = markdown_text + "\n\n"
    for img_path in cropped_images:
        filename = os.path.basename(img_path)
        # Using relative or absolute path based on how the PDF generation will handle it.
        # We will keep absolute path for PDF generation simplicity
        updated_md += f"![image]({img_path})\n\n"
        
    return updated_md
