import requests
import time
import sys

from src.config import BACKEND, OCR_MODEL, REFINER_MODEL, OLLAMA_API_BASE, LLM_TIMEOUT

def check_ollama_running():
    """Verifica si el servicio de Ollama está accesible."""
    try:
        response = requests.get("http://localhost:11434/", timeout=2)
        if response.status_code == 200:
            print("[INFO] Ollama service is running.")
            return True
    except requests.ConnectionError:
        pass
    print("[ERROR] Ollama no está corriendo. Por favor, inicia el servicio de Ollama.")
    return False

def get_loaded_models():
    """Devuelve una lista con los nombres de los modelos actualmente cargados en VRAM."""
    try:
        response = requests.get(f"{OLLAMA_API_BASE}/ps", timeout=10)
        if response.status_code == 200:
            return [m.get("name") for m in response.json().get("models", []) if m.get("name")]
    except requests.RequestException as e:
        print(f"[WARN] No se pudo obtener los modelos activos: {e}")
    return []

def unload_model(model_name):
    """Descarga un modelo específico de la VRAM."""
    print(f"[INFO] Descargando modelo '{model_name}' de la VRAM...")
    try:
        payload = {"model": model_name, "keep_alive": 0}
        requests.post(f"{OLLAMA_API_BASE}/generate", json=payload, timeout=15)
        time.sleep(1)
    except requests.RequestException as e:
        print(f"[WARN] Error al descargar modelo '{model_name}': {e}")

def unload_all_models():
    """Descarga todos los modelos activos de la VRAM."""
    print("[INFO] Liberando VRAM de todos los modelos cargados...")
    loaded = get_loaded_models()
    for model_name in loaded:
        unload_model(model_name)
    if loaded:
        print("[INFO] VRAM liberada.")
    else:
        print("[INFO] No había modelos cargados.")

def is_model_loaded(model_name):
    """Comprueba si un modelo específico ya está cargado en VRAM."""
    return model_name in get_loaded_models()

def load_model(model_name):
    """
    Carga un modelo en la VRAM de Ollama usando keep_alive.
    Si ya está cargado, no lo recarga (ahorra tiempo).
    """
    if is_model_loaded(model_name):
        print(f"[INFO] El modelo '{model_name}' ya está cargado en VRAM.")
        return

    print(f"[INFO] Cargando modelo '{model_name}' en VRAM...")
    try:
        payload = {"model": model_name, "keep_alive": "2h"}
        response = requests.post(f"{OLLAMA_API_BASE}/generate", json=payload, timeout=30)
        if response.status_code == 200:
            print(f"[INFO] Modelo '{model_name}' cargado correctamente.")
        else:
            print(f"[ERROR] Fallo al cargar el modelo '{model_name}': {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] No se pudo comunicar con Ollama para cargar el modelo: {e}")
        sys.exit(1)

def prepare_ocr_phase():
    """Inicializa Ollama y carga el modelo de OCR para la fase 1."""
    if BACKEND == "vllm":
        print("[INFO] Usando vLLM backend. Saltando gestión de carga de modelos.")
        return
    if not check_ollama_running():
        sys.exit(1)
    unload_all_models()
    load_model(OCR_MODEL)

def switch_to_refiner_phase():
    """Descarga el modelo OCR y carga el modelo de refinamiento para la fase 2."""
    if BACKEND == "vllm":
        return
    print(f"\n[INFO] Cambiando de modelo: '{OCR_MODEL}' → '{REFINER_MODEL}'")
    unload_model(OCR_MODEL)
    time.sleep(2)  # pausa para asegurar liberación de VRAM
    load_model(REFINER_MODEL)

def finalize():
    """Descarga todos los modelos al finalizar el proceso."""
    if BACKEND == "vllm":
        return
    print("\n[INFO] Descargando todos los modelos de la VRAM (limpieza final)...")
    unload_all_models()

if __name__ == "__main__":
    prepare_ocr_phase()
