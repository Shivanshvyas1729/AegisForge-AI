# How to Download All Models Needed with Ollama (Self-Contained in Project)

This guide provides step-by-step instructions and commands to download all required AI models directly into your project's **`model_pool/`** directory.

> **Zero Host Pollution Guarantee:** All model weights will be stored exclusively inside `SIH/model_pool/ollama/` and `SIH/model_pool/easyocr/`. Your Windows `C:\Users\<username>\` system folders remain completely untouched.

---

## 📋 Required Models Overview

| Model | Purpose | Storage Size | Backend | Target Location |
|---|---|---|---|---|
| **`deepseek-r1:1.5b`** | ASME Section VIII calculations & PSU Note for Approval reasoning | ~1.1 GB | Ollama | `model_pool/ollama/` |
| **`qwen2.5-coder:1.5b`** | SCADA, Modbus CRC-16, and industrial automation scripts | ~1.0 GB | Ollama | `model_pool/ollama/` |
| **`llama3.2:3b`** | Fast executive briefings and general refinery summaries | ~2.0 GB | Ollama | `model_pool/ollama/` |
| **`moondream`** | Multimodal VLM for reading P&ID tags and equipment symbols | ~1.7 GB | Ollama | `model_pool/ollama/` |
| **`EasyOCR`** | CRAFT + CRNN offline OCR engine for blueprints *(Already installed!)* | ~98 MB | PyTorch (CPU) | `model_pool/easyocr/` |

**Total Disk Space Required:** ~5.8 GB (Ensure $\ge 8\text{ GB}$ free on your drive).

---

## ⚙️ Step 1: Install Ollama (If Not Yet Installed)

The LLM/SLM models require the local Ollama runtime.

- **Option A (One-Click Installer):** Double-click [`scripts\install_ollama.bat`](scripts/install_ollama.bat)  
  *(This automatically downloads and runs the official `OllamaSetup.exe`)*
- **Option B (Manual Download):** Download and install from [ollama.com/download/windows](https://ollama.com/download/windows)

---

## 🚀 Step 2: Choose Your Download Method

Choose any of the **three methods** below to download the models:

### 🌟 Method A: Zero-Code Web Dashboard (Recommended)

1. Double-click [`run_app.bat`](run_app.bat) in the project root.
2. In the web dashboard that opens, go to the **"📦 Model Hub & One-Click Downloader"** tab.
3. If Ollama is not running, click **"▶️ Start Local Ollama"**.
4. Click the **"⬇️ Download"** button next to each model.
   - You will see a live streaming progress bar for each download.
   - All files will be saved directly into `model_pool/ollama/`.

---

### 🐍 Method B: Automated Python Script (All-in-One)

1. **Start the isolated local Ollama server** in Terminal 1:
   ```cmd
   scripts\run_ollama_local.bat
   ```
   *(Keep this terminal open)*

2. **Run the download script** in Terminal 2:
   ```powershell
   .venv\Scripts\python.exe scripts\setup_models.py
   ```
   *This script performs pre-flight disk space checks, verifies write permissions, and pulls all 4 models sequentially.*

---

### 💻 Method C: Manual Terminal Commands (PowerShell / CMD)

If you prefer to download models individually using the terminal:

#### 1. Set the model storage path to this project (Important!)
In PowerShell:
```powershell
$env:OLLAMA_MODELS = "$PWD\model_pool\ollama"
```
In Command Prompt (cmd.exe):
```cmd
set OLLAMA_MODELS=%CD%\model_pool\ollama
```

#### 2. Start the Ollama server:
```powershell
ollama serve
```

#### 3. In another terminal, pull the models one by one:
```powershell
# Set storage path in second terminal as well:
$env:OLLAMA_MODELS = "$PWD\model_pool\ollama"

# Pull Reasoning Model (P0 Priority for ASME MVP)
ollama pull deepseek-r1:1.5b

# Pull Industrial Coding Model
ollama pull qwen2.5-coder:1.5b

# Pull General Summarization Model
ollama pull llama3.2:3b

# Pull Vision-Language Model
ollama pull moondream
```

---

## 🧪 Step 3: Verify That Models Are Working

Run the test harnesses to confirm the models respond from your project folder:

### 1. Test DeepSeek-R1 Reasoning on ASME Section VIII:
```powershell
.venv\Scripts\python.exe models\reasoning_models\test_reasoning.py
```

### 2. Test the Sovereign Dynamic Router:
```powershell
.venv\Scripts\python.exe models\router\model_router.py
```

### 3. Test EasyOCR on Sample P&ID Blueprint:
```powershell
.venv\Scripts\python.exe models\vision_models\test_easyocr.py --image sample_data\05_scanned_drawings_pid\pump_station_isometric_drawing.png --cpu
```

---

## 🗑️ How to Uninstall / Free Disk Space

When you want to remove the downloaded models and reclaim your disk space (~5.8 GB):

- **Option 1 (Via Dashboard):** Click the **"🗑️ Remove"** button next to any model in the web UI.
- **Option 2 (Via Batch File):** Run [`scripts\clean_models.bat`](scripts/clean_models.bat)  
  *Deletes only the `.pth` files and Ollama blobs inside `model_pool/` while keeping all your code intact.*
- **Option 3 (Complete Project Reset):** Run [`scripts\uninstall_all.bat`](scripts/uninstall_all.bat)  
  *Wipes `.venv/` and `model_pool/` for a 100% clean teardown.*
