#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Rainette Universal Mouse - macOS setup"

PYTHON_CMD=""
for candidate in python3.11 python3.12; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_CMD="$candidate"
    break
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  echo "Python 3.11 or 3.12 is required."
  echo "Install one of those versions, then run this file again."
  read -r -p "Press Return to close..."
  exit 1
fi

if [ ! -d .venv ]; then
  "$PYTHON_CMD" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt

echo
echo "Setup complete. Double-click run_macos.command."
echo "It will build and launch the native app so permissions belong to the app instead of Terminal."
read -r -p "Press Return to close..."
