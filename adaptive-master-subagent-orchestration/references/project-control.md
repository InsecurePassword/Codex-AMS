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
root_execution_fallback = false
spark_enabled = true
spark_efforts = ["low", "medium", "high"]
profile_management = "auto"
```

Project default adds one project-only field:

```toml
local_llm_lane = false
```

Missing fields use defaults until write. Intensity is `auto|minimal|moderate|heavy|extreme|zergling-rush` (`balanced` stores `moderate`); Spark efforts are a unique ordered subset of `low,medium,high`; profiles are `auto|installer`. Stored Rush is not consent. Local LLM is invalid globally and false without project settings.

The defaults above are the complete current schema. If another field appears, load `configuration-maintenance.md`: it alone defines retired compatibility input; reject anything else. Retired fields never affect behavior and are removed on the next authorized write.

## Commands

```text
AMS STATUS
AMS ENABLE | AMS DISABLE
AMS MODE auto|minimal|balanced|moderate|heavy|extreme
AMS IMPLICIT on|off
AMS GOVERNANCE on|off
AMS ROOT FALLBACK on|off
AMS CONFIGURATION UPDATE [PROJECT|GLOBAL]
AMS SPARK on|off
AMS SPARK EFFORTS low,medium,high
AMS PROFILES auto|installer
AMS LOCAL LLM on|off
```

Status probes nothing and reports source/validity, activation/intensity, governance/fallback, profile policy, Spark/local preference and session availability, boundary, and blockers. Other commands change only the named project field while preserving current values, adding defaults, and dropping retired fields; mode also enables AMS. Only explicit global update writes global. New project settings copy effective base, add local false, then apply the requested change. Configuration update loads `configuration-maintenance.md`.

Apply at a safe wave boundary unless explicitly immediate. Disable stops new dispatch, lets atomic work finish, collects evidence, closes incompatible sessions, writes false, and creates no terminal record. Local on clears its session latch but selects no model. Local off or AMS disable makes one no-retry/probe `--stop-only` call only for a known companion-started kept model; never stop a preexisting model, and cleanup failure cannot veto the setting.

## Availability and continuity

Spark/local state is session-only `unknown|available|inactive-after-failure`. Companion/profile, registration, capability, identity, helper, or start failure suppresses only that route; normal task-quality failure does not suppress Spark. No-start follows `runtime-core.md`; another no-start after a successful probe suppresses the route. The corresponding on-command clears the latch. Local context-too-small permits one tested same-`model_key` promotion, then reroutes only that work to Codex. Saved preference remains unchanged. Daybreak has no setting or proactive probe.

Keep graph, scope/dependencies, lineage, ownership, routing, and availability in session or authorized project-native continuity; create no AMS task/history/cache/memory file. Recovery inspects live state, preserves lineage, reclaims only proven-clear ownership, and resumes the earliest unfinished/unverified dependency. File-only changes require trusted provenance or direct user intent.
