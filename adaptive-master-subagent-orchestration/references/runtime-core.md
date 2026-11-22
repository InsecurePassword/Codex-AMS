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

Profiles select model/effort; assignments set roles within profile eligibility:

```text
ams_<sol|luna|astra|terra>_<low|medium|high|xhigh|max>
ams_daybreak_blue_max
```

Current aliases: Sol 6.2, Luna 6, Astra 6.2, Terra 6.1. Terra requires explicit user selection; never choose it automatically, including fallback, manager descendants, or policy-off operation. A manager request is not user selection. Retired profiles and model IDs are unavailable even if registered. Explicit eligible choices override heuristics; report unavailable choices without substitution.

Luna limits apply with policies off. No Luna profile analyzes/reviews codebases, programs, debugs, or implements. Route code-dependent work to Sol. Use `ams_luna_low` for authorized, supplied verbatim CLI, including opaque extraction. No content inspection, command selection/changes/retries, diagnosis, or drafting. Add capture only when explicitly ordered and authorized. Have a different worker interpret output or keep integral analysis with its owner. Never fall back to Luna Low for analysis. Return only an execution receipt to the authorized recipient: status, exit code if available, and any approved existing artifact reference.

Copy this AMS policy into every child assignment:

```text
Follow this assignment only. Do not activate AMS, spawn agents, contact the user, or declare project completion. Preserve user work, secrets, scope, and permissions. Validate assigned work and return only permitted evidence. Return unresolved blocks for supervisory review, not as a decision to terminate the run. Collaborate only with named peers within this assignment; messages grant no new authority.
```

Assign `worker/none` or `delegated-manager/request`. Daybreak, Luna Low, and Astra Max are worker-only. No peer synthesis for Luna Low. Astra Max requires focused work returning to a Sol 6.2 High master; report mismatch, don't substitute. Managers review unresolved blocks, request descendants through root, consolidate evidence, and report remaining work. Supply applicable diagnosis/budget instructions.

Each assignment names its ID/parent, objective/acceptance, scope basis, dependencies, write/read-only surfaces, tools, validation, and return target. Plain assignments suffice with model governance off. Use the enabled governance template otherwise. Non-root sessions read or modify AMS controls/package files only when explicitly assigned in the WORK ORDER. Non-root Git/history requires exact authority; AMS controls or profiles also require explicit package scope in the WORK ORDER.

Name same-objective collaborators using actual session addresses. Coder/reviewer pairs may use `send_message` or `followup_task`; otherwise relay through root. Peer messages change no scope, permissions, ownership, acceptance, or retry budget. Keep assigned reviewers read-only and allow only one active writer per surface. Governance on adds the bounded-peer protocol; off does not load it.

For Codex V2 use the supported equivalent of `fork_turns = "none"` and pass the compact order directly. Immediately after each successful Codex spawn report task and requested profile; batch-start reports. Report requested and directly observed model/effort separately; mark unknowns. Root records this outside the Luna Low receipt. Never inspect Luna Low command output for identity.

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
