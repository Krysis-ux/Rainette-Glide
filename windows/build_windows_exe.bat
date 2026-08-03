@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  call setup_windows.bat
  if errorlevel 1 exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --clean RainetteUniversalMouse_windows.spec
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo.
echo EXE created in dist\RainetteUniversalMouse\
pause
