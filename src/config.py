# ═══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN CENTRAL — book-ocr
#  Aquí se definen todos los parámetros ajustables del pipeline.
#  Edita este archivo para personalizar el comportamiento sin
#  tocar la lógica de los demás módulos.
# ═══════════════════════════════════════════════════════════════

# ───────────────────────────────────────────
# MODELOS DE OLLAMA
# ───────────────────────────────────────────

# Modelo multimodal usado para la extracción de texto (Fase 1).
# ADVERTENCIA: el prompt de OCR está ajustado a la sintaxis de DeepSeek-OCR;
# cambiar este modelo puede requerir ajustar los prompts en ocr_engine.py.
OCR_MODEL = "deepseek-ocr"

# Modelo de lenguaje usado para el refinamiento tipográfico (Fase 2).
REFINER_MODEL = "qwen2.5:14b"

# ───────────────────────────────────────────
# API DE OLLAMA
# ───────────────────────────────────────────

OLLAMA_API_BASE = "http://localhost:11434/api"

# Tiempo máximo (en segundos) de espera para cada llamada a la API.
LLM_TIMEOUT = 180  # 3 minutos

# ───────────────────────────────────────────
# TIPOGRAFÍA DEL PDF GENERADO
# ───────────────────────────────────────────

# Fuentes usadas en el CSS del PDF. Deben estar disponibles en el sistema
# o ser nombres genéricos de CSS (serif, sans-serif, monospace).
# "Georgia" ofrece un aspecto formal y legible para textos de libros.
PDF_FONT_NORMAL = "Georgia, 'Times New Roman', serif"
PDF_FONT_BOLD   = "Georgia, 'Times New Roman', serif"
PDF_FONT_ITALIC = "Georgia, 'Times New Roman', serif"

# ───────────────────────────────────────────
# PROMPT DEL REFINADOR (Fase 2 — Qwen)
# ───────────────────────────────────────────
# Este prompt puede ajustarse con libertad; solo el prompt del OCR (en
# ocr_engine.py) debe permanecer inalterado por sensibilidad del modelo.

REFINER_SYSTEM_PROMPT = (
    "You are a Markdown formatting specialist. Your only task is to identify words or phrases "
    "in the provided text that are likely to be in italic print in the original scanned book "
    "and wrap them with single *asterisks* in Markdown format. "
    "These typically include: book titles, words in foreign languages (Latin, French, etc.), "
    "technical terms being introduced, editorial emphasis, and any text enclosed in quotation marks "
    "(both straight quotes \" and curly quotes \u201c\u201d). Text in quotes should be italicized AND "
    "keep the surrounding quotation marks. "
    "Do NOT translate, rephrase, or add any content. Return ONLY the modified Markdown text."
)
