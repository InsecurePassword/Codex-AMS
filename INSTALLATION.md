# Installation

AMS supports Codex, OpenCode, and Pi. Normal installation pulls directly from canonical `main`; no clone, ZIP extraction, or local package path is required.

## Remote installation

Public downloads need no GitHub account, token, or GitHub CLI. Run in PowerShell:

```powershell
Invoke-RestMethod 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' -ErrorAction Stop | python - --harness all --install-pi-subagents
```

In Bash:

```bash
curl -fsSL 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' | python3 - --harness all --install-pi-subagents
```

Use `codex`, `opencode`, or `pi` instead of `all` to install only one harness. `--install-pi-subagents` is needed only when Pi is selected and `pi-subagents` is not already registered.

The streamed helper fetches the current manifest and package files from `main`, verifies every core file by size and SHA-256, stages them temporarily, and invokes the existing native installer transaction. Temporary package files are removed automatically. No model inference is performed.

The streamed helper requires Python 3.11+ for every target. OpenCode/Pi targets also require the selected harness on `PATH`. Windows uses PowerShell 5.1+; Linux/macOS uses Bash and standard utilities.

| Target | Native presets | Provider default |
|---|---|---|
| Codex | `$CODEX_HOME/agents`, otherwise `~/.codex/agents` (24 TOMLs) | Existing Codex registration |
| OpenCode | `$OPENCODE_CONFIG_DIR/agents`, otherwise `$XDG_CONFIG_HOME/opencode/agents` or `~/.config/opencode/agents` | `openai` |
| Pi | `$PI_CODING_AGENT_DIR/agents`, otherwise `~/.pi/agent/agents` | `openai-codex` |

OpenCode/Pi presets are translated from the 23 ordinary AMS profiles. Daybreak is not translated. Only exact model IDs advertised by the selected provider's native model catalog are installed; missing models are reported and never substituted. Provider configuration, credentials, permissions, compaction, and AMS project/global settings are not changed.

For another existing provider, add `--opencode-provider NAME` or `--pi-provider NAME`. For separate Pi launch profiles, set `PI_CODING_AGENT_DIR` to the same directory used by that launcher and run the Pi target for each intended profile.

Differing generated OpenCode/Pi agent files are preserved and block replacement. Restart selected harnesses after installation. In Pi, run `/subagents-doctor` and then `/skill:adaptive-master-subagent-orchestration`. In OpenCode, load the `adaptive-master-subagent-orchestration` skill. Parent relay is used when direct peer messaging is unavailable. Codex-only Daybreak/app-task/runtime-observation capabilities are not ported by this installer.

## Codex plugin marketplace

```text
codex plugin marketplace add InsecurePassword/Codex-AMS --ref main
codex plugin add Codex-AMS@Codex-AMS
```

The plugin installs the core skill but current plugin manifests do not register custom-agent profiles. Bootstrap the profiles directly from remote `main`:

```powershell
$env:AMS_INSTALL_PROFILES_ONLY = '1'
try {
    Invoke-RestMethod 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' -ErrorAction Stop | python - --harness codex
}
finally {
    Remove-Item Env:AMS_INSTALL_PROFILES_ONLY -ErrorAction SilentlyContinue
}
```

```bash
curl -fsSL 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' | AMS_INSTALL_PROFILES_ONLY=1 python3 - --harness codex
```

Profiles-only mode changes only the selected registry and does not replace the shared skill. Start a new Codex thread after installing or upgrading profiles.

## Optional authenticated downloads

For access-controlled downloads or GitHub API rate limits, use an existing GitHub CLI login:

```powershell
gh api -H 'Accept: application/vnd.github.raw+json' 'repos/InsecurePassword/Codex-AMS/contents/tools/install_harnesses.py?ref=main' | python - --harness all --install-pi-subagents
```

In Bash, use `python3` instead of `python`. The helper also reuses `GH_TOKEN` or `GITHUB_TOKEN` when provided. Authentication is optional for public access and does not change the installation targets or settings.

## Offline recovery

`install.ps1 -Local`, `install.sh --local`, and the helper's hidden `--local` mode remain available for recovery/testing when a complete trusted package is already present. They are not the normal installation path.

## Installer scope and verification

Remote installation is fixed to `InsecurePassword/Codex-AMS` `main`; there is no repository/ref override. The installer:

1. reads the canonical manifest and checks safe exact membership;
2. verifies every staged core file by byte length and SHA-256;
3. confirms the manifest did not change during staging;
4. uses the existing transactional native installer with package/profile locking and rollback;
5. leaves byte-identical profiles unchanged;
6. upgrades only recognized official predecessor profiles;
7. preserves and blocks on other differing profiles;
8. preserves unrelated files and harness/project settings.

The core skill is installed under `$HOME/.agents/skills/adaptive-master-subagent-orchestration/`. Codex profiles use `$CODEX_HOME/agents/` or `$HOME/.codex/agents/`. Optional companions remain separate and are not installed automatically.

## Update, repair, downgrade, and uninstall

- Update/repair: rerun the same remote installation command.
- Marketplace update: update/reinstall the Codex plugin and rerun the Codex profiles bootstrap.
- Marketplace uninstall: `codex plugin remove Codex-AMS@Codex-AMS`.
- Direct uninstall and profile/settings cleanup remain explicit package-maintenance actions.
- Before downgrade, back up current settings and prepare settings compatible with the older package.

Installation completion triggers no automatic audit, activation, project pause, or user-action request.
