# AMS bounded blocker diagnosis

Use after a reproducible non-runner lane failure. It is evidence-driven, session-only, and creates no campaign, receipt, history, or recovery state. Shared process no-starts use `runtime-core.md` instead.

Capture only decisive evidence: action/work-order, real execution route and invocation class, status/start failure, bounded stderr/output, cwd/relevant environment, scope/ownership/dependencies. Classify invocation/order; tool/model/module/runtime; path/quoting/shell/cwd; permission/sandbox/approval; baseline/hidden dependency; harness/environment; external credential/service/endpoint/physical dependency; or shared runner.

A route is the real mechanism/capability/permission path for the blocked action. Worker, manager, profile/effort, task name, branch, wrapper, shell label, or recovered context alone does not create another route. Admit a new route only with evidence of a materially different viable mechanism; do not invent routes to extend attempts.

## Two attempts per route

Each materially real delegated route receives exactly two execution attempts:

1. **Correction attempt:** targeted evidence checks, the smallest authorized correction, then one execution/validation.
2. **Confirmation attempt:** one execution in the proper lane, either repeating the corrected invocation to test a sporadic failure or applying one materially different evidence-backed correction.

Neither attempt may broaden scope, permissions, ownership, or acceptance. After two failures the route is exhausted; relabeling, replacement, reparenting, model/profile, wrapper/shell, or another worker does not reset it.

When enabled and eligible, `root-execution-fallback.md` may permit one atomic third and final root attempt. Otherwise mark only the affected route/objective deferred or blocked with evidence and both attempts.

Continue every independent authorized ready objective. Ask the user only when no autonomous ready path remains and a concrete credential, permission, physical action, external resource, material choice, or new authority is required. A lane block is not automatically an objective block; an objective block is not automatically a run block.

If a process started and its command failed, diagnose the supported parser/module/path/tool-release/permission cause within the same two attempts. Use another executable only when evidence shows equivalent semantics and a materially different route. Optional local-LLM failure suppresses that lane and reroutes unchanged work; troubleshoot the server only when requested.
