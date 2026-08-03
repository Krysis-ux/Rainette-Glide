#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="RainetteUniversalMouse.app"
DEST_DIR="$HOME/Applications"
DEST_APP="$DEST_DIR/$APP_NAME"

show_error() {
  /usr/bin/osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with icon stop" >/dev/null 2>&1 || true
}

PYTHON_CMD=""
for candidate in python3.11 python3.12; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_CMD="$candidate"
    break
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  show_error "Python 3.11 or 3.12 is required. Install Python, then run this installer again."
  echo "Python 3.11 or 3.12 is required."
  exit 1
fi

if [ ! -d .venv ]; then
  "$PYTHON_CMD" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
python -m pip install --upgrade PyInstaller

rm -rf build dist
python -m PyInstaller --noconfirm --clean RainetteUniversalMouse_macos.spec

# Ad-hoc signing gives macOS a stable application identity for Camera and
# Accessibility permissions instead of attributing pointer access to Terminal.
/usr/bin/codesign --force --deep --sign - "dist/$APP_NAME"
mkdir -p "$DEST_DIR"
rm -rf "$DEST_APP"
/usr/bin/ditto "dist/$APP_NAME" "$DEST_APP"
/usr/bin/codesign --verify --deep --strict "$DEST_APP"

/usr/bin/open "$DEST_APP"
echo
echo "Installed and opened: $DEST_APP"
echo "Grant Camera and Accessibility access to RainetteUniversalMouse when asked."
