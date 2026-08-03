#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  ./setup_macos.command
fi
source .venv/bin/activate
python -m pip install --upgrade PyInstaller
rm -rf build dist
python -m PyInstaller --noconfirm --clean RainetteUniversalMouse_macos.spec
codesign --force --deep --sign - dist/RainetteUniversalMouse.app
codesign --verify --deep --strict dist/RainetteUniversalMouse.app

echo
echo "Signed app created at dist/RainetteUniversalMouse.app"
echo "For normal installation, use install_macos_app.command."
read -r -p "Press Return to close..."
