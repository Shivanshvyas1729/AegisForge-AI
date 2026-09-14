@echo off
setlocal

:: Resolve project root dynamically based on script directory
set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "OLLAMA_MODELS=%PROJECT_ROOT%\model_pool\ollama"
set "EASYOCR_MODULE_PATH=%PROJECT_ROOT%\model_pool\easyocr"

echo ======================================================================
echo  AegisForge-AI: Sovereign Air-Gapped Workbench Launcher
echo ======================================================================
echo Project Root:       %PROJECT_ROOT%
echo Model Storage:      %OLLAMA_MODELS%
echo ======================================================================

:: Python executable check
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "STREAMLIT_EXE=%PROJECT_ROOT%\.venv\Scripts\streamlit.exe"

if not exist "%STREAMLIT_EXE%" (
    echo [ERROR] Streamlit executable not found at %STREAMLIT_EXE%
    echo Please make sure dependencies are installed in .venv
    pause
    exit /b 1
)

echo [INFO] Launching AegisForge-AI Web Dashboard...
echo The app will open in your default browser automatically.
echo.

"%STREAMLIT_EXE%" run "%PROJECT_ROOT%\frontend\app.py" --server.port 8501 --server.headless false

endlocal
