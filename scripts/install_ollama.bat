@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo  AegisForge-AI: Ollama Windows Installer Helper
echo ======================================================================
echo Downloading official Ollama installer (~1.4 GB) ...
echo Please keep this window open while the download completes.
echo ======================================================================

set "SETUP_PATH=%TEMP%\OllamaSetup.exe"

:: Check if curl is available (built into modern Windows)
where curl.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Using Windows curl with progress indicator...
    curl.exe -L --progress-bar -o "%SETUP_PATH%" "https://ollama.com/download/OllamaSetup.exe"
) else (
    echo [INFO] Using PowerShell BITS transfer...
    powershell -Command "Start-BitsTransfer -Source 'https://ollama.com/download/OllamaSetup.exe' -Destination '%SETUP_PATH%'"
)

if exist "%SETUP_PATH%" (
    echo.
    echo ======================================================================
    echo [OK] Download complete! Launching Ollama installer...
    echo ======================================================================
    start "" "%SETUP_PATH%"
    echo Follow the on-screen prompts in the installer window to complete setup.
) else (
    echo.
    echo [ERROR] Direct download failed.
    echo Opening the official download page in your browser instead:
    start https://ollama.com/download/windows
)

endlocal
