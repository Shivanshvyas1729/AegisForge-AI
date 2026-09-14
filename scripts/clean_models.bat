@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

echo ======================================================================
echo  AegisForge-AI: Clean Model Weights (.pth and Ollama blobs)
echo ======================================================================

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    "%PROJECT_ROOT%\.venv\Scripts\python.exe" "%PROJECT_ROOT%\scripts\clean_models.py" %*
) else (
    python "%PROJECT_ROOT%\scripts\clean_models.py" %*
)

endlocal
