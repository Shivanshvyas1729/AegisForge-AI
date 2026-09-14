# AegisForge-AI: Project-Local Session Environment Activator
# Strictly modifies the CURRENT terminal session in-memory only.
# Leaves ZERO permanent changes to your Windows OS or User Registry.

$ProjectRoot = $PSScriptRoot

# 1. Activate Python virtual environment if it exists
if (Test-Path "$ProjectRoot\.venv\Scripts\Activate.ps1") {
    . "$ProjectRoot\.venv\Scripts\Activate.ps1"
}

# 2. Add local Ollama executable to this session's PATH (in-memory only)
$OllamaDir = "$env:LOCALAPPDATA\Programs\Ollama"
if (Test-Path "$OllamaDir\ollama.exe") {
    if ($env:PATH -notlike "*$OllamaDir*") {
        $env:PATH = "$OllamaDir;" + $env:PATH
    }
}

# 3. Lock Ollama models strictly to this project (in-memory only)
$env:OLLAMA_MODELS = "$ProjectRoot\model_pool\ollama"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " AegisForge-AI: Project Environment Active (Session-Only)" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " [+] Python:        $ProjectRoot\.venv\Scripts\python.exe"
Write-Host " [+] Ollama Binary: $OllamaDir\ollama.exe"
Write-Host " [+] Model Storage: $env:OLLAMA_MODELS"
Write-Host " [*] Note: Closing this terminal automatically reverts all settings." -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan
