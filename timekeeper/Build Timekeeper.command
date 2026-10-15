#!/bin/bash
# Double-click this in Finder to build Timekeeper.app (it runs in a Terminal window)
cd "$(dirname "$0")"
if ./build_app.sh; then
    # Show the new app in Finder
    open -R dist/Timekeeper.app
    echo -e "\nDone. You can close this window."
else
    echo -e "\nThe build failed. The messages above say why."
fi
