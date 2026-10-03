# AMS profile management

Use only when a selected profile is missing, unregistered, mismatched, or explicitly being installed or repaired. Direct install deploys 36 profiles; marketplace install needs profiles-only bootstrap before a new thread.

Outside Codex, use `harness-compatibility.md` for native registries and preset installation; the Codex-specific file operations below do not apply. Assignment and authority boundaries still apply.

## Registry and routes

Prefer `$CODEX_HOME/agents/`, otherwise `$HOME/.codex/agents/`. Use `<project-root>/.codex/agents/` only for deliberate isolation, authoritative project policy, or unavailable global profiles.

```text
ams_<sol|luna|astra>_<low|medium|high|xhigh|max>
ams_<sol_6_0|sol_5_6|terra|luna_5_6>_<low|medium|high|xhigh|max>
ams_daybreak_blue_max
```

A profile requests a route; it does not prove availability, authorization, provisioning, or observed identity.

## Contract

Exact bundled bytes define the name, model/effort, and conditional task-purpose instructions. Explicit assignments govern; purpose defaults never restrict other tasks or initiate reviews. Ordinary descriptions identify routes only; they contain no model-purpose advice. Profiles are permission-neutral: no sandbox, approval, network, writable-root, credential, authorization, target, or tool override.

Root supplies role, supervision, and communication in each assignment from `runtime-core.md`, adding enabled governance when needed. Profiles reinforce child authority and execution quality, not selection eligibility. Changing policy switches never rewrites installed profiles. Ordinary profiles may be workers or managers; Daybreak is worker-only. Daybreak retains its specialized access contract. Peer communication remains available with model governance off; enabled governance adds the bounded-channel protocol.

Before spawn, verify the selected effective regular file matches its expected name, model/effort, managed contract, and permission neutrality. Requested identity is not observed identity. Daybreak remains governed only by `daybreak-blue.md`; profile presence proves nothing.

## Operations

Require registry containment, regular non-redirected files, bounded stable UTF-8/LF, no case/normalization collision, one writer, staged replacement, backup, and post-write verification.

`profile_management = "auto"` may create only a selected missing profile from exact bundled bytes after proving the target absent/unclaimed. It never replaces a differing file. A newly created role is usable only when the platform confirms current-thread registration; otherwise use a new thread or block without retrying spawn. `installer` reports the missing route. Use a truthful eligible loaded alternative only when no explicit selection prevents it; legacy routes require user selection and Daybreak has no substitute. Profile or unit/parent relabeling does not reopen a closed boundary; a distinct provisioned surface needs its own evidence.

Replace an existing differing profile only during direct user-authorized install/repair and only when it exactly matches a recognized official predecessor. Preserve customized, malformed, ambiguous, redirected, or user-authored files for user reconciliation.
