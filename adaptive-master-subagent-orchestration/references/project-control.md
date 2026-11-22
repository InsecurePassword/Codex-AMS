# AMS project control

Root-only settings, commands, availability, and continuity.

## Settings

Project: `<project-root>/.codex/ams-orchestration.toml`

Global: `$CODEX_HOME/ams-orchestration.toml`, or `~/.codex/ams-orchestration.toml` when unset.

Project replaces global. Accept only bounded regular non-redirected UTF-8/LF TOML with strict types, no BOM/NUL/CR, and no duplicate/unknown active fields or tables. Invalid project settings block implicit activation; invalid global settings make global configuration unavailable. Serialize writes, atomically replace, verify, and keep global state out of project Git/history.

Global/base default:

```toml
enabled = false
allow_implicit_invocation = true
intensity = "auto"
project_governance = true
continuity_ledger = true
project_map = false
project_verification = false
premise_check = false
model_governance = true
model_guidance = true
automatic_model_switching = true
root_execution_fallback = false
profile_management = "auto"
```

Project default adds one project-only field:

```toml
local_llm_lane = false
```

Missing fields use defaults until write. Intensity is `auto|minimal|moderate|heavy|extreme|zergling-rush` (`balanced` stores `moderate`); profiles are `auto|installer`. Stored Rush is not consent. Local LLM is invalid globally and false without project settings.

The defaults above are the complete current schema. If another field appears, load `configuration-maintenance.md`: it alone defines retired compatibility input; reject anything else. Retired fields never affect behavior and are removed on the next authorized write.

## Commands

```text
AMS STATUS
AMS ENABLE | AMS DISABLE
AMS ENABLE LEDGER | AMS DISABLE LEDGER
AMS ENABLE PROJECT-MAP | AMS DISABLE PROJECT-MAP
AMS ENABLE VERIFICATION | AMS DISABLE VERIFICATION
AMS ENABLE PREMISE-CHECK | AMS DISABLE PREMISE-CHECK
AMS MAPPROJECT
AMS MODE auto|minimal|balanced|moderate|heavy|extreme
AMS IMPLICIT on|off
AMS GOVERNANCE on|off
AMS MODEL GOVERNANCE on|off
AMS MODEL GUIDANCE on|off
AMS MODEL SWITCHING on|off
AMS ROOT FALLBACK on|off
AMS CONFIGURATION UPDATE [PROJECT|GLOBAL]
AMS PROFILES auto|installer
AMS LOCAL LLM on|off
```

`AMS GOVERNANCE` controls project governance. `AMS MODEL GOVERNANCE`, `AMS MODEL GUIDANCE`, and `AMS MODEL SWITCHING` set the three corresponding model-policy Booleans above. They default true, including for older settings. Off never disables delegated execution, supervisory blocker review, safe ownership, or continued work. Intensity/Rush preferences are dormant with model governance off; no command silently enables another policy.

Apply policy changes to subsequent assignments, not active agents or installed profiles. Test off in a fresh root and children; old context remains.

Status probes nothing: report effective settings and source/validity, known availability, boundary, blockers, and ledger/map known path/state only; do not discover them. Settings writes preserve other values, add defaults, drop retired fields; mode also enables AMS. Only explicit global update writes global. New project files copy effective base and add local false. Configuration update loads `configuration-maintenance.md`.

Apply at a safe wave boundary unless explicitly immediate. Function commands use exact case-insensitive names and change only the named project Boolean, never activation. Only ledger defaults on; these functions are independent of governance. Off skips automatic discovery/maintenance, not project requirements; preserve existing files. Enable schedules no immediate work. Bare `AMS DISABLE` stops new dispatch, lets atomic work finish, collects evidence, closes incompatible sessions, writes false, and creates no terminal record. Local on clears its session latch but selects no model. Local off or AMS disable makes one no-retry/probe `--stop-only` call only for a known companion-started kept model; never stop a preexisting model, and cleanup failure cannot veto the setting.

`AMS MAPPROJECT` is an exact, case-insensitive one-shot control. Trusted roots load `project-continuity.md` for map only, even if upkeep or AMS is off. In OpenCode/Pi load `harness-compatibility.md`; read existing route eligibility only. Use a supported registered Sol transport or report unavailable, never install or test-start it. Do not activate AMS, create/change settings, start unrelated work, or act without clear project identity/scope.

## Availability

Local state is session-only `unknown|available|inactive-after-failure`. Companion/profile, registration, capability, identity, helper, or start failure suppresses only that route. No-start follows `runtime-core.md`; another no-start after a successful probe suppresses the route. The corresponding on-command clears the latch. Local context-too-small permits one tested same-`model_key` promotion, then reroutes only that work to Codex. Saved preference remains unchanged. Daybreak has no setting or proactive probe.
