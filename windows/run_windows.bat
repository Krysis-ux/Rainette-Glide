@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
  call setup_windows.bat
  if errorlevel 1 exit /b 1
)
start "" /D "%~dp0" ".venv\Scripts\pythonw.exe" "%~dp0universal_mouse_windows.py"
