import requests
import base64
import os
import re

from src.config import (
    BACKEND, OCR_MODEL, REFINER_MODEL, OLLAMA_API_BASE, LLM_TIMEOUT, 
    REFINER_SYSTEM_PROMPT, OCR_TIMEOUT, VLLM_API_BASE, VLLM_MODEL, 
    VLLM_MAX_TOKENS, VLLM_TEMPERATURE
)

def _encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_markdown(image_path):
    """
    Extrae el texto de una imagen de página como Markdown usando DeepSeek-OCR.
    Usa el prompt exacto recomendado por la documentación oficial para máxima compatibilidad.
    """
    print(f"[INFO] Extrayendo texto de {os.path.basename(image_path)}...")
    base64_image = _encode_image(image_path)

    # Prompt crítico para DeepSeek-OCR — no modificar la sintaxis del prefijo <|grounding|>
    prompt = "<|grounding|>Convert the document to markdown."

    if BACKEND == "vllm":
        payload = {
            "model": VLLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": VLLM_TEMPERATURE,
            "max_tokens": VLLM_MAX_TOKENS
        }
        api_url = f"{VLLM_API_BASE}/chat/completions"
    else:
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
        api_url = f"{OLLAMA_API_BASE}/chat"

    try:
        response = requests.post(
            api_url,
            json=payload,
            timeout=OCR_TIMEOUT
        )
        if response.status_code == 200:
            if BACKEND == "vllm":
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                content = response.json().get("message", {}).get("content", "")
            # Limpiar etiquetas de coordenadas de DeepSeek (<|ref|>...<|/det|>)
            cleaned = re.sub(r'<\|ref\|>.*?<\|/ref\|><\|det\|>.*?<\|/det\|>\s*', '', content)
            return cleaned
        else:
            print(f"[ERROR] Fallo en extracción OCR: {response.text}")
            return ""
    except requests.Timeout:
        print(f"[ERROR] Timeout ({OCR_TIMEOUT}s) alcanzado al extraer texto de {os.path.basename(image_path)}.")
        return ""
    except requests.RequestException as e:
        api_name = "vLLM" if BACKEND == "vllm" else "Ollama"
        print(f"[ERROR] Error de conexión con {api_name} API: {e}")
        return ""

def analyze_layout(image_path):
    """
    Analiza el layout de la página para detectar regiones de imágenes o figuras.
    Usa el prompt de grounding de DeepSeek-OCR para obtener bounding boxes.
    """
    print(f"[INFO] Analizando layout de {os.path.basename(image_path)}...")
    base64_image = _encode_image(image_path)

    prompt = "<|grounding|>Given the layout of the image."

    if BACKEND == "vllm":
        payload = {
            "model": VLLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": VLLM_TEMPERATURE,
            "max_tokens": VLLM_MAX_TOKENS
        }
        api_url = f"{VLLM_API_BASE}/chat/completions"
    else:
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
        api_url = f"{OLLAMA_API_BASE}/chat"

    try:
        response = requests.post(
            api_url,
            json=payload,
            timeout=OCR_TIMEOUT
        )
        if response.status_code == 200:
            if BACKEND == "vllm":
                return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return response.json().get("message", {}).get("content", "")
        else:
            print(f"[ERROR] Fallo en análisis de layout: {response.text}")
            return ""
    except requests.Timeout:
        print(f"[ERROR] Timeout ({OCR_TIMEOUT}s) alcanzado al analizar layout de {os.path.basename(image_path)}.")
        return ""
    except requests.RequestException as e:
        api_name = "vLLM" if BACKEND == "vllm" else "Ollama"
        print(f"[ERROR] Error de conexión con {api_name} API: {e}")
        return ""

def refine_italics(markdown_text, page_num):
    """
    Usa el modelo de refinamiento (qwen2.5:14b) para identificar y marcar el texto
    que visualmente debería estar en cursiva según el contexto semántico.
    Por ejemplo: títulos de libros, palabras en latín, términos técnicos, énfasis editorial.
    
    Solo modifica el Markdown para añadir marcado de cursivas (*texto*) donde corresponda.
    No modifica el contenido del texto.
    """
    if not markdown_text.strip():
        return markdown_text

    print(f"[INFO] Refinando cursivas en página {page_num} con {REFINER_MODEL}...")

    system_prompt = REFINER_SYSTEM_PROMPT

    payload = {
        "model": REFINER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": markdown_text}
        ],
        "stream": False
    }

    try:
        response = requests.post(
            f"{OLLAMA_API_BASE}/chat",
            json=payload,
            timeout=LLM_TIMEOUT
        )
        if response.status_code == 200:
            refined = response.json().get("message", {}).get("content", "")
            if refined.strip():
                return refined
            else:
                print(f"[WARN] El refinador devolvió texto vacío en página {page_num}. Usando original.")
                return markdown_text
        else:
            print(f"[ERROR] Fallo en refinamiento de página {page_num}: {response.text}")
            return markdown_text
    except requests.Timeout:
        print(f"[WARN] Timeout ({LLM_TIMEOUT}s) alcanzado refinando página {page_num}. Usando texto original.")
        return markdown_text
    except requests.RequestException as e:
        print(f"[ERROR] Error de conexión durante refinamiento: {e}")
        return markdown_text
