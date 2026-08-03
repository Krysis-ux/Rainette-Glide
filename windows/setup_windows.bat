@echo off
setlocal
cd /d "%~dp0"
echo Rainette Universal Mouse - Windows setup
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if errorlevel 1 goto try_path_python

py -3.12 -c "import struct,sys; sys.exit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>nul
if errorlevel 1 goto try_py311
set "PYTHON_CMD=py -3.12"
goto found_python

:try_py311
py -3.11 -c "import struct,sys; sys.exit(0 if sys.version_info[:2] == (3, 11) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>nul
if errorlevel 1 goto try_py313
set "PYTHON_CMD=py -3.11"
goto found_python

:try_py313
py -3.13 -c "import struct,sys; sys.exit(0 if sys.version_info[:2] == (3, 13) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>nul
if errorlevel 1 goto try_path_python
set "PYTHON_CMD=py -3.13"
goto found_python

:try_path_python
where python >nul 2>nul
if errorlevel 1 goto no_python
python -c "import struct,sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 13) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>nul
if errorlevel 1 goto no_python
set "PYTHON_CMD=python"
goto found_python

:no_python
echo Python 3.11, 3.12, or 3.13 (64-bit) is required.
echo Download 64-bit Python from python.org and enable "Add Python to PATH".
pause
exit /b 1

:found_python
%PYTHON_CMD% -c "import struct,sys; sys.exit(0 if struct.calcsize('P') * 8 == 64 else 1)" >nul 2>nul
if errorlevel 1 (
  echo A 32-bit Python installation was found. MediaPipe requires 64-bit Python.
  echo Install 64-bit Python 3.11, 3.12, or 3.13 and run setup again.
  pause
  exit /b 1
)

if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -c "import struct,sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 13) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>nul
  if errorlevel 1 (
    echo Rebuilding an incompatible existing environment...
    rmdir /s /q .venv
  )
)

if not exist .venv\Scripts\python.exe (
  echo Creating private Python environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo Could not create the Python environment.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel setuptools
if errorlevel 1 goto install_failed
python -m pip install -r requirements.txt
if errorlevel 1 goto install_failed

python -c "import cv2, mediapipe, pyautogui, PIL, screeninfo; print('Dependencies verified successfully.')"
if errorlevel 1 goto install_failed

echo.
echo Setup complete. Double-click run_windows.bat.
pause
exit /b 0

:install_failed
echo.
echo Dependency installation failed.
echo Confirm that you are using 64-bit Python 3.11-3.13 and have an internet connection.
pause
exit /b 1
