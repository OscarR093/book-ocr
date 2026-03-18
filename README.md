# 📖 Book OCR — AI-Powered Scanned Book Processor

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python"/>
  <img src="https://img.shields.io/badge/Ollama-Local%20AI-black?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/DeepSeek--OCR-Vision%20LLM-purple?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/PyMuPDF-PDF%20Engine-orange?style=for-the-badge"/>
</p>

A local, **privacy-first** tool for extracting text from scanned PDF books using AI. It processes each page as an image, extracts Markdown-formatted text using **DeepSeek-OCR** via **Ollama**, detects and crops embedded images, and reassembles everything into a clean, formatted PDF.

No cloud APIs. No subscriptions. Runs entirely on your hardware.

---

## ✨ Features

- 🔍 **AI-powered OCR** via [DeepSeek-OCR](https://ollama.com/library/deepseek-ocr) running locally on Ollama
- 📄 **Markdown-aware output** — headings, bold, italics, and lists are preserved
- 🖼️ **Automatic image detection and cropping** from scanned pages
- 🧠 **Smart Ollama management** — auto-detects if Ollama is running, unloads current models, and loads the OCR model
- 📦 **Clean output structure** — organized folder per book, auto-cleanup of temporary files
- 📝 **PDF generation** using PyMuPDF with proper styling

---

## 🗂️ Project Structure

```
book-ocr/
├── main.py                  # Entry point — run this
├── requirements.txt
├── src/
│   ├── ollama_manager.py    # Ollama service & model management
│   ├── ocr_engine.py        # Text extraction and layout analysis via DeepSeek-OCR
│   ├── pdf_processor.py     # PDF → Image conversion (page by page)
│   ├── layout_engine.py     # Bounding box parsing and image cropping
│   └── converter.py         # Markdown → Formatted PDF via PyMuPDF Story
└── output/
    └── <book-name>/         # Temp files (auto-deleted after processing)
```

---

## ⚙️ Requirements

- [Ollama](https://ollama.com) (v0.13.0+)
- `deepseek-ocr` model pulled in Ollama:
  ```bash
  ollama pull deepseek-ocr
  ```
- [Conda](https://docs.conda.io/) for environment management
- Python 3.10+

---

## 🚀 Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/book-ocr.git
cd book-ocr
```

### 2. Create and activate the Conda environment

```bash
conda create -n book-ocr python=3.10 -y
conda activate book-ocr
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install markdown
```

### 4. Pull the OCR model

```bash
ollama pull deepseek-ocr
```

---

## 📖 Usage

Place your scanned PDF in the project root directory and run:

```bash
conda activate book-ocr
python3 main.py your_book.pdf
```

The script will:
1. ✅ Verify Ollama is running
2. 🔄 Unload any models currently in VRAM
3. 🚀 Load `deepseek-ocr` into memory
4. 🖼️ Convert each PDF page into a high-resolution image
5. 🧠 Run OCR on each page (text + layout analysis)
6. ✂️ Crop detected figures and images
7. 📝 Assemble a rich Markdown per page
8. 📄 Compile all pages into a final formatted PDF
9. 🧹 Clean up all temporary files automatically

**Output:** `output/<book-name>_final_ocr.pdf`

---

## 🔧 Configuration

To change the OCR model (if you want to try another vision LLM via Ollama), edit `src/ollama_manager.py`:

```python
OCR_MODEL = "deepseek-ocr"  # Change to any compatible Ollama vision model
```

---

## 📝 Notes

- **DeepSeek-OCR is prompt-sensitive.** The tool uses the exact prompts recommended in the [official documentation](https://ollama.com/library/deepseek-ocr), such as `<|grounding|>Convert the document to markdown.` for text and `<|grounding|>Given the layout of the image.` for structure analysis.
- Best results are achieved with PDFs scanned at 300 DPI or higher.
- Processing time varies depending on the number of pages and your GPU/CPU performance.

---

## 📄 License

MIT License. Feel free to fork, adapt, and contribute.
