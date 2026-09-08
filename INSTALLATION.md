# Installation

AMS supports a Codex plugin marketplace installation and a direct repository-tree fallback. Neither path installs optional companions or edits project AMS settings.

## Install from a private repository or downloaded ZIP

Extract the complete trusted package, open its `Codex-AMS` directory, and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Local
```

On Linux/macOS: `bash ./install.sh --local`.

This uses the adjacent manifest and package files without network access or GitHub credentials. Hash/membership checks, recognized profile upgrades, rollback, and settings preservation are unchanged. Set `AMS_INSTALL_PROFILES_ONLY=1` for profiles-only installation. Start a new Codex thread after upgrading the skill and profiles.

The online commands below require public access to the repository. A browser login does not authenticate `irm` or `curl`; for this private repository, use the local method.

## Codex, OpenCode, and Pi targets

The direct installer defaults to Codex. From a complete checkout or extracted ZIP, select `codex`, `opencode`, `pi`, or `all`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Local -Harness all
```

Bash equivalent: `bash ./install.sh --local --harness all`.

OpenCode/Pi targets require Python 3.11+ and the selected harness on PATH. Codex-only installation still needs no Python. The installer reuses the same verified shared skill in `~/.agents/skills`; it does not register this repository in another harness's plugin marketplace.

| Target | Native presets | Provider default |
|---|---|---|
| Codex | `$CODEX_HOME/agents`, otherwise `~/.codex/agents` (24 TOMLs) | Existing Codex registration |
| OpenCode | `$OPENCODE_CONFIG_DIR/agents`, otherwise `$XDG_CONFIG_HOME/opencode/agents` or `~/.config/opencode/agents` | `openai` |
| Pi | `$PI_CODING_AGENT_DIR/agents`, otherwise `~/.pi/agent/agents` | `openai-codex` |

OpenCode/Pi Markdown presets are translated from the 23 ordinary model profiles, retaining their neutral task instructions and requested reasoning effort. Daybreak is not translated. Only exact model IDs advertised by the selected provider's `opencode models` or `pi --list-models` catalog are installed; unavailable models are reported, never substituted. No matching models aborts before AMS writes. Catalog presence does not verify authentication, model execution, or provider support for every effort.

For another existing provider use `-OpenCodeProvider NAME` or `-PiProvider NAME`; Bash uses `--opencode-provider NAME` and `--pi-provider NAME`. Provider configuration and credentials are never created or changed. A local Qwen route is not silently installed under a Sol/Astra name.

Pi requires the existing `pi-subagents` package. A registered installation is reused. When absent, the installer stops before AMS writes unless explicitly given `-InstallPiSubagents` (Bash: `--install-pi-subagents`):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Local -Harness all -InstallPiSubagents
```

That flag permits `pi install npm:pi-subagents` to download and register the dependency using Pi's own package manager. It does not update an already registered package or change compaction, model, or permission settings. The dependency remains installed if a later AMS install fails. Native catalog commands may refresh catalog metadata; `-Local`/`--local` selects the AMS source, not a network sandbox for those harness commands. No inference is performed.

For separate Pi launch profiles, set `PI_CODING_AGENT_DIR` to the same directory the launcher uses and repeat the Pi target for each intended profile. Other profile directories are not scanned or changed. `AMS_INSTALL_PROFILES_ONLY=1` installs only selected registries; otherwise the skill is shared. Non-Codex-only targets never write the Codex registry. Run installations sequentially.

Differing native agent files are preserved and block installation; reconcile them rather than using an overwrite switch. Existing project/global AMS settings, harness providers, credentials, and permissions are preserved. A custom `AMS_SKILL_HOME` needs explicit skill discovery configuration in each harness; the installer does not edit that configuration.

Restart the selected harnesses after installation. In Pi run `/subagents-doctor`, then invoke `/skill:adaptive-master-subagent-orchestration`. In OpenCode ask it to load the `adaptive-master-subagent-orchestration` skill. Use native task/subagent tools and parent relay when direct peer messaging is unavailable. Codex-only app tasks, runtime observation, and Daybreak are not ported. Optional companions are not installed.

## Marketplace installation

```text
codex plugin marketplace add InsecurePassword/Codex-AMS --ref main
codex plugin add Codex-AMS@Codex-AMS
```

The plugin installs the core skill but current plugin manifests do not register custom-agent profiles. Deploy all 24 profiles before starting a new thread.

### Windows profile bootstrap

```powershell
$env:AMS_INSTALL_PROFILES_ONLY = '1'
try {
    irm 'https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install.ps1' | iex
}
finally {
    Remove-Item Env:AMS_INSTALL_PROFILES_ONLY -ErrorAction SilentlyContinue
}
```

### Linux/macOS profile bootstrap

```bash
curl -fsSL 'https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install.sh' | AMS_INSTALL_PROFILES_ONLY=1 bash
```

Profiles-only mode verifies the complete canonical manifest and profile bytes, then transactionally changes only the agent registry. It does not install or replace the skill directory.

## Direct fallback installer

### Windows

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm 'https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install.ps1' | iex"
```

### Linux/macOS

```bash
curl -fsSL 'https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install.sh' | bash
```

Bash requires `curl`, `awk`, `sort`, `uniq`, `cmp`, `mktemp`, `wc`, `tr`, `grep`, `head`, `find`, `dirname`, `stat`, `chmod`, `mkdir`, `mv`, `rm`, `cp`, `date`, `sleep`, `ps`, `od`, `hostname`, and either `sha256sum` or `shasum`. Windows requires PowerShell 5.1+.

## Installer scope and verification

Without the local option, the installers fetch only canonical `main`:

```text
https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install-manifest.txt
https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/adaptive-master-subagent-orchestration/...
```

They expose no repository/ref/manifest override. Both installers:

1. serialize package/profile transactions with an owner-token install lock; recover only a stable lock older than 30 seconds whose same-host PID is proven dead, or a stable old empty ownerless crash lock; foreign-host, live, young, malformed, redirected, or changing locks fail closed;
2. require two byte-identical manifests;
3. require exact safe core membership, byte lengths, and SHA-256 hashes;
4. stage the complete package before replacement;
5. validate all 24 managed profiles;
6. transactionally replace the skill and eligible profiles with rollback;
7. leave byte-identical profiles unchanged;
8. upgrade only exact recognized official predecessor profiles;
9. preserve and block on every other differing profile;
10. preserve settings and unrelated files.

AMS owns no persistent runtime/convergence state, so package operations require no campaign export, history migration, lease, receipt, or archive/prune procedure. The included Daybreak profile and reference grant no Trusted Access, identity, authorization, permission, target authority, or retention treatment; those remain external provisioning requirements.

## Installed paths

```text
$HOME/.agents/skills/adaptive-master-subagent-orchestration/
$CODEX_HOME/agents/ams_*.toml
```

When `CODEX_HOME` is unset, profiles use `$HOME/.codex/agents/`. `AMS_SKILL_HOME` and `CODEX_HOME` may select destination roots. Installers do not edit `$CODEX_HOME/config.toml`, project `.codex/ams-orchestration.toml`, operating-system ACL policy, credentials, optional companions, or unrelated Codex configuration.

## Optional companions

Copy a desired companion directory from `extensions/` to `$HOME/.agents/skills/`. Companions carry no AMS release or compatibility identity. Replace the complete directory from the same audited source snapshot as a unit; never mix files from different snapshots:

```text
extensions/ams-local-openai-lane/
extensions/ams-app-task-lane/
extensions/ams-runtime-observation/
```

All have implicit invocation disabled. Installing a companion enables nothing.

The local OpenAI companion requires Python 3.11+ and separately developed/tested project profiles under `<project-root>/.codex/ams-local-llm/profiles/`. Do not create or tune profiles during AMS runtime.

## Update, repair, downgrade, and uninstall

- Marketplace update: upgrade/reinstall the plugin, rerun profiles-only bootstrap, then start a new thread.
- Direct update/repair: rerun the direct installer.
- Marketplace uninstall: `codex plugin remove Codex-AMS@Codex-AMS`; optional marketplace-source removal is separate.
- Direct uninstall removes only the skill directory through an explicit package-maintenance action.
- Settings and installed profiles remain unless separately authorized for cleanup.
- Before downgrade, back up complete current settings and prepare a separate older-compatible live settings file. No runtime-state export is required.

Installation completion triggers no automatic audit, activation, project pause, or user-action request.
