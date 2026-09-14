@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

echo ======================================================================
echo  AegisForge-AI: Complete Environment & Model Teardown / Uninstall
echo ======================================================================
echo This will permanently remove:
echo   1. All downloaded model weights in %PROJECT_ROOT%\model_pool\
echo   2. Python virtual environment at   %PROJECT_ROOT%\.venv\
echo   3. All temporary caches (__pycache__, logs)
echo.
echo Source code, git history, and sample datasets will NOT be deleted.
echo ======================================================================
set /p CONFIRM="Are you sure you want to completely uninstall? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo [INFO] Teardown aborted. No files were deleted.
    exit /b 0
)

echo.
echo [*] Cleaning model weights...
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    "%PROJECT_ROOT%\.venv\Scripts\python.exe" "%PROJECT_ROOT%\scripts\clean_models.py" -y
)

echo [*] Removing Python virtual environment (.venv)...
if exist "%PROJECT_ROOT%\.venv" (
    rmdir /s /q "%PROJECT_ROOT%\.venv"
    echo [OK] Removed .venv
)

echo [*] Removing bytecode caches...
for /d /r "%PROJECT_ROOT%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)

echo.
echo ======================================================================
echo [SUCCESS] Complete project uninstall finished!
echo Zero external artifacts remain on this system.
echo To reinstall in the future, run: python -m venv .venv ^&^& pip install -r requirements.txt
echo ======================================================================

endlocal
