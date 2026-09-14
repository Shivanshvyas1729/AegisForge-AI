@echo off
cd /d "%~dp0"
echo ====================================================
echo Generating AegisForge-AI Native OpenXML Documents...
echo (.docx, .pptx, .xlsx)
echo ====================================================
python generate_sample_documents.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Documents generated in sample_data directories!
) else (
    echo.
    echo [ERROR] Document generation failed. Ensure Python 3 is installed.
)
echo.
pause
