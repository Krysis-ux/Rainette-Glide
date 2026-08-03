#!/bin/bash
set -e
cd "$(dirname "$0")"

APP="$HOME/Applications/RainetteUniversalMouse.app"
if [ -d "$APP" ]; then
  open "$APP"
  exit 0
fi

echo "The native app has not been installed yet."
echo "Building it now so Camera and Accessibility permissions belong to the app, not Terminal."
./install_macos_app.command
