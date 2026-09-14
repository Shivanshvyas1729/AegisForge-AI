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
if exist "%PROJECT_ROOT%\.venv\Scripts\streamlit.exe" (
    set "STREAMLIT_CMD="%PROJECT_ROOT%\.venv\Scripts\streamlit.exe""
) else if exist "C:\Users\rahul\anaconda3\envs\SIH\Scripts\streamlit.exe" (
    set "STREAMLIT_CMD="C:\Users\rahul\anaconda3\envs\SIH\Scripts\streamlit.exe""
) else (
    set "STREAMLIT_CMD=python -m streamlit"
)

echo [INFO] Launching AegisForge-AI Web Dashboard...
echo The app will open in your default browser automatically.
echo.

%STREAMLIT_CMD% run "%PROJECT_ROOT%\frontend\app.py" --server.port 8501 --server.headless false

endlocal
