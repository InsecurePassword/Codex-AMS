# Adaptive Master–Subagent Orchestration

Adaptive Master–Subagent Orchestration (AMS) keeps the current trusted top-level root in control while routing bounded project work to cost-appropriate Codex subagents. AMS does not choose or require the root model/reasoning tier. The root alone owns the automation boundary, physical spawning, hierarchy, routing, integration, acceptance, completion, and user communication.

## Installation

For this private repository, use the complete extracted package: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Local`. See [local installation](INSTALLATION.md#install-from-a-private-repository-or-downloaded-zip); online bootstrap commands require public repository access.

### Codex plugin marketplace

```text
codex plugin marketplace add InsecurePassword/Codex-AMS --ref main
codex plugin add Codex-AMS@Codex-AMS
```

The plugin installs the skill, not custom-agent profiles. Before starting a new Codex thread, deploy all 24 profiles:

```powershell
$env:AMS_INSTALL_PROFILES_ONLY = '1'
try {
    irm 'https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install.ps1' | iex
}
finally {
    Remove-Item Env:AMS_INSTALL_PROFILES_ONLY -ErrorAction SilentlyContinue
}
```

```bash
curl -fsSL 'https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install.sh' | AMS_INSTALL_PROFILES_ONLY=1 bash
```

### Direct fallback installer

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm 'https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install.ps1' | iex"
```

```bash
curl -fsSL 'https://github.com/InsecurePassword/Codex-AMS/raw/refs/heads/main/install.sh' | bash
```

The direct installer deploys the core skill and all 24 profiles. Neither method edits general Codex configuration, project AMS settings, optional companions, operating-system permissions, or unrelated files.

## Runtime model

- The root is a management lane while a compliant delegated route exists.
- Workers are leaves; managers request root-mediated descendants. Assigned same-objective collaborators may exchange scoped evidence directly while the root receives terminal status and one final synthesis.
- One active writer owns each mutable surface.
- Every work order has an explicit scope basis and dependency readiness.
- Completing one bounded objective advances the next authorized objective; it does not stop the automation run.
- Findings and logs are evidence, not authority to expand scope or acceptance.
- Each materially real delegated route receives two bounded attempts; configured root fallback is one third and final attempt.
- Shared process-start failure has one session episode: initial start, one same-lane retry, one root probe, and only after probe success one corrected confirmation.
- Every successful Codex spawn reports the requested AMS profile immediately.
- Astra is a peer route for end-to-end tool-heavy, computer-use, very-large-context, or high-rework-risk work when it is expected to beat Sol on total accepted-task usage, time, or correction.
- Daybreak Blue is a lazy worker-only fallback after a qualifying cyber-safeguard refusal from a real standard-Sol worker/manager work order; root handling alone never qualifies.
- AMS creates no convergence campaigns, receipts, runtime ledger, history, or persistent availability cache.

### Bounded peer channels

With model governance enabled, when two direct `worker/none` sessions must collaborate, the root may name one bounded peer channel in both work orders and provide canonical absolute task paths such as `/root/sol_lead` and `/root/luna_worker`. The peers may use Codex direct messaging for in-scope questions, evidence, and corrections. Peer traffic cannot change scope, dependencies, permissions, ownership, criteria, retry budgets, or authority; a lead remains a worker. The member returns a short terminal stub, the lead returns one final synthesis, and the root alone accepts completion. If direct messaging is unavailable, normal root relay remains valid.

### Astra and computer use

Astra profiles cover `low` through `max`. AMS selects Astra for qualified end-to-end tool work, UI control, very large context, or expensive rework when the expected completed-task cost is lower than Sol; it is neither the default nor merely a last-resort tier. Before browser or desktop control, AMS loads `references/computer-use.md`, confirms the selected session exposes the required tool, prefers shell/API/MCP/direct file access when simpler, and assigns one active controller per interactive surface.

## Configuration

Global/base settings:

```toml
enabled = false
allow_implicit_invocation = true
intensity = "auto"
project_governance = true
model_governance = true
model_guidance = true
automatic_model_switching = true
root_execution_fallback = false
spark_enabled = true
spark_efforts = ["low", "medium", "high"]
profile_management = "auto"
```

Project settings add:

```toml
local_llm_lane = false
```

The local-LLM field is project-only. When false or absent, AMS never loads the companion, reads local profiles, probes an endpoint, or starts a model. Spark and local-lane availability are remembered only for the current top-level session after a capability failure.

## Compact governance

`project_governance = true` retains the proven 3.09-style lifecycle layer: existing deliverables/dependencies/criteria, proportional non-recursive review, automatic continuation through the authorized queue, project-native workflow precedence, and concise handoff. It is disableable with `AMS GOVERNANCE off` and creates no additional acceptance system or durable state.

## Daybreak Blue fallback

AMS includes `ams_daybreak_blue_max`, requesting `gpt-daybreak-blue` at `max` effort. It is considered only after a real standard-Sol worker or delegated-manager work order explicitly refuses one unchanged authorized defensive cybersecurity work unit for cyber-safeguard reasons. Root handling without that work order is ineligible. Generic failure, weak output, missing tools, permission denial, or account/transport failure does not trigger it.

Before project data is supplied, `references/daybreak-blue.md` requires exact approved internal access-path evidence and a capability preflight. Observed `gpt-5.6-sol` is valid only when the same admission directly proves use of the approved Daybreak Blue surface; the underlying model ID alone is insufficient. The lane is worker-only, single-flight per access boundary, limited to one confirmed-start task, and cannot broaden scope, permissions, targets, data, or operational effect. Installation does not grant Trusted Access. The current official access alias, provisioning boundary, and onboarding procedure remain external OpenAI controls:

- https://help.openai.com/en/articles/20001258-openai-daybreak-trusted-access-for-cyber-overview
- https://help.openai.com/en/articles/20001261-enterprise-daybreak-onboarding

## Optional companions

Repository-only companions are installed separately and have implicit invocation disabled:

- `ams-local-openai-lane`: explicitly authorized project-local OpenAI-compatible work with context-profile selection and Codex verification;
- `ams-app-task-lane`: explicitly authorized user-visible app-task transport;
- `ams-runtime-observation`: explicitly requested local runtime-metadata corroboration.

The local lane consumes stable prebuilt/tested project profiles and never develops them at runtime. It sends fresh context, requires a returned model identity equal to the requested model or a profile-declared bounded alias, reports requested/observed identity separately, can keep/stop a companion-started model, and requires Codex verification. Non-context helper failure suppresses it for the session until `AMS LOCAL LLM on`; helper-process no-start uses runner fail-fast, while no fitting context falls back only that work.

## Documentation

- [INSTALLATION.md](INSTALLATION.md)
- [PRODUCT DOCUMENTATION.md](PRODUCT%20DOCUMENTATION.md)
- [LOCAL-LLM-PROFILE-DEVELOPMENT.md](LOCAL-LLM-PROFILE-DEVELOPMENT.md) — repository-only profile development and qualification guide
- `adaptive-master-subagent-orchestration/references/`

## Requirements

- Codex with plugin/skill and custom-subagent support;
- PowerShell 5.1+ on Windows or Bash plus standard utilities listed in [INSTALLATION.md](INSTALLATION.md);
- Python 3.11+ only for repository verification and the optional local/runtime-observation helpers;
- approved Daybreak access on the exact internal product surface and boundary only when the optional Daybreak fallback is used.

## Optional model policies

The user-selected master still delegates execution and technical diagnosis, supervises unresolved blockers, and continues independent authorized work. It never guesses its own model or execution skills. These autonomy rules do not switch off.

Three independent Booleans default to true for existing installations:

| Setting | Loaded policy | Off |
|---|---|---|
| `model_governance` | `references/model-governance.md` | Master chooses team organization without AMS intensity, allocation, or packet prescriptions. |
| `model_guidance` | `references/model-guidance.md` | No AMS model-purpose or effort advice is supplied. |
| `automatic_model_switching` | `references/model-switching.md` | Master chooses/reconsiders routes freely, without AMS switching heuristics. |

Use `AMS MODEL GOVERNANCE on|off`, `AMS MODEL GUIDANCE on|off`, and `AMS MODEL SWITCHING on|off`. `AMS GOVERNANCE` remains the separate project-governance control. Settings never authorize more permissions, activate local endpoints or Daybreak, or enable root fallback.

For native model judgment inside AMS, set the three fields false in the project settings and start a fresh root and fresh agents. This preserves delegation, manager assessment of unresolved blockers, existing failure budgets, scope/validation, and direct coder/reviewer messaging. It is not the same as running without AMS. Turning switching off does not prohibit switching.

Ordinary profiles now contain only model/effort metadata and general task instructions. AMS role and communication rules are supplied with assignments, not permanently imposed on Sol or another family. The existing bounded two-worker peer protocol remains available when model governance is on; off uses named same-objective collaborators without the peer packet.
