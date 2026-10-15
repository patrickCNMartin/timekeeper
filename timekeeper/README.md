# Timekeeper: developer guide

How the app is put together, how to run it from source, and how to build it on each
platform. For how to *use* the app, see the [main README](../README.md).

## Layout

| File | What it does |
|---|---|
| `app.py` | Tkinter window, saved settings, error messages. Only calls `run_report()`. |
| `report.py` | `run_report()`: runs the pipeline, writes the `.pptx` and `.csv`. Holds `BASE_URL` and `QUERY_DAYS`. |
| `timekeeper_utils.py` | iLab calls, date filtering, sorting requests into bins, CSV table, slide text (markdown). |
| `build_ppt.py` | Turns that markdown into slides: layout, colours (`THEME`), title slide. |
| `build_app.sh` | macOS build: installs what's missing, then builds `dist/Timekeeper.app`. |
| `Build Timekeeper.command` | Double-click wrapper around `build_app.sh` for Finder. |
| `pyproject.toml`, `uv.lock`, `.python-version` | uv project: dependencies and Python 3.13. |
| `../.github/workflows/build-app.yml` | GitHub Actions build for macOS and Windows. |

## How a report is built

`run_report(api_key, core_id, core_name, out_dir, days)` in `report.py`:

1. **Query a wide range.** iLab's date filter works on a creation date that the API
   doesn't return, not on `submitted_at`. So the query covers `max(QUERY_DAYS, days)`
   days (360 by default).
2. **Filter on `submitted_at`** to the last `days` days (`filter_by_submitted_date`).
3. **Fetch custom forms and milestones**, only for the requests that are left
   (`add_forms`). Each one costs two API calls.
4. **Sort into bins** (`sort_service_requests`). Each request goes into the first bin
   whose rule matches, checked in `RULES` order. Bin order in the outputs follows `BINS`.
5. **Write the CSV** (`format_response`): the base `FIELDS`, the bin as `type`, and
   empty `REPORT_METRICS` columns for people to fill in.
6. **Write the slides.** `convert_sr_to_md` writes markdown to a temp folder, and
   `convert_md_to_ppt` turns it into the `.pptx`.

Output names are `core_meeting_YYYY-MM-DD.pptx` and `.csv`. Running again on the same
day overwrites them.

The window runs `run_report` on a background thread. Its `print()` progress goes into
a queue through `contextlib.redirect_stdout`, and the main thread shows it in the log
box. Two consequences:
- Tk is only ever touched from the main thread.
- The stdout redirect applies to the whole process, so anything printed during a
  build ends up in the log box.

## Settings and secrets

- **API key:** stored in the OS credential store via
  [keyring](https://pypi.org/project/keyring/), under service `timekeeper` and user
  `ilab_api_key`. That's Keychain on macOS and Credential Manager on Windows. The app
  never writes the key to a file.
- **Everything else** (core name, core ID, folder, days) goes in `~/.timekeeper.json`.
- **Nothing core-specific is committed.** Core name and ID start blank.
- **Settings are saved when Build is clicked,** before the pull runs. A wrong key stays
  saved until it's corrected.

## Run from source (any platform)

1. **Install [uv](https://docs.astral.sh/uv/):**
   - **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. **From this folder:**
   ```sh
   uv sync
   uv run python app.py
   ```

`pyproject.toml` sets `python-preference = "only-managed"`. That makes uv always use
its own Python 3.13 build, which includes Tkinter (many system and Nix Pythons don't).
`uv sync` also installs PyInstaller, from the default `dev` group.

## Building the app

PyInstaller only builds for the OS and CPU it runs on. There's no cross-compiling, so
each platform needs its own build.

### macOS

```sh
./build_app.sh        # or double-click "Build Timekeeper.command" in Finder
```

The script:
1. Clears `UV_PYTHON` and `VIRTUAL_ENV`, so a shell setting can't swap in a Python
   without Tkinter.
2. Installs uv into `~/.local/bin` if it isn't found. This needs no admin rights,
   leaves shell profiles alone, and uses the version pinned in the script.
3. Opens Apple's Command Line Tools installer if `xcode-select -p` fails, and waits for
   it to finish. PyInstaller needs `install_name_tool` from those tools.
4. Runs `uv sync`, then `pyinstaller --windowed --name Timekeeper app.py`.
5. Zips the app with `ditto` into `dist/Timekeeper-mac.zip`. A plain `zip` would break
   the symlinks inside the `.app`.

Notes on the result:
- `dist/Timekeeper.app` is about 80 MB, and the zip about 40 MB.
- The app only runs on the CPU type it was built on (Apple Silicon or Intel).
- The app is ad-hoc signed, not notarized.
- An app built on the same Mac it runs on has no quarantine flag, so it opens without a
  Gatekeeper warning.

### Windows

Install uv (see above), then in PowerShell from this folder:

```powershell
uv sync
uv run pyinstaller --noconfirm --windowed --onefile --name Timekeeper app.py
```

That gives one self-contained `dist\Timekeeper.exe`. No extra system tools are needed.
`--onefile` makes it a single file to hand out, at the cost of a slower start (it
unpacks itself on each launch).

The Mac scripts (`build_app.sh`, `.command`) don't run on Windows.

### Linux

Not a target, and untested. Running from source should work on a desktop with a
Secret Service keyring (GNOME Keyring, KWallet). The build would be
`uv run pyinstaller --noconfirm --onefile --name Timekeeper app.py`.

### GitHub Actions

`.github/workflows/build-app.yml` builds both platforms on demand:
1. Go to **Actions → Build app → Run workflow**.
2. It runs `build_app.sh` on `macos-latest`, and the PyInstaller command above on
   `windows-latest`.
3. It uploads `Timekeeper-mac.zip` and `Timekeeper.exe` as run artifacts.

Artifacts need a GitHub login to download and expire after 90 days. To share builds
publicly, attach them to a GitHub Release.

## Distribution and signing

Builds aren't signed, so on another person's machine:
- **macOS:** Gatekeeper blocks the first launch. The user has to go to System
  Settings → Privacy & Security → **Open Anyway**. macOS 15 and later no longer offer
  right-click → Open for this.
- **Windows:** SmartScreen shows "Windows protected your PC". The user clicks
  **More info → Run anyway**. Antivirus tools occasionally flag `--onefile` PyInstaller
  builds.
- **macOS Keychain:** each new build asks once for permission to read the saved key.
  This happens because the app's ad-hoc signature changes with every build.

Removing these warnings needs:
- **macOS:** an Apple Developer ID ($99/year) plus notarization (`codesign`, then
  `notarytool`).
- **Windows:** a code-signing certificate.

## Adapting it to another core or iLab server

- **iLab server:** `BASE_URL` in `report.py` points at the EU server. Other endpoints,
  from the iLab API docs:

  | Region | `BASE_URL` |
  |---|---|
  | US (MY/General) | `https://api.ilabsolutions.com/v1/cores` |
  | EU | `https://api-eu.ilabsolutions.com/v1/cores` |
  | AU | `https://au-api.ilab.agilent.com/v1/cores` |
  | Stanford | `https://stanford-api.ilabsolutions.com/v1/cores` |

- **Finding a core ID:** this call lists every core a token can see.
  ```sh
  curl -s -H "Authorization: Bearer $ILAB_TOKEN" https://api-eu.ilabsolutions.com/v1/cores.json
  ```
- **Bins and service/form names:** these live in `timekeeper_utils.py` and are written
  for one proteomics core. Other cores need to edit:
  - `STARTUP_MEETING` and `SUPPLEMENTARY_SAMPLE` (service names)
  - the form names in `RULES`
  - `PREVIOUS_REQUEST_FIELD` and `NEW_SAMPLES_FIELD`
  - `RULES` and `BINS` themselves

  A request that matches no rule is left out of both outputs.
- **CSV columns:** `FIELDS` and `REPORT_METRICS`.
- **Slide bullets:** `BIN_BULLETS` and `BULLET_LABELS`.
- **Slide look:** `THEME` and `convert_md_to_ppt` in `build_ppt.py`.

## Gotchas

- **Rate limit:** 300 API requests per minute per token. Past that iLab returns 429,
  which the app shows as "try again in a minute". A long window with many requests can
  hit it, because each request costs two calls.
- **Token expiry:** tokens expire one year after they're created by default, and then
  the API returns 401. Core admins can extend the date under Administration → API
  Clients.
- **Encoding:** the markdown is written as UTF-8 explicitly, because Windows defaults to
  cp1252. The CSV is written as `utf-8-sig` so Excel shows accented names correctly.
- **Harmless PyInstaller warnings:** missing `jinja2` (optional pandas styling), and
  `user32`/`msvcrt` on macOS (Windows-only libraries).
- **Lint:** `uvx ruff check .` uses the ruff settings in `pyproject.toml`.
