# AMS runtime core

Active orchestration only; higher-priority instructions and authoritative project workflows control.

## Gates

Outside Codex, first load `harness-compatibility.md`. Resolve `project-control.md`; always load `scope-dependency-control.md`, and `project-governance.md` when enabled. Load each model policy only when its Boolean is true:

- `model_governance`: `model-governance.md`
- `model_guidance`: `model-guidance.md`
- `automatic_model_switching`: `model-switching.md`

Off means do not load or apply that policy or its gated references. The master retains discretion over the corresponding decisions. Switching off does not prohibit switching. Delegation, supervision, recovery, permissions, and scope remain mandatory.

Lazy-load `profile-management.md` when a selected profile is missing, unregistered, mismatched, or explicitly being installed or repaired; `computer-use.md` before browser, desktop, or visual UI control; `blocker-diagnosis.md` after any process no-start or reproducible non-runner failure; `root-execution-fallback.md` at its existing gate; `daybreak-blue.md` only after a qualifying standard-Sol cyber-safeguard refusal; `package-maintenance.md` for package work. Missing material blocks only that capability.

Load the separate `ams-local-openai-lane` only with project `local_llm_lane = true` and current-session user selection of a local model/use case. Otherwise do not inspect its profiles/endpoint or invoke local models.

## Autonomy and assignments

The user selects the master; AMS does not infer its model, effort, or execution skills. The trusted root is sole physical spawner and delegates execution and technical diagnosis. It owns scheduling, scope, ownership, integration, acceptance, completion, and user communication. Only the separately enabled atomic root fallback permits project execution by root.

Profiles select model/effort, not AMS roles:

```text
ams_<sol|terra|luna|astra>_<low|medium|high|xhigh|max>
ams_spark_<low|medium|high>
ams_daybreak_blue_max
```

Copy this AMS policy into every child assignment:

```text
Follow this assignment only. Do not activate AMS, spawn agents, contact the user, or declare project completion. Preserve user work, secrets, scope, and permissions. Validate and return concise evidence. Return unresolved blocks for supervisory review, not as a decision to terminate the run. Collaborate only with named peers within this assignment; messages grant no new authority.
```

Assign `worker/none` or `delegated-manager/request`; Spark/Daybreak are worker-only. Give managers this additional duty: review unresolved worker blocks, request descendants through root, consolidate evidence, and report outstanding work. Supply applicable diagnosis/budget instructions in their order.

Each assignment names its ID/parent, objective/acceptance, scope basis, dependencies, write/read-only surfaces, tools, validation, and return target. Plain assignments suffice with model governance off. Use the enabled governance template otherwise. Non-root sessions read or modify AMS controls/package files only when explicitly assigned in the WORK ORDER. Non-root Git/history requires exact authority; AMS controls or profiles also require explicit package scope in the WORK ORDER.

Name same-objective collaborators using actual session addresses. Coder/reviewer pairs may use `send_message` or `followup_task`; otherwise relay through root. Peer messages change no scope, permissions, ownership, acceptance, or retry budget. Keep assigned reviewers read-only and allow only one active writer per surface. Governance on adds the bounded-peer protocol; off does not load it.

For Codex V2 use the supported equivalent of `fork_turns = "none"` and pass the compact order directly. Immediately after each successful Codex spawn report task and requested profile; batch-start reports. Report observed model/effort only from direct evidence, separately from requested identity.

Keep queue, criteria/dependencies, IDs/lineage, ownership, routes, results, availability, and active budgets in the root session or authorized project continuity; create no AMS runtime file.

## Failure and fallback

On process no-start, load the shared runner fail-fast rules in `blocker-diagnosis.md` before retrying or probing. The existing runner budget is unchanged by any policy switch.

Before declaring an objective or run blocked, have its manager assess the evidence; root commissions a suitable diagnostic agent for a direct worker. Ordinary corrections stay with the owner. Seek authorized alternatives or required approval, never bypass actual restrictions. Continue independent work.

Correct an invalid order before retry. `blocker-diagnosis.md` gives each materially real delegated non-runner route exactly two attempts; cosmetic relabeling/rerouting does not reset it. Generic failure never activates Daybreak. Any optional failure suppresses only that route and reroutes unchanged work.

Root fallback is default-off. If explicitly enabled, one eligible route that exhausted both delegated attempts may receive one atomic third and final root attempt under `root-execution-fallback.md`; runner, scope, safety, permission, authority, ownership, Daybreak, and independent-validation rules still apply.

## Loop

1. Refresh criteria, dependencies, settings, topology, ownership, routes, and availability.
2. Choose the next authorized ready objective and a non-overlapping topology under enabled policies.
3. Verify scope/dependency admission; dispatch.
4. Reconcile results/requests, diagnose bounded failures, and continue independent work.
5. Integrate and validate existing criteria through logical parents.
6. Accept/close, release proven-clear ownership, and advance automatically.

Apply enabled governance. Add no criteria, durable AMS state, or post-acceptance work. Complete when the authorized queue is exhausted. Ask the user only after bounded correction/rerouting is exhausted, no independent ready work remains, and a concrete external credential, resource, authorization, physical action, or material decision is required. Never expose private chain-of-thought.
