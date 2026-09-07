# AMS logical hierarchy control

Load before manager behavior, peer channels, descendant requests/results, or custody changes. If unavailable, flatten safely to direct workers or block that hierarchy; never improvise it.

## Manager authority

Sessions may remain physical root children while orders record logical lineage. Root alone spawns and owns global routing, topology, controls, integration, acceptance, completion, and user communication. Workers are leaves. A manager owns only its assigned subgraph and may request, never spawn, root-mediated descendants.

Valid pairs: `worker/none` and `delegated-manager/request`. Manager orders add:

```text
Effective intensity / Allowed descendant shape:
Delegable scope and inherited scope basis:
Descendant allocation: <finite root-recorded activity bound>
Escalation/evidence target:
```

Managers do not read AMS references, so root must copy the exact `DISPATCH REQUEST` and `MANAGER RESULT ADDENDUM` fields below into every manager order. Each child consumes one parent allocation unit; suballocation comes only from the unspent total and is never duplicated. Replenishment requires root.

Authority, scope, dependencies, permissions, ownership, and allocation only narrow. Minimal stays serial. Balanced allows either two direct non-manager sessions or one manager with at most three direct non-manager descendants, never both or nested. Higher modes have no fixed shape ceiling, but each layer must add supervision, context isolation, or useful parallelism.

## Bounded peer channel

Root may authorize direct messaging only when cheaper than relay and only between exactly two root-spawned `worker/none` siblings. Copy the same addendum into both orders:

```text
PEER CHANNEL
Channel ID / Purpose / Direction:
Authorized canonical peer paths: </root/name, /root/name>
Peer role: <lead | member>
Write ownership / Read-only surfaces:
Escalate to root for:
Root return: <final synthesis | terminal stub>
```

Both orders must match. Use `send_message` or `followup_task` only with the named peer path. No discovery, relative traversal, extra member, manager role, or peer-created channel. Messages are limited to questions, answers, evidence, and corrections already inside both orders and change no objective, scope basis, exclusion, dependency, permission, ownership, criterion, delegation, retry budget, or user authority. Lead remains `worker/none` and gains no spawn, descendant-request, graph, acceptance, completion, or user-contact authority. Messaging never transfers a write surface.

Member sends detail to lead and returns root a terminal stub with status, exact changed paths, validation, and lead path. Lead returns one synthesized `RESULT`; root alone accepts. Peer traffic need not be copied into root context. Escalate order/authority changes, destructive/external action, terminal blockers, or material dependency changes. If direct targeting is unavailable, use root relay.

## Dispatch

```text
DISPATCH REQUEST
Root objective / Request ID / Parent work-order ID:
Requested role and logical lineage:
Objective / Acceptance:
Scope basis / Scope / Exclusions:
Dependencies/readiness / Ownership:
Suggested profile, permissions, descendant allocation:
Validation and delegation value:
```

Root verifies unique request ID, lineage, inherited basis, readiness, ownership, allocation, mode/capacity, route, safety, and value, then accepts, narrows, reroutes, delays, flattens, or rejects. A finding creates no work without existing authority. Exact replay reuses the decision; conflicting reuse is deviation.

Before spawn assign child ID/lineage and reserve allocation. Ordinary routes reserve child ownership; specialized contracts may keep an explicit root write freeze until confirmed start. Proven no-start releases the reservation and creates no child owner after its bounded retry. Uncertain start is potentially live: retain ownership/allocation and prohibit overlap until closure is proven.

## Custody and results

Logical parent is immutable. Replacement or reparenting closes/supersedes the old order and creates a new ID. Record results idempotently by work-order ID. Late closed/superseded results remain evidence only and restore no custody, ownership, or acceptance. Managers reconcile descendants before claiming completion.

```text
MANAGER RESULT ADDENDUM
Descendant requests/orders and status:
Evidence accepted/rejected/superseded/outstanding:
Remaining allocation:
Ownership returned / Recommended parent action:
```

Results normally flow through logical parents. Peer channels change no lineage: member sends detail to lead and stub to root; lead sends synthesis to root. If a parent is unavailable, preserve evidence and resume it or issue a superseding manager order with explicit custody transfer.

Cancellation, quarantine, replacement, or supersession releases ownership/allocation only after closure and proof that no live or potentially live writer remains. Until then the slot and surface stay occupied. A specialized serial fallback that leaves a manager `inactive-resumable` must resume it or explicitly supersede it on every terminal path, including preflight failure or no-start.

A worker block affects one lane; a manager-subgraph block follows only after bounded rerouting/diagnosis; a run block requires no authorized autonomous route. One active writer per mutable surface. Managers subdivide only their owned surface and never overlap live/potential writers. Circular/orphaned/rewritten lineage, authority/allocation amplification, unmanaged recursion, bypassed parent review, or valueless management is deviation. Keep these facts in root session or project-native continuity; create no hierarchy ledger.
