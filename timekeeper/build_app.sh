#!/usr/bin/env bash
# Build dist/Timekeeper.app and a zip of it to share (macOS).
# Installs uv if it's missing (no admin rights needed); uv brings its own Python 3.13.
# Opens Apple's Command Line Tools installer if those are missing.
set -euo pipefail
cd "$(dirname "$0")"

# Always build with uv's own Python (it has Tkinter), whatever the shell points uv at
unset UV_PYTHON VIRTUAL_ENV

# uv goes in ~/.local/bin and we leave shell profiles alone, so always look there
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null; then
    echo "Installing uv into ~/.local/bin"
    curl -LsSf https://astral.sh/uv/install.sh \
        | env UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh
fi

# PyInstaller rewrites library paths with install_name_tool, which comes with
# Apple's Command Line Tools: open Apple's installer and wait for it if they're missing
if ! xcode-select -p >/dev/null 2>&1; then
    echo "Apple's Command Line Tools are needed: click Install in the window that opens."
    xcode-select --install || true
    echo "Waiting for the install to finish (close this window to cancel)"
    until xcode-select -p >/dev/null 2>&1; do sleep 10; done
fi

uv sync
uv run pyinstaller --noconfirm --windowed --name Timekeeper app.py
# ditto keeps the symlinks inside the .app intact (plain zip breaks them)
ditto -c -k --keepParent dist/Timekeeper.app dist/Timekeeper-mac.zip

echo "Built $(pwd)/dist/Timekeeper.app and dist/Timekeeper-mac.zip"
