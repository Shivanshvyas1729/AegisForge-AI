@echo off
setlocal

echo ======================================================================
echo  AegisForge-AI: Ollama Windows Installer Helper
echo ======================================================================
echo Downloading official Ollama installer from https://ollama.com ...
echo.

set "SETUP_PATH=%TEMP%\OllamaSetup.exe"

powershell -Command "Write-Host 'Downloading OllamaSetup.exe...'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://ollama.com/download/OllamaSetup.exe', '%SETUP_PATH%')"

if exist "%SETUP_PATH%" (
    echo [OK] Download complete! Launching Ollama installer...
    start "" "%SETUP_PATH%"
    echo Please follow the on-screen installer prompts.
) else (
    echo [ERROR] Failed to download OllamaSetup.exe.
    echo Please download it manually from: https://ollama.com/download/windows
)

endlocal
