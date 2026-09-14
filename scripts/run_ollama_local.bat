@echo off
setlocal enabledelayedexpansion

:: Resolve project root dynamically based on script directory
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

set "OLLAMA_MODELS=%PROJECT_ROOT%\model_pool\ollama"

echo ======================================================================
echo  AegisForge-AI: Isolated Ollama Server Launcher
echo ======================================================================
echo Project Root:       %PROJECT_ROOT%
echo Model Storage Dir:  %OLLAMA_MODELS%
echo ======================================================================

:: Ensure model directory exists
if not exist "%OLLAMA_MODELS%" (
    mkdir "%OLLAMA_MODELS%"
)

:: Check if ollama is in PATH
where ollama >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    :: Check typical Windows user install location
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
    ) else (
        echo [ERROR] Ollama was not found in PATH or at %LOCALAPPDATA%\Programs\Ollama.
        echo Please install Ollama from: https://ollama.com/download/windows
        pause
        exit /b 1
    )
)

echo [INFO] Starting Ollama with storage isolated in %OLLAMA_MODELS%...
echo Press Ctrl+C at any time to stop the server.
echo.

ollama serve

endlocal
