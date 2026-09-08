# AMS technical reference

For implementers and advanced users. Start with [Installation](INSTALLATION.md) and the [User guide](PRODUCT%20DOCUMENTATION.md) for everyday use.

This reference describes the current implementation, not a separate execution engine. AMS behavior is primarily instructions followed by the host agent. The host's tools, sandbox, permissions, and model availability remain independent controls. Local scripts implement installation and the optional helpers; prose does not itself enforce a permission boundary.

The installed contracts under [the core skill](adaptive-master-subagent-orchestration/SKILL.md) remain authoritative. Paths written as `references/...` below are relative to that skill directory. This technical reference is not installed or loaded by normal AMS execution.

## Product boundary

AMS has two core responsibilities:

1. keep the current trusted top-level root in control of the authorized automation boundary, physical dispatch, hierarchy, sequencing, ownership, integration, acceptance, completion, and user communication;
2. delegate scoped work and supervise recovery, with optional policies for team organization, model guidance, and model switching.

The root model and reasoning effort are external configuration. AMS does not select, require, infer, or attest them. Workers are leaves. Delegated managers request root-mediated descendants and never physically spawn, expand authority, contact the user, or accept completion.

## Core behavior

Core AMS provides:

- 24 Codex model/effort profiles, plus native OpenCode/Pi presets for exact advertised ordinary-model matches;
- root-mediated delegation; optional model governance adds finite allocation and Balanced team limits;
- same-objective collaboration through available direct messaging or parent relay; optional model governance adds the bounded-pair protocol;
- one-writer mutable-surface ownership;
- mandatory scope/dependency admission;
- automation-boundary continuation from one accepted objective to the next;
- compact default-on project governance;
- bounded blocker diagnosis without recovery loops;
- command-runner fail-fast with three diagnostic starts and at most one corrected original-lane confirmation after a successful probe;
- bounded root fallback with independent validation;
- session-local Spark availability suppression;
- optional project-local local-LLM routing through a separate companion;
- refusal-triggered Daybreak Blue capability preflight and one-task defensive fallback;
- transactional package/profile installation.

AMS creates no convergence campaign, persistent custody/receipt system, archive/prune history, runtime lock/state, review/accounting ledger, or availability cache.

### Bounded peer channels

With model governance enabled, when direct collaboration is cheaper than relaying every intermediate message through the root, the root may place exactly two direct `worker/none` siblings in one bounded peer channel. Both work orders must name the same channel, canonical absolute task paths, purpose, lead/member roles, writer ownership, escalation conditions, and root-return mode. Peers may use `send_message` or `followup_task` only with the named path. Messages are evidence or scoped steering inside the existing orders and cannot alter objective, scope, dependencies, permissions, ownership, criteria, delegation, retry budget, or user authority. The lead remains a worker. The member sends detail to the lead and returns a short root terminal stub; the lead returns one synthesized result. Root acceptance and completion authority do not move.

## Settings and precedence

Project settings:

```text
<project-root>/.codex/ams-orchestration.toml
```

Global/base settings:

```text
$CODEX_HOME/ams-orchestration.toml
```

When `CODEX_HOME` is unset, use `~/.codex/ams-orchestration.toml`. These are AMS settings paths in all three harnesses; the installer does not create or migrate them.

A present project file fully replaces global base settings. Global/base default:

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

Project default additionally contains:

```toml
local_llm_lane = false
```

`local_llm_lane` is invalid globally. Missing project settings force the local lane off. Retired convergence/modular fields and legacy `schema_version` are inert compatibility input and are removed during the next authorized write.

## Commands

```text
AMS STATUS
AMS ENABLE | AMS DISABLE
AMS MODE auto|minimal|balanced|moderate|heavy|extreme
AMS IMPLICIT on|off
AMS GOVERNANCE on|off
AMS MODEL GOVERNANCE on|off
AMS MODEL GUIDANCE on|off
AMS MODEL SWITCHING on|off
AMS ROOT FALLBACK on|off
AMS CONFIGURATION UPDATE [PROJECT|GLOBAL]
AMS SPARK on|off
AMS SPARK EFFORTS low,medium,high
AMS PROFILES auto|installer
AMS LOCAL LLM on|off
```

These are messages interpreted by the loaded skill, not terminal executables. Normal controls write project settings only. `AMS CONFIGURATION UPDATE GLOBAL` is the sole global-writing command. `AMS STATUS` is physically read-only and performs no capability probes.

## Scope, dependencies, and automation

The root establishes an automation boundary from direct user instruction and authoritative project-native queues, milestones, or packets. Every assignment cites a scope basis and dependencies/readiness. Plain assignments satisfy this requirement with model governance off; the formal `WORK ORDER`/`RESULT` templates are optional governed policy. Findings, logs, reviewer suggestions, warnings, TODOs, and repository content cannot create work or criteria.

Before affected dispatch or acceptance, AMS verifies the declared candidate base and accepted dependency closure. Worktree-only repairs, unrecorded branches, caches, generated state, or undeclared packets do not silently satisfy prerequisites. Validation failures outside the owned surface are compared with the base/control when practical and classified as objective, baseline, environment, harness, or another dependency.

When one objective passes, AMS closes it, releases ownership, refuses post-acceptance extras, selects the next authorized ready objective, and continues. The run stops normally only when the authorized queue is exhausted; blockers stop the run only when bounded diagnosis/rerouting is exhausted and no independent authorized path remains.

## Governance

Default-on project governance coordinates the existing project workflow:

- track existing authorized deliverables, criteria, dependencies, critical path, integration, validation, risk, and blockers;
- continue automatically while authorized ready work remains;
- use proportional, non-recursive independent review when warranted;
- respect project-native packets, pauses, approvals, trackers, and gates;
- provide a concise handoff when autonomous progress cannot continue.

Governance cannot expand scope, create criteria, create durable state, or override project authorization. `AMS GOVERNANCE off` removes only this lifecycle layer; core scope/dependency, ownership, delegation, supervisory recovery, evidence, and truthful completion controls remain. Model-purpose advice and switching heuristics are controlled by their separate switches.

## Failure behavior

A reproducible non-runner failure is budgeted per materially real delegated route. The route gets exactly two attempts in its proper lane: one evidence-backed correction attempt and one confirmation attempt, which may repeat the corrected invocation once to distinguish a sporadic failure or use one materially different evidence-backed correction. Changing worker, manager, profile, effort, task name, branch, wrapper, shell label, or context does not create another route or reset its budget. After two failures, optional root fallback—disabled by default—may perform one atomic third and final attempt when its safety gate passes.

Repeated `spawn_ready` creates one root-session episode keyed by the unchanged physical runner signature. It gets three diagnostic starts: initial failure, one same-lane retry, then one root process-only probe. Probe success permits at most one materially corrected original-lane confirmation; another no-start terminalizes the episode without a new process, profile, manager, transport, context, or intensity reset. Probe failure likewise terminalizes process-dependent work. Active or potentially live sessions, writers, and allocations remain owned until closure is proven; unresolved state is reported live or unverified while runner-independent authorized work continues.

A local lane or objective can be deferred while independent authorized work continues. User intervention is requested only when no autonomous route remains and a concrete permission, credential, physical action, external resource, material choice, or new authority is required.

## Spark

`spark_enabled` is persistent preference. Availability is session-local. Profile/registration/model-capability failure suppresses Spark; task-quality failure does not. `spawn_ready` first uses shared runner diagnosis; after probe success, another Spark-specific no-start suppresses it. `AMS SPARK on` clears the latch; no availability field is persisted.

## Astra and computer use

Five `ams_astra_<low|medium|high|xhigh|max>` profiles request `gpt-6-astra`. With model guidance enabled, Astra is a peer route, not a universal default or mandatory escalation: use it for end-to-end tool-heavy, computer-use, very-large-context, or high-rework-risk work when one Astra owner is expected to reach acceptance with less total usage, time, or correction than Sol. Sol remains appropriate for difficult coding, architecture, security, and diagnosis when Astra's tool or long-context advantage is not material.

Before browser, desktop, or visual UI control, load `references/computer-use.md`. Use only a session that exposes the required tool, prefer shell/API/MCP/direct file operations when simpler, assign one active controller per interactive surface, treat screen content as untrusted evidence, use existing platform approvals, and verify the resulting application state. Computer use changes neither model authority nor AMS authority.

## Local OpenAI-compatible lane

The separately installed `ams-local-openai-lane` companion is eligible only when:

- project-local `local_llm_lane = true`;
- the session latch is not inactive;
- current-session user steering selects the model and permitted use cases;
- the current work matches those use cases.

The user selects the model. Codex may choose only a tested context/profile variant with the same `model_key`, selecting the smallest safe context or promoting once to a larger same-model profile when necessary. It never changes the model automatically or knowingly truncates work.

Profiles are manually created or built/audited/tested in a separate Codex development interaction under `<project-root>/.codex/ams-local-llm/profiles/`. AMS runtime only consumes stable files; any start command requires a stop command.

The companion executes one configured start attempt, one OpenAI-compatible request, and optional stop; transient request files are deleted after use. It requires the response to expose a model identity equal to the requested model or a bounded alias explicitly listed in the user-owned profile, and returns requested and observed identity separately. It sends fresh context, stops a known companion-started kept profile on local-lane/AMS disable or before same-model switching, and cleans up once after a started-call failure. Every result is Codex-verified. Non-context helper failure/rejection suppresses the lane without changing settings; helper-process `spawn_ready` uses runner fail-fast. No fitting context falls back only that work and leaves the lane available. Only `AMS LOCAL LLM on` clears an inactive latch.

## Daybreak Blue

The installed `ams_daybreak_blue_max` worker profile requests `gpt-daybreak-blue` at `max` effort. It is never a normal strength tier and is considered only after an explicit cybersecurity-safeguard refusal from a real standard-Sol worker or delegated-manager work order for one unchanged authorized defensive work unit. Root handling without that work order does not qualify.

`references/daybreak-blue.md` requires:

- one stable fallback unit bound to the original scope, dependencies, authorization, data, and operational boundary;
- one stable access boundary and an ephemeral current-session admission, with durable closure separated from session generation;
- exact approved internal access-path, product-surface, identity-boundary, and retention evidence;
- platform attestation, the current OpenAI onboarding workflow in a disposable non-project workspace, or a distinguishing non-project defensive fixture;
- exact root-objective, operation, work-order, nonce, start-attempt, parent/custody, and ownership correlation;
- one confirmed-start task, with one pre-start retry only after a proven temporary no-start;
- durable access closure only from authoritative access/capability evidence; runner/no-start failure is session-local and never becomes entitlement evidence;
- parent resumption or explicit supersession after every terminal preflight/task path;
- requested route identity `gpt-daybreak-blue`; observed `gpt-5.6-sol` is accepted only with direct same-admission evidence that the approved Daybreak Blue product surface was used; the underlying model ID alone proves nothing;
- no model substitution, offensive-workflow expansion, additional Daybreak unit, or root-execution escalation.

The profile grants no access, permission, authorization, target authority, or retention treatment. Access provisioning remains external and is not inferred from installation or model availability. Daybreak creates no AMS database, transcript service, receipt history, runtime lock, or recovery file.

## Package boundaries

Installed core contains 44 files: `SKILL.md`, `agents/openai.yaml`, 24 profiles, and 18 normative references. [install-manifest.txt](install-manifest.txt) records their exact lengths and hashes. Repository documentation, `.github/`, `tools/`, and `verification/` are not installed as core instructions. `extensions/` contains separately installed companions; their helpers run only when explicitly used.

The root loads `SKILL.md`, project control, runtime core, and scope/dependency control for active work. Project governance and each model policy load only when enabled. Other references are gated. Outside Codex, `harness-compatibility.md` maps native tools and registries. Only the selected model profile applies to its child; the full profile directory is not added to each prompt.

The Codex plugin manifest declares only the skill path. It does not declare the bundled TOMLs as registered agents, so this package's marketplace path requires the profiles-only bootstrap before a new thread. This is a statement about this package, not a claim that all plugins are unable to distribute agents.

Direct installation deploys the shared skill and the selected harness registries. Codex gets all 24 bundled TOMLs; OpenCode and Pi receive up to 23 translated ordinary presets after exact model-catalog matching. Daybreak is not translated. Native OpenCode/Pi presets contain neutral task instructions, not permanent AMS worker/manager roles.

No AMS-authored durable orchestration database, daemon, task ledger, or recovery subsystem is installed. The host apps and `pi-subagents` may maintain their own sessions and artifacts; that is separate from AMS's no-runtime-state instruction.

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

## Model preset reference

These are the package's requested identifiers and efforts, not claims about account entitlement or effective backend behavior.

| Family | Requested model | Bundled efforts |
|---|---|---|
| Sol | `gpt-5.6-sol` | `low`, `medium`, `high`, `xhigh`, `max` |
| Terra | `gpt-5.6-terra` | `low`, `medium`, `high`, `xhigh`, `max` |
| Luna | `gpt-5.6-luna` | `low`, `medium`, `high`, `xhigh`, `max` |
| Astra | `gpt-6-astra` | `low`, `medium`, `high`, `xhigh`, `max` |
| Spark | `gpt-5.3-codex-spark` | `low`, `medium`, `high` |
| Daybreak Blue | `gpt-daybreak-blue` | `max`, specialized Codex-only contract |

Codex filenames are `ams_<family>_<effort>.toml`; the special name is `ams_daybreak_blue_max.toml`. OpenCode/Pi use the corresponding `.md` names and provider-qualified model IDs. OpenCode receives `mode: subagent` and `reasoningEffort`; Pi receives `name`, `thinking`, and `systemPromptMode: append`.

Ordinary profiles contain only route metadata and general task instructions. AMS supplies its role, scope, permissions, validation, and communication instructions with the assignment. Model advice is in `model-guidance.md`; switching policy is in `model-switching.md`. No benchmark in this repository proves that one model is always cheaper.

## Intensity and Rush

Intensity applies only with model governance enabled. `auto` chooses a useful small topology. `minimal` permits at most one active non-root session. `balanced` is stored as `moderate` and permits either two direct non-manager sessions or one manager with at most three direct non-manager descendants, not a mixture or nesting. Heavy and Extreme admit useful parallelism and supervision subject to capacity, finite allocation, dependencies, and one-writer ownership.

The explicit current-turn request `Use Zergling Rush for this task` activates the separate speed-first policy only with model governance enabled. A stored `zergling-rush` value, old handoff, or generic request to be fast is not consent. Rush may spend substantially more model usage, but it changes neither permissions nor acceptance and never increases Daybreak or shared-runner budgets. See [the Rush contract](adaptive-master-subagent-orchestration/references/zergling-rush.md).

The optional [Extreme standalone prompt](SOL-ULTRA-AMS-EXTREME-ORCHESTRATION-PROMPT.md) is not installed, automatically loaded, or a source of master-model identity.

## Installer options

The normal entry point is the remotely streamed [tools/install_harnesses.py](tools/install_harnesses.py), shown in [Installation](INSTALLATION.md). It requires Python 3.11+ for **every** target, including Codex. The direct native Codex scripts do not themselves need Python; their OpenCode/Pi wrappers do.

| Python helper option | Meaning |
|---|---|
| `--harness codex`, `opencode`, `pi`, or `all` | Select registries. Required. `all` attempts each app and retains successful installs when another app needs configuration. |
| `--opencode-provider NAME` | Use an existing OpenCode provider ID; default `auto` discovers unambiguous exact model matches. |
| `--pi-provider NAME` | Use an existing Pi provider ID; default `auto` discovers unambiguous exact model matches. |
| `--install-pi-subagents` | Permit Pi's package manager to install `npm:pi-subagents` when not already registered. Valid only for `pi` or `all`. |
| `--local` | Use an existing complete trusted source tree. Recovery/testing option, not the normal remote install. |

Remote canonical `main` is the default even when the helper is run from a checkout. Only explicit `--local` selects that checkout. Neither exposes an arbitrary repository/ref override.

The helper reads `opencode models` or `pi --list-models` in the caller's working directory, preserving project-specific provider discovery and the user's Pi offline setting. Exact model IDs are matched across providers. A unique provider is selected per model. An exact existing generated preset preserves its prior provider; otherwise ambiguous matches require an explicit provider option and list the actual choices. Missing exact models are reported, not silently substituted. Catalog presence does not verify authentication or that the backend accepts every requested effort.

The shared skill and selected Codex registry are installed before per-app model configuration. OpenCode and Pi are then configured independently. A target failure reports `NOT CONFIGURED`, rolls back only that target's newly created agent files, and retains the shared skill and other successful targets. The helper exits `0` for all selected targets installed, `2` for partial installation, and `1` for a fatal shared-package or argument error. A missing model catalog is not reported as successful model configuration.

| Environment variable | Purpose |
|---|---|
| `AMS_SKILL_HOME` | Shared skill parent; default `~/.agents/skills`. A custom directory must be configured for discovery in each app separately. |
| `CODEX_HOME` | Codex home; default `~/.codex`. Native presets go in `agents/`. |
| `OPENCODE_CONFIG_DIR` | OpenCode config directory; takes precedence over the XDG/default location. |
| `XDG_CONFIG_HOME` | OpenCode falls back to its `opencode/` child, otherwise `~/.config/opencode`. |
| `PI_CODING_AGENT_DIR` | Pi profile home; default `~/.pi/agent`. Use the same value as the intended launcher and repeat for each desired Pi profile. |
| `AMS_INSTALL_PROFILES_ONLY=1` | Change only selected agent registries, not the shared skill. |
| `GH_TOKEN` / `GITHUB_TOKEN` | Optional repository-download authentication; never a model-provider credential. |

`AMS_INSTALL_SKILL_ONLY` is an internal handoff from the translator to the native installer. It is not a model-policy setting. For a non-Codex-only target, the helper does not write the Codex registry.

Pi dependency installation is explicitly opt-in, reuses registered packages, and does not update an existing package. A newly added package remains installed if a later AMS step fails. Pi's own package manager may add package resources; AMS does not configure unrelated packages, model defaults, permissions, or compaction. Native catalog commands may refresh metadata; `--local` is not a network sandbox for those commands.

The native wrappers accept `-Harness`, `-OpenCodeProvider`, `-PiProvider`, and `-InstallPiSubagents` in PowerShell, or their lower-case hyphenated equivalents in Bash. They default to Codex. OpenCode/Pi wrapper invocations fetch and run the shared Python helper remotely unless `-Local`/`--local` was explicitly selected. The streamed Python command remains the simplest cross-harness entry point.

Bash's core installer requires `curl`, `awk`, `sort`, `uniq`, `cmp`, `mktemp`, `wc`, `tr`, `grep`, `head`, `find`, `dirname`, `stat`, `chmod`, `mkdir`, `mv`, `rm`, `cp`, `date`, `sleep`, `ps`, `od`, `hostname`, and `sha256sum` or `shasum`. The shared native transaction runs through Windows PowerShell 5.1+ on Windows.

## Codex marketplace and profiles-only installation

Choose the direct install **or** the marketplace-managed skill path; do not intentionally maintain competing AMS skill copies. Existing multi-harness installations can continue to use the shared direct-installed skill.

For the marketplace path, run in a terminal with Codex installed:

```text
codex plugin marketplace add InsecurePassword/Codex-AMS --ref main
codex plugin add Codex-AMS@Codex-AMS
```

These register the Codex plugin, not an OpenCode or Pi plugin. Then bootstrap the Codex agent registry in PowerShell:

```powershell
$previous = $env:AMS_INSTALL_PROFILES_ONLY
try {
    $env:AMS_INSTALL_PROFILES_ONLY = '1'
    Invoke-RestMethod 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' -ErrorAction Stop | python - --harness codex
}
finally {
    if ($null -eq $previous) { Remove-Item Env:AMS_INSTALL_PROFILES_ONLY -ErrorAction SilentlyContinue }
    else { $env:AMS_INSTALL_PROFILES_ONLY = $previous }
}
```

Bash:

```bash
curl -fsSL 'https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/tools/install_harnesses.py' | AMS_INSTALL_PROFILES_ONLY=1 python3 - --harness codex
```

Start a new Codex thread. A downloaded profile is not proof of current-thread registration. For marketplace updates, update the installed skill through Codex's plugin manager, then rerun profiles-only bootstrap; rerunning that bootstrap alone does **not** update the plugin's skill copy. If your Codex version does not expose the plugin commands, use the direct install rather than editing unrelated global configuration.

Codex's skill-picker label is `AMS`; the canonical skill name remains `adaptive-master-subagent-orchestration`. Select its entry after typing `$`, rather than assuming `$AMS` is a registered alias. User-disabled skills stay disabled across reinstalls. The plugin manifest version is bumped for refreshed metadata; it is not an AMS runtime-policy version.

## Authenticated downloads

Public downloads use `raw.githubusercontent.com` without authentication first. This avoids spending GitHub Contents API requests on each ordinary public file. Only after an access error does the helper try optional credentials from `GH_TOKEN`, `GITHUB_TOKEN`, or an existing GitHub CLI login and use the Contents API. Public downloads do not depend on a valid stored token when raw access succeeds.

For access-controlled downloads or an API limit, sign in using [GitHub CLI](https://cli.github.com/manual/gh_auth_login) and use the authenticated command in [Installation](INSTALLATION.md#download-problems). The Bash equivalent checks the download before executing it:

```bash
ams=$(gh api -H 'Accept: application/vnd.github.raw+json' 'repos/InsecurePassword/Codex-AMS/contents/tools/install_harnesses.py?ref=main') && printf '%s\n' "$ams" | python3 - --harness all --install-pi-subagents
```

A GitHub token in the environment authenticates the helper's subsequent downloads; it does not automatically authenticate a plain `curl` or `Invoke-RestMethod` download of the helper itself. Use the GitHub CLI bootstrap when the helper also needs authenticated access. Never put credentials in a URL or committed file.

## Installation integrity and recovery

Remote staging validates manifest paths, the downloaded core lengths/hashes, and an unchanged manifest re-read before handing off to the native installer. The native transaction validates its exact core membership and uses the existing install lock, staging, backup, and rollback behavior. Matching hashes establish consistency with the fetched manifest, not independent publisher signing.

Codex profiles are replaced only when absent, byte-identical, or an exact recognized official predecessor. Custom, unknown, or redirected targets block replacement. OpenCode/Pi generated files are create-only or byte-identical: **this build does not automatically upgrade a differing native Markdown preset**, even if it has the AMS marker. Reconcile it deliberately. Rollback of newly created native Markdown agents checks identity and bytes before removal.

Settings are not migrated by installation. Project/global settings updates are agent-directed writes through the skill's commands. No installer adds model governance to profiles or rewrites them when a policy switch changes.

The core installer can recover a stable same-host dead-owner lock older than its 30-second grace period, or an old empty ownerless lock. It rejects live, young, malformed, foreign-host, or changing locks. Run installations sequentially; do not delete another installer's lock. These are package transaction locks, not an AMS runtime convergence subsystem.

When a complete trusted package is already available, run from its root for offline source recovery:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Local
```

```bash
bash ./install.sh --local
```

The local native installers default to Codex. Native multi-harness wrappers are described above. Normal users should keep using the remote commands; recovery mode is not a requirement to download a ZIP first.

## Optional companions and transport limits

The core installer does not install any directory under `extensions/`. For deliberate separate deployment, copy the **complete** desired companion directory from a trusted matching source snapshot into `~/.agents/skills/`, retaining its directory name, then restart Codex. Do not copy only `SKILL.md` or mix helper/reference files from different snapshots. A replacement should preserve any user changes for review.

| Companion | Purpose and limitation |
|---|---|
| [Local OpenAI lane](extensions/ams-local-openai-lane/README.md) | One selected local-model task at a time with Codex verification; not OpenCode/Pi provider configuration. |
| [App-task lane](extensions/ams-app-task-lane/README.md) | Explicit user-visible Codex app-task transport when the required tools are actually available; not a second orchestrator. |
| [Runtime observation](extensions/ams-runtime-observation/README.md) | Explicit inspection of allowlisted local Codex session metadata; not private reasoning or a model-selection tool. |

Companion `agents/openai.yaml` metadata disables implicit invocation for Codex. The skill bodies also require explicit gates. Do not assume another harness interprets Codex-specific metadata or has equivalent tools. The current multi-harness installer does not port Daybreak, app tasks, or runtime observation; it does not qualify the local-lane companion for another harness.

OpenCode uses native `task`; Pi uses the separately installed `pi-subagents` extension. Reuse actual returned identities for follow-up. Direct peer transport is conditional on exposed tools; otherwise root relays. The core autonomy, ownership, and supervisory obligations remain, but tool names and identity formats are harness-specific. Pi's upstream background execution requires its npm installation; standalone Pi builds can use supported foreground execution. Consult the installed extension's guide/doctor rather than assuming every transport is available.

## Uninstall and downgrade

Send `AMS DISABLE` in the affected project and let active work reach a safe boundary before removing files. The installer has no uninstall flag. Disabling AMS is not uninstallation and is not emergency process termination.

For a marketplace-managed Codex copy, use `codex plugin remove Codex-AMS@Codex-AMS` or Codex's plugin manager. This does not remove a separately direct-installed shared skill or your agent/settings files.

For a direct install, explicitly remove only the known AMS skill directory under the chosen skill home. The default shared location is used by multiple harnesses; removing it can affect all of them. Keep installed presets and project/global settings unless separately authorized to remove them. Never remove an entire `.agents`, `.codex`, `.pi`, or OpenCode directory as an AMS uninstall.

Pi's subagent dependency may serve other workflows. Remove it only through Pi's own package manager and only when independently intended. It is not automatically removed with AMS.

Before downgrade, back up complete current settings and prepare a separate older-compatible settings file. Preserve the current file; no AMS runtime-state export is needed. Do not claim an older installer will accept newer profile bytes without checking its predecessor rules.

## Verification and evidence limits

[The verification workflow](.github/workflows/verify.yml) defines the maintained commands and platform matrix. It compiles Python, checks core membership and profiles, exercises configuration/orchestration contract fixtures, companion helpers, context budgets, native installers, and multi-harness installer fixtures. Public remote-source checks are conditional workflow steps. Native Codex discovery checks query the actual `skills/list` registry after separate standalone and plugin installations, without starting a model turn. Inspect the checks for the exact commit you plan to use; this document is not a permanent claim that every future build passes.

The contract tests combine simulated behavior with textual assertions; they do not run an AI model through every scenario. OpenCode/Pi catalog and package-manager fixtures do not prove live account access, effective reasoning effort, direct peer support, or long-duration autonomous behavior. Native installer tests exercise the real filesystem/scripts; Codex registry checks are not a visual test of a user's particular app window. End-to-end model/computer-use qualification remains distinct from a green installer job.

`tools/measure_context.py --check` measures authored UTF-8 bytes with approximate token estimates. Use `--model-policies off` to compare the disabled-policy path. The historical context and manifest baselines are comparison fixtures, not the current settings schema or extra live profiles. They do not measure billed reasoning tokens or prove total-task cost reduction.

## Upstream references

- [OpenAI skills](https://developers.openai.com/codex/skills) and [plugins](https://developers.openai.com/codex/plugins)
- [OpenCode skills](https://opencode.ai/docs/skills) and [agents](https://opencode.ai/docs/agents)
- [Pi skills](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md)
- [Pi subagents](https://github.com/nicobailon/pi-subagents)
- [GitHub CLI API commands](https://cli.github.com/manual/gh_api)

Upstream products change independently of AMS. Confirm installed tool schemas and availability; do not infer capabilities solely from a profile filename or example.
