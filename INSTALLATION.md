# Install AMS

This guide installs AMS into **Codex, OpenCode, Pi, or all three**. It downloads the current files directly from this repository. You do not need to clone the repository, download a ZIP, or find a local installer file.

## Before you start

You need a working installation of the coding app you want to use, access to its AI models, and **Python 3.11 or newer**. AMS does not install the coding app or give you access to paid models.

Official setup guides: [Codex](https://developers.openai.com/codex/quickstart/), [OpenCode](https://opencode.ai/docs/), [Pi](https://github.com/earendil-works/pi/tree/main/packages/coding-agent), and [Python](https://www.python.org/downloads/).

For OpenCode and Pi, the app's command must work in your terminal. The installer checks the app's model list. If none of the AMS model names is listed, installation stops with an explanation rather than choosing a different model for you.

These commands download and run code from this repository. Run them only if you trust this project. Public downloads do not require a GitHub account or GitHub CLI. See [download problems](#download-problems) if access is restricted or a download fails.

## Windows

Open the Start menu, type **PowerShell**, and open it normally. You do not need to choose "Run as administrator."

Check Python:

```powershell
python --version
```

It must report version 3.11 or newer. If the command is missing, install Python and open a new PowerShell window.

**Copy only the install command for the app you use.** Run it in PowerShell, not in the AI chat. It can run from any folder.

### Codex

```powershell
Invoke-RestMethod 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' -ErrorAction Stop | python - --harness codex
```

### OpenCode

```powershell
Invoke-RestMethod 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' -ErrorAction Stop | python - --harness opencode
```

### Pi

```powershell
Invoke-RestMethod 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' -ErrorAction Stop | python - --harness pi --install-pi-subagents
```

Pi needs the `pi-subagents` extension to create helpers. The last option lets Pi install that extension if it is missing. An existing registered copy is reused, not automatically updated.

### All three

Use this only when Codex, OpenCode, and Pi are already set up:

```powershell
Invoke-RestMethod 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' -ErrorAction Stop | python - --harness all --install-pi-subagents
```

Choosing `all` does not skip apps that are missing. Choose one app instead when that is all you need.

## macOS or Linux

Open a terminal and check `python3 --version`. You need Python 3.11 or newer, Bash, and the usual command-line utilities listed in the [technical reference](TECHNICAL%20REFERENCE.md#installer-options).

Use Bash for these commands. Copy only the line for your app:

```bash
# Codex
curl -fsSL 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' | python3 - --harness codex

# OpenCode
curl -fsSL 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' | python3 - --harness opencode

# Pi
curl -fsSL 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' | python3 - --harness pi --install-pi-subagents

# All three, when all are already set up
curl -fsSL 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' | python3 - --harness all --install-pi-subagents
```

## Finish and check the installation

Look for **"Selected harness installation complete."** Read any missing-model notices too. A successful install checks the files; it does not make a paid test call or prove that every model will run on your account.

Restart the app you installed into and open a **new chat in your project**. Then follow [Start your first task](PRODUCT%20DOCUMENTATION.md#start-your-first-task).

For Pi, type this inside Pi to check the subagent extension:

```text
/subagents-doctor
```

If the check reports a problem, fix that problem before asking AMS to delegate work.

## What was installed?

The installer puts one shared AMS skill in your user account, plus model presets for the apps you selected. A preset tells the app which model and thinking level to request.

Codex gets 24 presets. OpenCode and Pi get only the ordinary presets whose exact model names appear in the selected provider's list, up to 23 each. The specialized Daybreak preset is not installed into OpenCode or Pi.

The installer does not change your main model, existing provider settings, passwords, permissions, automatic conversation compaction, or saved AMS project settings. Optional AMS companions are not included in this install. The explicit Pi option may add `pi-subagents` through Pi's package manager.

## Update AMS

Run the same installation command you used before, then restart the app and start a new chat. Do not run two AMS installers at the same time.

Supported older Codex presets are upgraded. Edited or unrecognized Codex presets are preserved. OpenCode/Pi presets that differ from the generated files also stop replacement; the installer does not guess which edits to keep.

Updating does not turn AMS on or change your saved policy switches. To update an older project's settings, load AMS in that project and send this **in the AI chat**:

```text
AMS CONFIGURATION UPDATE PROJECT
AMS STATUS
```

This keeps supported settings and adds missing defaults. See [Settings and older projects](PRODUCT%20DOCUMENTATION.md#settings-and-older-projects).

## Common problems

| What you see | What to do |
|---|---|
| `python` or `python3` is not found | Install Python 3.11 or newer, then open a new terminal. |
| `opencode` or `pi` is not on PATH | Make sure that app's command works in this terminal. Follow its setup guide, then reopen the terminal. |
| `No AMS models listed` | Check the selected app's model access. A different provider name may need an [installer option](TECHNICAL%20REFERENCE.md#installer-options). Do not rename another model to pretend it is Sol or Astra. |
| `Pi requires pi-subagents` | Run the Pi command above with `--install-pi-subagents`. If the extension is deliberately disabled, review that setting first. |
| A differing agent/profile file is being preserved | Keep a backup and compare your changes before replacing it. Do not delete all agent files or disable the check. |
| Another installation may be active | Let that installation finish. Do not delete its lock while it is running. |
| AMS does not appear in the app | Restart into a new chat, check that you used the intended user/Pi profile, and check skill-discovery permissions. See [custom locations](TECHNICAL%20REFERENCE.md#installer-options). |

### Download problems

A `404` or access error can mean the download is unavailable to you. A `403` can also be a GitHub request limit. Do not keep running a failed command or treat an empty response as a successful install.

For an access-controlled download or an API limit, [GitHub CLI](https://cli.github.com/) can use an account with repository access. Sign in once with `gh auth login`, then use this alternative in PowerShell:

```powershell
$ams = gh api -H 'Accept: application/vnd.github.raw+json' 'repos/InsecurePassword/Codex-AMS/contents/tools/install_harnesses.py?ref=main'
if ($LASTEXITCODE -ne 0) { throw 'AMS download failed.' }
$ams | python - --harness all --install-pi-subagents
```

Replace `all` with the app you need; leave off `--install-pi-subagents` for Codex-only or OpenCode-only installs. This is optional, not a requirement for normal public downloads. Bash and token-based details are in the [technical reference](TECHNICAL%20REFERENCE.md#authenticated-downloads).

For connection, certificate, or package-download errors, fix the reported connection problem. Do not turn off certificate checks or paste passwords into an installer command.

## Other installation methods

The [technical reference](TECHNICAL%20REFERENCE.md) covers Codex's plugin marketplace, profiles-only installation, existing provider names, separate Pi profiles, offline recovery, optional companions, and removal. The direct commands above are the simplest starting point.
