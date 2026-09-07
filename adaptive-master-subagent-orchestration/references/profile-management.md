# AMS profile management

Use only when a selected profile is missing, unregistered, mismatched, or explicitly being installed or repaired. Direct install deploys 24 profiles; marketplace install needs profiles-only bootstrap before a new thread.

## Registry and routes

Prefer `$CODEX_HOME/agents/`, otherwise `$HOME/.codex/agents/`. Use `<project-root>/.codex/agents/` only for deliberate isolation, authoritative project policy, or unavailable global profiles.

```text
ams_<sol|terra|luna|astra>_<low|medium|high|xhigh|max>
ams_spark_<low|medium|high>
ams_daybreak_blue_max
```

A profile requests a route; it does not prove availability, authorization, provisioning, or observed identity.

## Contract

Exact bundled bytes define the name, model/effort, instructions, and V2 mode hint. Profiles are permission-neutral: no sandbox, approval, network, writable-root, credential, authorization, target, or tool override.

Sol, Terra, Luna, and Astra profiles act only as the assigned `worker/none` or `delegated-manager/request`; Spark and Daybreak accept only `worker/none`. Root alone spawns. Workers are leaves; managers return bounded root-mediated dispatch requests within granted scope and allocation. Peer messaging is limited to the named `worker/none` paths in one matching channel and changes no order or authority; the member returns a terminal stub, the lead returns synthesis, and root retains acceptance. All profiles preserve scope, dependencies, ownership, permissions, validation, user work, root-only user contact, and root-only completion.

For Codex V2 use the supported equivalent of `fork_turns = "none"` and pass the compact order directly. Before spawn, verify the selected effective regular file matches its expected name, model/effort, managed contract, and permission neutrality. Requested identity is not observed identity. Daybreak remains governed only by `daybreak-blue.md`; profile presence proves nothing.

## Operations

Require registry containment, regular non-redirected files, bounded stable UTF-8/LF, no case/normalization collision, one writer, staged replacement, backup, and post-write verification.

`profile_management = "auto"` may create only a selected missing profile from exact bundled bytes after proving the target absent/unclaimed. It never replaces a differing file. A newly created role is usable only when the platform confirms current-thread registration; otherwise use a new thread or block without retrying spawn. `installer` reports the missing route. Use a truthful loaded alternative when suitable; Daybreak has no substitute. Profile or unit/parent relabeling does not reopen a closed boundary; a distinct provisioned surface needs its own evidence.

Replace an existing differing profile only during direct user-authorized install/repair and only when it exactly matches a recognized official predecessor. Preserve customized, malformed, ambiguous, redirected, or user-authored files for user reconciliation.
