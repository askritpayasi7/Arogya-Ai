@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo Starting RxScribe - Prescription Reader Dashboard
echo ===================================================

if not exist ".venv\Scripts\streamlit.exe" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\streamlit.exe
    echo Please create the virtual environment first:
    echo    python -m venv .venv
    echo    .\.venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] .env not found. Creating from .env.example...
        copy ".env.example" ".env" >nul
        echo [NOTICE] Please remember to verify your GEMINI_API_KEY in .env.
    )
)

echo Starting Streamlit app and opening in browser...
start http://localhost:8501
".venv\Scripts\streamlit.exe" run app.py --server.headless=false

pause
