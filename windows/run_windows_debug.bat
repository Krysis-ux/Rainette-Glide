@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  call setup_windows.bat
  if errorlevel 1 exit /b 1
)
call .venv\Scripts\activate.bat
python universal_mouse_windows.py
echo.
echo Universal Mouse closed.
echo Log: %LOCALAPPDATA%\RainetteUniversalMouse\universal_mouse.log
pause
