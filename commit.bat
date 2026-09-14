@echo off
cd /d "%~dp0"
echo ====================================================
echo Staging and committing changes for AegisForge-AI...
echo ====================================================
echo.

REM Stage all files respecting .gitignore
git add -A

REM Display status
echo Git Status:
echo ----------------------------------------------------
git status --short
echo ----------------------------------------------------
echo.

REM Create commit
git commit -m "feat(samples): add domain-curated industrial benchmark datasets across 6 categories"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================
    echo [SUCCESS] Changes committed successfully!
    echo ====================================================
    echo.
    echo To push your commit to GitHub:
    echo   git push origin main
) else (
    echo.
    echo [!] Nothing to commit or commit failed. Check git status above.
)

pause
