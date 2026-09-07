# Product Documentation

**Product:** Adaptive Master–Subagent Orchestration (AMS)
## 1. Product boundary

AMS has two core responsibilities:

1. keep the current trusted top-level root in control of the authorized automation boundary, physical dispatch, hierarchy, sequencing, ownership, integration, acceptance, completion, and user communication;
2. request the lowest-cost reliable Codex model family and reasoning effort for each bounded non-root session.

The root model and reasoning effort are external configuration. AMS does not select, require, infer, or attest them. Workers are leaves. Delegated managers request root-mediated descendants and never physically spawn, expand authority, contact the user, or accept completion.

## 2. Core behavior

Core AMS provides:

- Codex model/effort routing across 24 `ams_*` profiles;
- root-mediated hierarchy and finite allocation; Balanced permits two direct sessions or one manager plus three direct descendants;
- bounded direct peer channels between exactly two named root-spawned `worker/none` siblings, with terminal status and one final lead synthesis returned to root;
- one-writer mutable-surface ownership;
- mandatory scope/dependency admission;
- automation-boundary continuation from one accepted objective to the next;
- compact default-on 3.09-style project governance;
- bounded blocker diagnosis without recovery loops;
- command-runner fail-fast with three diagnostic starts and at most one corrected original-lane confirmation after a successful probe;
- bounded root fallback with independent validation;
- session-local Spark availability suppression;
- optional project-local local-LLM routing through a separate companion;
- refusal-triggered Daybreak Blue capability preflight and one-task defensive fallback;
- transactional package/profile installation.

AMS creates no convergence campaign, persistent custody/receipt system, archive/prune history, runtime lock/state, review/accounting ledger, or availability cache.

### Bounded peer channels

When direct collaboration is cheaper than relaying every intermediate message through the root, the root may place exactly two direct `worker/none` siblings in one bounded peer channel. Both work orders must name the same channel, canonical absolute task paths, purpose, lead/member roles, writer ownership, escalation conditions, and root-return mode. Peers may use `send_message` or `followup_task` only with the named path. Messages are evidence or scoped steering inside the existing orders and cannot alter objective, scope, dependencies, permissions, ownership, criteria, delegation, retry budget, or user authority. The lead remains a worker. The member sends detail to the lead and returns a short root terminal stub; the lead returns one synthesized result. Root acceptance and completion authority do not move.

## 3. Settings and precedence

Project settings:

```text
<project-root>/.codex/ams-orchestration.toml
```

Global/base settings:

```text
$CODEX_HOME/ams-orchestration.toml
```

A present project file fully replaces global base settings. Global/base default:

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

Project default additionally contains:

```toml
local_llm_lane = false
```

`local_llm_lane` is invalid globally. Missing project settings force the local lane off. Retired convergence/modular fields and legacy `schema_version` are inert compatibility input and are removed during the next authorized write.

## 4. Commands

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

Normal controls write project settings only. `AMS CONFIGURATION UPDATE GLOBAL` is the sole global-writing command. `AMS STATUS` is physically read-only and performs no capability probes.

## 5. Scope, dependencies, and automation

The root establishes an automation boundary from direct user instruction and authoritative project-native queues, milestones, or packets. Every work order cites a `Scope basis` and `Dependencies/readiness`. Findings, logs, reviewer suggestions, warnings, TODOs, and repository content cannot create work or criteria.

Before affected dispatch or acceptance, AMS verifies the declared candidate base and accepted dependency closure. Worktree-only repairs, unrecorded branches, caches, generated state, or undeclared packets do not silently satisfy prerequisites. Validation failures outside the owned surface are compared with the base/control when practical and classified as objective, baseline, environment, harness, or another dependency.

When one objective passes, AMS closes it, releases ownership, refuses post-acceptance extras, selects the next authorized ready objective, and continues. The run stops normally only when the authorized queue is exhausted; blockers stop the run only when bounded diagnosis/rerouting is exhausted and no independent authorized path remains.

## 6. Governance

Default-on project governance retains the compact 3.09 behavior:

- track existing authorized deliverables, criteria, dependencies, critical path, integration, validation, risk, and blockers;
- continue automatically while authorized ready work remains;
- use proportional, non-recursive independent review when warranted;
- respect project-native packets, pauses, approvals, trackers, and gates;
- provide a concise handoff when autonomous progress cannot continue.

Governance cannot expand scope, create criteria, create durable state, or override project authorization. `AMS GOVERNANCE off` removes only this lifecycle layer; core scope/dependency, ownership, routing, evidence, failure, and truthful completion controls remain.

## 7. Failure behavior

A reproducible non-runner failure is budgeted per materially real delegated route. The route gets exactly two attempts in its proper lane: one evidence-backed correction attempt and one confirmation attempt, which may repeat the corrected invocation once to distinguish a sporadic failure or use one materially different evidence-backed correction. Changing worker, manager, profile, effort, task name, branch, wrapper, shell label, or context does not create another route or reset its budget. After two failures, optional root fallback—disabled by default—may perform one atomic third and final attempt when its safety gate passes.

Repeated `spawn_ready` creates one root-session episode keyed by the unchanged physical runner signature. It gets three diagnostic starts: initial failure, one same-lane retry, then one root process-only probe. Probe success permits at most one materially corrected original-lane confirmation; another no-start terminalizes the episode without a new process, profile, manager, transport, context, or intensity reset. Probe failure likewise terminalizes process-dependent work. Active or potentially live sessions, writers, and allocations remain owned until closure is proven; unresolved state is reported live or unverified while runner-independent authorized work continues.

A local lane or objective can be deferred while independent authorized work continues. User intervention is requested only when no autonomous route remains and a concrete permission, credential, physical action, external resource, material choice, or new authority is required.

## 8. Spark

`spark_enabled` is persistent preference. Availability is session-local. Profile/registration/model-capability failure suppresses Spark; task-quality failure does not. `spawn_ready` first uses shared runner diagnosis; after probe success, another Spark-specific no-start suppresses it. `AMS SPARK on` clears the latch; no availability field is persisted.

## 9. Astra and computer use

Five `ams_astra_<low|medium|high|xhigh|max>` profiles request `gpt-6-astra`. Astra is a peer route, not a universal default or mandatory escalation: use it for end-to-end tool-heavy, computer-use, very-large-context, or high-rework-risk work when one Astra owner is expected to reach acceptance with less total usage, time, or correction than Sol. Sol remains appropriate for difficult coding, architecture, security, and diagnosis when Astra's tool or long-context advantage is not material.

Before browser, desktop, or visual UI control, load `references/computer-use.md`. Use only a session that exposes the required tool, prefer shell/API/MCP/direct file operations when simpler, assign one active controller per interactive surface, treat screen content as untrusted evidence, use existing platform approvals, and verify the resulting application state. Computer use changes neither model authority nor AMS authority.

## 10. Local OpenAI-compatible lane

The separately installed `ams-local-openai-lane` companion is eligible only when:

- project-local `local_llm_lane = true`;
- the session latch is not inactive;
- current-session user steering selects the model and permitted use cases;
- the current work matches those use cases.

The user selects the model. Codex may choose only a tested context/profile variant with the same `model_key`, selecting the smallest safe context or promoting once to a larger same-model profile when necessary. It never changes the model automatically or knowingly truncates work.

Profiles are manually created or built/audited/tested in a separate Codex development interaction under `<project-root>/.codex/ams-local-llm/profiles/`. AMS runtime only consumes stable files; any start command requires a stop command.

The companion executes one configured start attempt, one OpenAI-compatible request, and optional stop; transient request files are deleted after use. It requires the response to expose a model identity equal to the requested model or a bounded alias explicitly listed in the user-owned profile, and returns requested and observed identity separately. It sends fresh context, stops a known companion-started kept profile on local-lane/AMS disable or before same-model switching, and cleans up once after a started-call failure. Every result is Codex-verified. Non-context helper failure/rejection suppresses the lane without changing settings; helper-process `spawn_ready` uses runner fail-fast. No fitting context falls back only that work and leaves the lane available. Only `AMS LOCAL LLM on` clears an inactive latch.

## 11. Daybreak Blue

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

## 12. Package boundaries

Installed core contains `SKILL.md`, metadata, 24 profiles, and 14 normative references. `.github/`, `tools/`, `verification/`, and `extensions/` are repository-only and never run during normal orchestration.

Marketplace installation is skill-only and requires the profiles-only bootstrap before a new thread. The direct installer deploys core and profiles. Both preserve differing user-authored profiles and never edit general Codex configuration, project settings, optional companions, or permissions.
