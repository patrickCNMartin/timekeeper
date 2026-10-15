#!/usr/bin/env bash
# Build dist/Timekeeper.app and a zip of it to share (macOS).
# Installs uv if it's missing (no admin rights needed); uv brings its own Python 3.13.
set -euo pipefail
cd "$(dirname "$0")"

# Always build with uv's own Python (it has Tkinter), whatever the shell points uv at
unset UV_PYTHON VIRTUAL_ENV

# uv goes in ~/.local/bin and we leave shell profiles alone, so always look there
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null; then
    echo "Installing uv into ~/.local/bin"
    curl -LsSf https://astral.sh/uv/0.12.17/install.sh \
        | env UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh
fi

uv sync
uv run pyinstaller --noconfirm --windowed --name Timekeeper app.py
# ditto keeps the symlinks inside the .app intact (plain zip breaks them)
ditto -c -k --keepParent dist/Timekeeper.app dist/Timekeeper-mac.zip

echo "Built $(pwd)/dist/Timekeeper.app and dist/Timekeeper-mac.zip"
