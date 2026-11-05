@echo off
setlocal
title Health App - Research Paper and FSSAI Advisory Launcher
cd /d "%~dp0"

echo ======================================================================
echo   Launching Health App Terminal Menu...
echo ======================================================================

:: Attempt to use Python 3.13 if specifically installed at standard location
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" -m health_app.menu
    goto done
)

:: Otherwise fallback to default system python
python -m health_app.menu

:done
if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Program exited with error code %ERRORLEVEL%.
    pause
)
endlocal
