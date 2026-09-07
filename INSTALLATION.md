# Installation

AMS supports a Codex plugin marketplace installation and a direct repository-tree fallback. Neither path installs optional companions or edits project AMS settings.

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

The installers fetch only canonical `main`:

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
