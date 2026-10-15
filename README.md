# Timekeeper

A small Mac and Windows app for core meetings. It pulls your core's recent service
requests from iLab and saves:

- **a PowerPoint deck:** a title slide, then one slide per request, grouped by status
  (drafts, start-up meetings, supplementary samples, processing, completed, cancelled);
- **a CSV table:** one row per request, with empty columns ready for the meeting's
  numbers.

Building, changing or adapting the app? See the
**[developer guide](timekeeper/README.md)**.

## What you need

- **An iLab API token for your core.** A core administrator creates it in iLab under
  **Administration → API Clients**. That section only appears if your institution has
  API access turned on. Tokens expire after one year unless the administrator extends
  them.
- **Your core's iLab ID**, a number. Ask the person who gave you the token.
- **A Mac or a Windows PC.**

The app talks to iLab's **EU server**. If your institution uses another iLab server
(US, Australia, Stanford), a developer has to change one setting first. The
[developer guide](timekeeper/README.md#adapting-it-to-another-core-or-ilab-server)
explains how.

## Getting the app

### Mac: build it yourself (a few minutes)

1. On this repository's GitHub page, click **Code → Download ZIP**, then double-click
   the zip to unzip it.
2. Open the `timekeeper` folder and double-click **Build Timekeeper.command**.
   - If macOS says it can't verify the file, open **System Settings → Privacy &
     Security**, scroll down, click **Open Anyway**, then double-click it again.
3. A Terminal window shows the progress.
   - The first time, if your Mac doesn't have Apple's Command Line Tools, macOS asks to
     install them. Click **Install**; the build carries on once they're in. That
     download can add 10 minutes or more.
   - Nothing else needs installing, and you won't be asked for your password.
4. When it's done, a Finder window opens with **Timekeeper.app** selected. Drag it to
   your Applications folder.

An app you build on your own Mac opens straight away, with no security warning.

### Mac or Windows: get a ready-made copy

Ask whoever maintains Timekeeper at your core for `Timekeeper-mac.zip` (Mac) or
`Timekeeper.exe` (Windows). Because the app isn't signed, the first launch shows a
warning:

- **Mac:** unzip, double-click **Timekeeper.app**, and close the warning. Then open
  **System Settings → Privacy & Security** and click **Open Anyway**.
- **Windows:** at "Windows protected your PC", click **More info → Run anyway**.

You only have to do this once.

## Using it

Fill in the window, then click **Build report**.

| Field | What to enter |
|---|---|
| **API key** | Your iLab API token. It's stored in your Mac's Keychain or Windows Credential Manager, never in a file. |
| **Core name** | Optional. Shown on the title slide. |
| **Core ID** | Your core's iLab ID (a number). |
| **Save to** | The folder for the files. Click **Browse…** to choose one. |
| **Last (days)** | Include requests submitted in this many days, counting back from today. |

The box at the bottom shows progress. Most runs take under a minute, but more requests
take longer. When it's done you'll find two files in your folder:

- `core_meeting_YYYY-MM-DD.pptx`
- `core_meeting_YYYY-MM-DD.csv`

Running it again on the same day replaces them.

Everything you typed is remembered, so next time you only need to click **Build
report**.

## If something goes wrong

| Message | What to do |
|---|---|
| *iLab rejected the API key* | Check the key. If it worked before, it has probably expired (after one year); ask your core administrator for a new one or a later expiry date. |
| *iLab doesn't know this core ID* | Check the core ID. |
| *Can't reach iLab* | Check your internet connection, or your VPN if your institution needs one. |
| *Can't write … close it and try again* | The file is open in PowerPoint or Excel. Close it, then build again. |
| *iLab returned an error (429)* | Too many requests in one minute. Wait a minute and try again. |
| Mac: *Timekeeper wants to use your confidential information stored in "timekeeper"* | Click **Always Allow**. This happens once after each new version of the app. |

## Changing or removing your saved key

- **To change it:** type the new key and click **Build report**.
- **To remove it:**
  - **Mac:** open **Keychain Access**, search for `timekeeper`, and delete the entry.
  - **Windows:** open **Credential Manager → Windows Credentials**, find `timekeeper`,
    and click **Remove**.
- **To reset the other fields:** delete `.timekeeper.json` in your home folder.
  - **Mac:** it's hidden. In Finder press **Cmd+Shift+.** to show hidden files.
  - **Windows:** it's at `C:\Users\<you>\.timekeeper.json`.
