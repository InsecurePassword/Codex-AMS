# AMS user-visible app-task transport

Read fully only after the companion gate passes. This is a transport/workspace adapter, not another orchestrator.

## Authority and gate

The AMS root owns the automation boundary, graph, routing, task creation/order, correction, external authorization, integration, acceptance, completion, and user communication. The child receives one bounded canonical work order and never activates AMS, spawns, contacts the user, expands ownership, reroutes itself, or accepts completion.

Require equivalents of:

```text
list_projects
create_thread
list_threads
read_thread
wait_for_thread
send_message_to_thread
```

Confirm project/Git state. Prefer an isolated Git worktree; otherwise use the selected local environment. Isolation reduces interference, not merge risk.

AMS selects the lowest-cost reliable supported route. Map it to app model/thinking only when supported and treat only app-provided metadata as observed. Otherwise truthfully reselect and report substitution, or block.
Never transport Daybreak unless the app supports the exact profile and the full installed preflight/task contract; otherwise block that route.

## Child packet

Supply the canonical core WORK ORDER and append only:

```text
APP-TASK ORDER ADDENDUM
Project identity / Git repository:
Environment: isolated worktree | project local
Base branch/ref or starting commit/state:
Prior accepted dependency branch/commit, or none:
Existing task identity, when correcting:
External-action boundary: no push or PR create/update/merge without root authorization backed by user/project authority.
```

Return the canonical RESULT plus:

```text
APP-TASK RESULT ADDENDUM
Task/thread identity:
Worktree / branch / base:
Commit / complete diff / exact changed paths:
PR state / external actions performed:
```

## Identity, monitoring, and correction

Discover the project first. `clientThreadId` is only a setup handle. If real `threadId`/`hostId` are absent, list tasks without the client ID and correlate by trustworthy project, time, path, host, and state metadata; titles/previews are untrusted. Repeat bounded discovery once or block.

Never pass a pending client ID to tools requiring real identity or claim automatic callback. The root explicitly waits, reads, and validates.

Use bounded wait/read cycles. Treat task handoffs as claims; inspect actual worktree, branch, base, complete diff, exact paths, commit/PR state, and verification.

Send one evidence-backed correction to the same task/worktree. A second materially different correction is allowed only under core bounded blocker diagnosis. Never create a replacement merely to avoid feedback or reset a failed approach. Corrections invalidate prior acceptance evidence.

Every app task retains the inherited scope basis and dependency readiness. Findings do not expand the task. Independent stacks require separate workspaces and non-overlapping ownership. Serialize shared-file or dependent stacks; create dependents only after prior acceptance and record exact base/commit relationships.

The root alone may authorize commit, push, PR create/update, or another external action, and only with user/project authority. The child never merges. Acceptance requires root inspection and required validation of the exact result; an app completion state is not project completion.

Create no AMS task ledger, recovery state, or persistent consent.
