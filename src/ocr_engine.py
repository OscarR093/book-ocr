import requests
import base64
import os
import json
import re

from src.ollama_manager import OCR_MODEL, OLLAMA_API_BASE

def _encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_markdown(image_path):
    """
    Given an image path, return the full page text content converted to markdown.
    Uses DeepSeek-OCR specific prompt sensitivity recommendations.
    """
    print(f"[INFO] Extracting full text/markdown from {os.path.basename(image_path)}...")
    base64_image = _encode_image(image_path)
    
    # Prompt is critical for DeepSeek-OCR
    prompt = "<|grounding|>Convert the document to markdown."
    
    payload = {
        "model": OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64_image]
            }
        ],
        "stream": False
    }

    try:
        response = requests.post(f"{OLLAMA_API_BASE}/chat", json=payload)
        if response.status_code == 200:
            data = response.json()
            content = data.get("message", {}).get("content", "")
            # Limpiar etiquetas de coordenadas de DeepSeek (<|ref|>...<|/det|>)
            cleaned = re.sub(r'<\|ref\|>.*?<\|/ref\|><\|det\|>.*?<\|/det\|>\s*', '', content)
            return cleaned
        else:
            print(f"[ERROR] OCR Extraction failed: {response.text}")
            return ""
    except requests.RequestException as e:
        print(f"[ERROR] Request to Ollama API failed: {e}")
        return ""

def analyze_layout(image_path):
    """
    Given an image path, analyze the layout.
    For DeepSeek-OCR, we can use specific prompts to get layout components, finding figures/images.
    (Note: DeepSeek-OCR may output coordinates for figures. If not, we fall back to other layout tools or prompt tweaking.)
    In this preliminary implementation, we will ask it to list bounding boxes of images if possible,
    Or use another prompt. We will use the 'Parse the figure.' prompt from docs to see if it acts on specific images,
    but for full layout `Given the layout of the image.` might return structure.
    Let's initially try to request just the figure locations if supported, or gracefully degraded to text-only mode
    if layout extraction is too complex.
    """
    print(f"[INFO] Analyzing layout for {os.path.basename(image_path)}...")
    base64_image = _encode_image(image_path)
    
    # Prompt to get layout/bounding boxes for images. 
    # DeepSeek-OCR doc says "<|grounding|>Given the layout of the image."
    prompt = "<|grounding|>Given the layout of the image."
    
    payload = {
        "model": OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64_image]
            }
        ],
        "stream": False
    }

    try:
        response = requests.post(f"{OLLAMA_API_BASE}/chat", json=payload)
        if response.status_code == 200:
            data = response.json()
            # This output needs parsing to extract actual coordinates for cropping.
            return data.get("message", {}).get("content", "")
        else:
            print(f"[ERROR] Layout Analysis failed: {response.text}")
            return ""
    except requests.RequestException as e:
        print(f"[ERROR] Request to Ollama API failed: {e}")
        return ""

