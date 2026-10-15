# Timekeeper

A small window that pulls the last N days of service requests from iLab and saves
the core meeting slides (`.pptx`) and summary table (`.csv`).

Enter the API key, check the core name/ID, pick a folder and press **Build report**.
Everything is remembered for next time: the API key in the system keychain
(macOS Keychain / Windows Credential Manager), the rest in `~/.timekeeper.json`.

Files are saved as `core_meeting_YYYY-MM-DD.pptx` and `.csv`; running it again on the
same day overwrites them.

## Build the app

**macOS:** double-click **Build Timekeeper.command** in Finder (or run `./build_app.sh`
in Terminal). About a minute later Finder shows `dist/Timekeeper.app`, plus
`dist/Timekeeper-mac.zip` to share.

Nothing needs installing first and no admin password is asked for: if
[uv](https://docs.astral.sh/uv/) is missing, the script installs it into `~/.local/bin`
(shell profiles are left alone), and uv downloads its own Python 3.13, which includes
Tkinter.

The app runs on the same kind of Mac it was built on (Apple Silicon or Intel). An app you
build on your own Mac also opens without the first-launch warning below.

If the repo was downloaded as a zip from the browser, macOS may block the `.command` file
too: right-click it → **Open**.

**Windows:** run the **Build app** workflow from the repo's Actions tab and download
`Timekeeper.exe` from the run page. (It also builds the Mac zip.)

## Run from source

```sh
uv sync
uv run python app.py
```

## First launch on a colleague's machine

The app isn't signed, so the first launch shows a warning:

- **macOS:** double-click, close the warning, then System Settings → Privacy & Security →
  **Open Anyway**. After each new version macOS also asks to use the keychain: click
  **Always Allow**.
- **Windows:** "Windows protected your PC" → **More info** → **Run anyway**.
