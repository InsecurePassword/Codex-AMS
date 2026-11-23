# AMS intensity control

Use only with model governance enabled for non-`auto` modes. Intensity changes topology, never scope, acceptance, dependencies, permissions, routing, validation, or completion.

- `minimal`: at most one active non-root; a manager yields/closes before its descendant starts.
- `balanced` / stored `moderate`: two direct workers or one manager with up to three direct workers; no mix or nesting.
- `heavy`: proactively use useful managers and ready parallel lanes.
- `extreme`: enumerate distinct admitted ready lanes. Before waiting and when slots or readiness change, fill verified free capacity in project priority order; don't wait for unrelated completion or use habitual ceilings.
- `auto`: smallest useful topology; don't load this file merely to choose it.

Heavy/Extreme have no fixed depth or shape ceiling. Root spawns; managers request and supervise, workers execute. Every lane needs existing scope and acceptance, readiness, non-overlapping ownership or isolation, finite allocation, a suitable profile, safety, and net value. Spare slots do not justify splitting coherent work, duplicating effort, or creating scope. Rush requires separate current-turn consent.

Prefer effective harness limits, including stricter live constraints. Account once for occupied, reserved, and potentially live slots. Honor loaded Codex precedence; static files may miss overrides or managed limits. `agents.max_concurrent_threads_per_session` (legacy `agents.max_threads`) excludes root. In known supporting V2, an explicit loaded `features.multi_agent_v2.max_concurrent_threads_per_session` overrides that key and includes root (subtract one for workers). If count is unknown, dispatch real ready work through native admission, track successful/uncertain opens, and honor refusals. Resume capacity-blocked work only on material change; never guess or probe.
