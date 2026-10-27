# -----------------------------------------------------------------------------#
# IMPORT LIBS
# -----------------------------------------------------------------------------#
import contextlib
import json
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import keyring
import requests

from report import run_report

# -----------------------------------------------------------------------------#
# DEFINE GLOBAL VARS
# -----------------------------------------------------------------------------#
SETTINGS_PATH = Path.home() / ".timekeeper.json"

# The API key lives in the system keychain, not in the settings file
KEYRING_SERVICE = "timekeeper"
KEYRING_USER = "ilab_api_key"

DEFAULTS = {
    "core_name": "",
    "core_id": "",
    "out_dir": str(Path.home() / "Documents"),
    "days": "14",
    # Checkbox: "1" also saves the full iLab pull as json
    "save_json": "0",
}


# -----------------------------------------------------------------------------#
# SETTINGS
# -----------------------------------------------------------------------------#
def load_settings() -> dict:
    try:
        saved = json.loads(SETTINGS_PATH.read_text())
    except (OSError, ValueError):
        saved = {}
    try:
        api_key = keyring.get_password(KEYRING_SERVICE, KEYRING_USER) or ""
    except keyring.errors.KeyringError:
        api_key = ""
    return DEFAULTS | saved | {"api_key": api_key}


def save_settings(settings: dict):
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, settings["api_key"])
    SETTINGS_PATH.write_text(json.dumps({k: settings[k] for k in DEFAULTS}, indent=2))


def check_settings(settings: dict) -> str | None:
    """What the user needs to fix before we can build, if anything"""
    if not settings["api_key"]:
        return "Enter your iLab API key."
    if not settings["core_id"]:
        return "Enter your iLab core ID."
    if not settings["core_id"].isdigit():
        return "The core ID should be a number."
    if not Path(settings["out_dir"]).is_dir():
        return "Choose a folder to save to."
    if not settings["days"].isdigit() or int(settings["days"]) < 1:
        return "Days should be a whole number, 1 or more."
    return None


def explain(error: Exception) -> str:
    """User-facing message for an error raised while building"""
    if isinstance(error, requests.HTTPError):
        status = error.response.status_code
        if status in (401, 403):
            return "iLab rejected the API key (or the key can't see this core)."
        if status == 404:
            return "iLab doesn't know this core ID."
        return f"iLab returned an error ({status}). Try again in a minute."
    if isinstance(error, requests.ConnectionError):
        return "Can't reach iLab. Check your internet connection."
    if isinstance(error, PermissionError):
        return (
            f"Can't write {error.filename}.\n"
            "If it's open in PowerPoint or Excel, close it and try again."
        )
    return f"Something went wrong: {type(error).__name__}: {error}"


# -----------------------------------------------------------------------------#
# WINDOW
# -----------------------------------------------------------------------------#
class QueueWriter:
    """Stand-in for stdout: sends print() output to the window's log"""

    def __init__(self, messages: queue.Queue):
        self.messages = messages

    def write(self, text: str) -> int:
        self.messages.put(("log", text))
        return len(text)

    def flush(self):
        pass


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        # The build thread only talks to the window through this queue
        self.messages = queue.Queue()
        settings = load_settings()
        self.fields = {key: tk.StringVar(value=settings[key]) for key in settings}

        root.title("Timekeeper")
        frame = ttk.Frame(root, padding=16)
        frame.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        # (label, setting, entry options, stretch to full width)
        rows = [
            ("API key", "api_key", {"show": "•", "width": 44}, True),
            ("Core name", "core_name", {}, True),
            ("Core ID", "core_id", {"width": 10}, False),
            ("Save to", "out_dir", {}, True),
            ("Last (days)", "days", {"width": 6}, False),
        ]
        for row, (label, key, options, stretch) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            entry = ttk.Entry(frame, textvariable=self.fields[key], **options)
            entry.grid(row=row, column=1, sticky="ew" if stretch else "w", pady=3)
        ttk.Button(frame, text="Browse…", command=self.browse).grid(
            row=3, column=2, padx=(6, 0)
        )
        ttk.Checkbutton(
            frame,
            text="Also save the full iLab pull (.json)",
            variable=self.fields["save_json"],
            onvalue="1",
            offvalue="0",
        ).grid(row=5, column=1, sticky="w", pady=3)

        self.button = ttk.Button(frame, text="Build report", command=self.build)
        self.button.grid(row=6, column=0, columnspan=3, pady=(12, 8))

        self.log = tk.Text(frame, height=8, width=60, state="disabled", wrap="word")
        self.log.grid(row=7, column=0, columnspan=3, sticky="nsew")
        frame.rowconfigure(7, weight=1)

        self.poll()

    def browse(self):
        folder = filedialog.askdirectory(initialdir=self.fields["out_dir"].get())
        if folder:
            self.fields["out_dir"].set(folder)

    def build(self):
        settings = {key: var.get().strip() for key, var in self.fields.items()}
        problem = check_settings(settings)
        if problem:
            messagebox.showerror("Timekeeper", problem)
            return
        try:
            save_settings(settings)
        except Exception as error:
            # Not worth stopping the build over
            messagebox.showwarning("Timekeeper", f"Couldn't save your settings: {error}")

        self.button.config(state="disabled")
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        threading.Thread(target=self.work, args=(settings,), daemon=True).start()

    def work(self, settings: dict):
        """Runs on the build thread: never touches the window directly"""
        with contextlib.redirect_stdout(QueueWriter(self.messages)):
            try:
                saved = run_report(
                    settings["api_key"],
                    settings["core_id"],
                    settings["core_name"],
                    settings["out_dir"],
                    int(settings["days"]),
                    save_json=settings["save_json"] == "1",
                )
                names = ", ".join(path.name for path in saved)
                self.messages.put(("done", f"\nSaved {names}\nin {saved[0].parent}\n"))
            except Exception as error:
                self.messages.put(("error", explain(error)))

    def poll(self):
        """Move build thread messages into the window, every 100 ms"""
        while not self.messages.empty():
            kind, text = self.messages.get_nowait()
            self.log.config(state="normal")
            self.log.insert("end", text if kind != "error" else f"\n{text}\n")
            self.log.see("end")
            self.log.config(state="disabled")
            if kind in ("done", "error"):
                self.button.config(state="normal")
            if kind == "error":
                messagebox.showerror("Timekeeper", text)
        self.root.after(100, self.poll)


# -----------------------------------------------------------------------------#
# ENTRY
# -----------------------------------------------------------------------------#
if __name__ == "__main__":
    if sys.platform == "win32":
        # Sharp text on high-DPI screens
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = tk.Tk()
    App(root)
    root.mainloop()
