import subprocess
import requests
import time
import sys
import json

OCR_MODEL = "deepseek-ocr"
OLLAMA_API_BASE = "http://localhost:11434/api"

def check_ollama_running():
    """Verify if Ollama service is reachable."""
    try:
        response = requests.get(f"http://localhost:11434/", timeout=2)
        if response.status_code == 200:
            print("[INFO] Ollama service is running.")
            return True
    except requests.ConnectionError:
        pass
    print("[ERROR] Ollama is not running. Please start the Ollama service.")
    return False

def unload_current_models():
    """Unload all currently active models from memory."""
    print("[INFO] Checking currently loaded models to free VRAM...")
    try:
        response = requests.get(f"{OLLAMA_API_BASE}/ps")
        if response.status_code == 200:
            models = response.json().get("models", [])
            for model in models:
                model_name = model.get("name")
                if model_name:
                    print(f"[INFO] Unloading model {model_name}...")
                    # Unload model by asking to keep it alive for 0 seconds
                    unload_payload = {"model": model_name, "keep_alive": 0}
                    requests.post(f"{OLLAMA_API_BASE}/generate", json=unload_payload)
            print("[INFO] VRAM should be freed.")
            time.sleep(1) # Give it a moment to unload completely
        else:
            print(f"[WARN] Failed to fetch running models: {response.text}")
    except requests.RequestException as e:
        print(f"[WARN] Error fetching running models: {e}")

def load_ocr_model():
    """Ensure the target OCR model is downloaded and loaded."""
    if not check_ollama_running():
        sys.exit(1)
        
    unload_current_models()
    
    print(f"[INFO] Ensuring model '{OCR_MODEL}' is ready (this may take a moment if it's not downloaded)...")
    # First check if we have it locally, otherwise pull it could be slow but we can just use generate call
    # which automatically pulls if missing (in recent versions of Ollama). Or we can trigger a pre-flight generate.
    
    # Pre-warm the model
    try:
        payload = {
            "model": OCR_MODEL,
            "keep_alive": "1h" # keep alive for 1 hour to avoid reload
        }
        # The first request will load the model into VRAM
        response = requests.post(f"{OLLAMA_API_BASE}/generate", json=payload)
        if response.status_code == 200:
            print(f"[INFO] Successfully loaded model '{OCR_MODEL}' into VRAM.")
        else:
            print(f"[ERROR] Failed to load model '{OCR_MODEL}': {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Could not communicate with Ollama to load model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    load_ocr_model()
