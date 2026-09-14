@echo off
set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

if exist "%PROJECT_ROOT%\.venv\Scripts\activate.bat" (
    call "%PROJECT_ROOT%\.venv\Scripts\activate.bat"
)

if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
)

set "OLLAMA_MODELS=%PROJECT_ROOT%\model_pool\ollama"

echo ==================================================================
echo  AegisForge-AI: Project Environment Active (Session-Only)
echo ==================================================================
echo  [+] Python:        %PROJECT_ROOT%\.venv\Scripts\python.exe
echo  [+] Ollama Path:   %LOCALAPPDATA%\Programs\Ollama
echo  [+] Model Storage: %OLLAMA_MODELS%
echo  [*] Note: All settings are temporary for this window only.
echo ==================================================================
cmd /k
