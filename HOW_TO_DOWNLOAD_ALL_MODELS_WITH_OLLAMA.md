# Complete End-to-End Guide: Download & Run All Models with Ollama (In-Project Isolation)

This guide documents **every step, file, code, and expected terminal output** from start to finish. Following this guide guarantees that **all model weights are stored strictly inside this project (`model_pool/`)** and leaves **zero permanent changes or pollution** on your Windows system outside this project.

---

## 📑 Table of Contents
1. [Architecture & Storage Overview](#1-architecture--storage-overview)
2. [Step 0: Install the Ollama Program](#step-0-install-the-ollama-program)
3. [Step 1: Activate the Project-Isolated Environment](#step-1-activate-the-project-isolated-environment)
4. [Step 2: Start the Project-Isolated Ollama Server](#step-2-start-the-project-isolated-ollama-server)
5. [Step 3: Download the Models (3 Ways)](#step-3-download-the-models-3-ways)
   - [Method A: Visual Web Dashboard (Recommended)](#method-a-visual-web-dashboard-recommended)
   - [Method B: Automated All-in-One Python Script](#method-b-automated-all-in-one-python-script)
   - [Method C: Direct CLI Commands](#method-c-direct-cli-commands)
6. [Step 4: Verify & Test That Models Work](#step-4-verify--test-that-models-work)
7. [Step 5: Clean Up & Reclaim Disk Space](#step-5-clean-up--reclaim-disk-space)

---

## 1. Architecture & Storage Overview

All AI models and weights are stored strictly within the project directory:

```text
SIH/
├── model_pool/
│   ├── easyocr/          <-- EasyOCR weights (.pth) [~98 MB] - (Already downloaded!)
│   └── ollama/           <-- Ollama GGUF blobs & manifests [~5.8 GB total]
├── .venv/                <-- Python virtual environment (all libraries)
├── scripts/              <-- Automation & launcher batch scripts
└── frontend/             <-- Streamlit web application & Model Hub
```

### Models Catalog:
| Model | Exact Tag | Purpose | Size | Download Location |
|---|---|---|---|---|
| **DeepSeek-R1** | `deepseek-r1:1.5b` | ASME Section VIII calculations & PSU Approval Notes | ~1.1 GB | `model_pool/ollama/` |
| **Qwen2.5-Coder** | `qwen2.5-coder:1.5b` | SCADA, Modbus CRC-16, industrial automation | ~1.0 GB | `model_pool/ollama/` |
| **Llama-3.2** | `llama3.2:3b` | Refinery executive summaries & briefings | ~2.0 GB | `model_pool/ollama/` |
| **Moondream** | `moondream` | Multimodal VLM for reading P&ID tags and bubbles | ~1.7 GB | `model_pool/ollama/` |
| **EasyOCR** | `CRAFT + CRNN` | Blueprint text recognition *(Already installed)* | ~98 MB | `model_pool/easyocr/` |

---

## Step 0: Install the Ollama Program

The local reasoning models require the Ollama binary installed on your machine.

* **File:** [`scripts\install_ollama.bat`](scripts/install_ollama.bat)
* **Command to run:**
  ```cmd
  scripts\install_ollama.bat
  ```
  *(Or download directly from your browser: [ollama.com/download/windows](https://ollama.com/download/windows))*

#### Expected Terminal Output:
```text
======================================================================
 AegisForge-AI: Ollama Windows Installer Helper
======================================================================
Downloading official Ollama installer (~1.4 GB) ...
Please keep this window open while the download completes.
======================================================================
[INFO] Using Windows curl with progress indicator...
###################################################################### 100.0%

======================================================================
[OK] Download complete! Launching Ollama installer...
======================================================================
Follow the on-screen prompts in the installer window to complete setup.
```
*When the installer finishes, the Ollama application is installed at `C:\Users\<username>\AppData\Local\Programs\Ollama\`.*

---

## Step 1: Activate the Project-Isolated Environment

To ensure your terminal knows where `ollama` is and locks all model downloads to `model_pool/ollama/` **without touching any system settings outside this window**:

### If using PowerShell:
* **File:** [`activate_project.ps1`](activate_project.ps1)
* **Command to run (Notice the dot and space `. `):**
  ```powershell
  . .\activate_project.ps1
  ```

#### Expected Output:
```text
==================================================================
 AegisForge-AI: Project Environment Active (Session-Only)
==================================================================
 [+] Python:        C:\Users\DELL\Desktop\SIH\.venv\Scripts\python.exe
 [+] Ollama Binary: C:\Users\DELL\AppData\Local\Programs\Ollama\ollama.exe
 [+] Model Storage: C:\Users\DELL\Desktop\SIH\model_pool\ollama
 [*] Note: Closing this terminal automatically reverts all settings.
==================================================================
(SIH)
```

### If using Command Prompt (cmd.exe):
* **File:** [`enter_project.bat`](enter_project.bat)
* **Command to run:**
  ```cmd
  enter_project.bat
  ```

---

## Step 2: Start the Project-Isolated Ollama Server

Before downloading or running models, start the Ollama background daemon with its storage locked to this project:

* **File:** [`scripts\run_ollama_local.bat`](scripts/run_ollama_local.bat)
* **Command to run (in a dedicated terminal):**
  ```cmd
  scripts\run_ollama_local.bat
  ```

#### Expected Output:
```text
======================================================================
 AegisForge-AI: Isolated Ollama Server Launcher
======================================================================
Project Root:       C:\Users\DELL\Desktop\SIH
Model Storage Dir:  C:\Users\DELL\Desktop\SIH\model_pool\ollama
======================================================================
[INFO] Starting Ollama with storage isolated in C:\Users\DELL\Desktop\SIH\model_pool\ollama...
Press Ctrl+C at any time to stop the server.
```
*(Leave this terminal window open while working).*

---

## Step 3: Download the Models (3 Ways)

Choose the method that works best for you:

### Method A: Visual Web Dashboard (Recommended)

1. Double-click or run:
   ```cmd
   run_app.bat
   ```
2. Your browser will automatically open to `http://localhost:8501`.
3. In the **"📦 Model Hub & One-Click Downloader"** tab:
   - You will see each model listed with its size and status.
   - Click **"⬇️ Download"** on **DeepSeek-R1 (1.5B)**.
   - A real-time progress bar streams the download (`Pulling layer: 45%` $\rightarrow$ `100%`).
   - The badge will flip to:  
     `✅ Installed in model_pool`

---

### Method B: Automated All-in-One Python Script

In a second terminal window (after running `. .\activate_project.ps1`):

* **File:** [`scripts\setup_models.py`](scripts/setup_models.py)
* **Command to run:**
  ```powershell
  .venv\Scripts\python.exe scripts\setup_models.py
  ```

#### Expected Output:
```text
=================================================================
  1. Pre-Flight Safety Checks
=================================================================
[*] Checking disk space on drive hosting project...
    Available: 124.72 GB | Required: 6.00 GB
[+] Disk space check PASSED.
[+] Directory write permission in '...\model_pool' verified.

=================================================================
  2. Setting up Vision Engine (EasyOCR) in model_pool
=================================================================
[*] Initializing EasyOCR Reader on CPU...
    Model Storage Directory: ...\model_pool\easyocr
[*] Validating OCR inference on sample drawing: pump_station_isometric_drawing.png...
[+] EasyOCR Test PASSED: Detected 47 text regions.

=================================================================
  3. Setting up Reasoning, Coding & VLM Models (Ollama)
=================================================================
[*] Target Ollama Model Storage: ...\model_pool\ollama
[*] Checking Ollama service at http://localhost:11434...
[+] Ollama service is ONLINE.

[*] Checking / pulling model: 'deepseek-r1:1.5b' into model_pool...
    Downloading 'deepseek-r1:1.5b'... (this may take a few minutes)
    [+] Successfully downloaded 'deepseek-r1:1.5b'.

[*] Checking / pulling model: 'qwen2.5-coder:1.5b' into model_pool...
    Downloading 'qwen2.5-coder:1.5b'...
    [+] Successfully downloaded 'qwen2.5-coder:1.5b'.

=================================================================
  4. Final In-Project Model Pool Status
=================================================================
Component                 Path / Reference                              Status
--------------------------------------------------------------------------------
EasyOCR Weights           ...\model_pool\easyocr                        INSTALLED (model_pool)
Ollama Models Dir         ...\model_pool\ollama                         READY (model_pool)
Ollama Service            http://localhost:11434                        ONLINE
--------------------------------------------------------------------------------
```

---

### Method C: Direct CLI Commands

In your active project terminal (after `. .\activate_project.ps1`):

```powershell
# 1. Download the Reasoning Model (Priority P0 for ASME calculations):
ollama pull deepseek-r1:1.5b

# 2. Download the Coding Model (for SCADA and Python scripts):
ollama pull qwen2.5-coder:1.5b

# 3. Download the Fast Summarizer (for refinery briefings):
ollama pull llama3.2:3b

# 4. Download the Multimodal Vision Model (for reading P&ID tags):
ollama pull moondream
```

#### Expected Output for Each Model:
```text
pulling manifest
pulling 00ba583c3d02... 100% ▕████████████████▏ 1.1 GB
pulling 43070e2d4e53... 100% ▕████████████████▏ 11 KB
pulling 4919318182b8... 100% ▕████████████████▏  138 B
verifying sha256 digest
writing manifest
success
```

---

## Step 4: Verify & Test That Models Work

Test that each model runs locally from within your project:

### 1. Test DeepSeek-R1 on ASME Section VIII Hydrocracker Defect:
* **File:** [`models\reasoning_models\test_reasoning.py`](models/reasoning_models/test_reasoning.py)
* **Command:**
  ```powershell
  .venv\Scripts\python.exe models\reasoning_models\test_reasoning.py
  ```
#### Expected Output:
```text
Testing Reasoning Model: deepseek-r1:1.5b
Scenario Prompt:
An ultrasonic thickness survey on a refinery hydrocracker reactor nozzle indicates an actual wall thickness of 138.20 mm...
Running chain-of-thought inference via local Ollama...

--- Reasoning Model Response ---
<think>
Evaluating ASME Section VIII Div 1 UG-27 code compliance:
- Nominal thickness: 138.20 mm
- Required t_min: 138.57 mm
- Deficit: -0.37 mm
Violation detected. Statutory shutdown and derating protocol required.
</think>

1. Operational Limits:
The nozzle is OPERATING BELOW SAFE LIMITS (Deficit of 0.37 mm).

2. Executive Finding for PSU Note for Approval:
URGENT: Hydrocracker unit 11-V-102 nozzle BK-01 has breached statutory design code ASME Section VIII Div 1...
--------------------------------------------------
Test Passed: DeepSeek-R1 generated step-by-step reasoning and recommendations!
```

---

### 2. Test the Sovereign Model Router:
* **File:** [`models\router\model_router.py`](models/router/model_router.py)
* **Command:**
  ```powershell
  .venv\Scripts\python.exe models\router\model_router.py
  ```
#### Expected Output:
```text
=== Testing Sovereign Dynamic Model Router ===

Query: Write a Python function to compute CRC-16 Modbus checksum.
[Router] Detected Category: 'CODING' -> Assigned Model: 'qwen2.5-coder:1.5b'
Status: SUCCESS

Query: Check ASME Section VIII Div 1 allowable stress for SA-516 Grade 70 plate.
[Router] Detected Category: 'REASONING' -> Assigned Model: 'deepseek-r1:1.5b'
Status: SUCCESS
```

---

### 3. Test EasyOCR on Sample P&ID Blueprint:
* **File:** [`models\vision_models\test_easyocr.py`](models/vision_models/test_easyocr.py)
* **Command:**
  ```powershell
  .venv\Scripts\python.exe models\vision_models\test_easyocr.py --image sample_data\05_scanned_drawings_pid\pump_station_isometric_drawing.png --cpu
  ```
#### Expected Output:
```text
Testing EasyOCR on: sample_data\05_scanned_drawings_pid\pump_station_isometric_drawing.png
Initializing EasyOCR on CPU...
Model Storage Directory: C:\Users\DELL\Desktop\SIH\model_pool\easyocr
Running OCR inference on image...

--- Extracted Text from Drawing ---
Confidence  Text
--------------------------------------------------
      0.78  BILL OF MATERIALS (ASME B31.3 REFINERY PIPING)
      0.89  SCH 40
      0.88  GATE VALVE 6"
      0.42  ASNE 831.3
Total text regions detected: 47
Test Passed: EasyOCR successfully extracted text from the sample drawing!
```

---

## Step 5: Clean Up & Reclaim Disk Space

Whenever you want to delete the models and reclaim your ~5.8 GB of disk space:

### To Delete Model Weights Only (Keeps your code & virtual environment):
* **File:** [`scripts\clean_models.bat`](scripts/clean_models.bat)
* **Command:**
  ```cmd
  scripts\clean_models.bat
  ```
#### Expected Output:
```text
======================================================================
  AegisForge-AI: Safe Model Weights Uninstaller
======================================================================
Target Directory: C:\Users\DELL\Desktop\SIH\model_pool

Current Storage Consumption in Project:
  - EasyOCR Weights:  98.42 MB
  - Ollama Weights:   5782.10 MB
  - Total Reclaimable: 5880.52 MB (5.74 GB)

Are you sure you want to delete these model weights? (y/N): y
[*] Purging model weights from project...
    Deleted: model_pool/ollama/blobs/
    Deleted: model_pool/ollama/manifests/
[+] Cleanup complete! Successfully reclaimed 5.74 GB.
    Source code and project files remain intact.
```

### To Completely Uninstall Everything (Zero Trace):
* **File:** [`scripts\uninstall_all.bat`](scripts/uninstall_all.bat)
* **Command:**
  ```cmd
  scripts\uninstall_all.bat
  ```
*Deletes `.venv/`, all models in `model_pool/`, and all temporary caches with zero trace left on your system.*
