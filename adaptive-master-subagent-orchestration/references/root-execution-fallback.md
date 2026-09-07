# AMS root execution fallback

Load only after one delegated route exhausts its two attempts, mandatory progress would stop, no other viable delegated route can do the same action, and `root_execution_fallback = true`. Fallback is default-off and never normal execution. Scope/dependency admission, runner fail-fast, higher policy, and ownership still control.

Root may act only when the action is mandatory and already authorized; exactly two delegated attempts failed; no viable delegated route remains; no approval is needed; mutation is low-risk/reversible and not destructive, irreversible, external, or security-sensitive; no live/potential writer owns the surface; one smallest atomic action can restore progress; and the runner episode is not terminal.

An unavailable or exhausted Daybreak route never authorizes root execution of the refused security-sensitive task. A runner probe is diagnostic, not fallback.

## Third and final attempt

This is one atomic third and final execution attempt for the exhausted route. Record:

```text
Root fallback:
Exhausted route and attempts / Blocker:
Scope basis / Dependencies / Ownership and safety:
Atomic action / Output bound / Exact validation:
```

Before mutation close, cancel, quarantine, or supersede the affected order; prove its writer inactive; preserve lineage/late-result rules; reclaim the surface; and hold temporary root ownership in session.

Use targeted reads and bounded output. After mutation capture an exact commit, diff, snapshot, hash, or immutable artifact and freeze the surface until captured. Later writes must explicitly supersede it; old validation cannot accept combined state. No second root attempt or relabeling resets the budget.

A mutation remains incomplete until a suitable non-root validates that exact result, or the user explicitly accepts documented residual risk. Root cannot self-accept, even with governance off.

Stop if scope/dependencies change materially, risk becomes material, ownership is uncertain, approval is needed, or the atomic endpoint becomes unclear. Never bypass safety, permissions, authorization, or runner fail-fast.
