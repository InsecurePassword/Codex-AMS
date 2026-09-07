# AMS configuration maintenance

Load for `AMS CONFIGURATION UPDATE [PROJECT|GLOBAL]`, or when a settings file contains fields outside the current schema. Load `project-control.md` first. This reference never runs implicitly, creates migration history, enables AMS, or changes an existing supported value.

The only retired compatibility fields are `schema_version`, `convergence_control`, `convergence_correction_limit`, `convergence_redesign_limit`, `spark_available`, `work_order_refinement`, `review_control`, `shared_worktree_verification`, `runtime_observation`, `untrusted_evidence_handling`, `task_graph_safeguards`, `rejected_approach_handoff`, `request_accounting`, and `app_task_lane`. Retired Booleans require Boolean; limits remain corrections `2..12` and redesigns `1..12`; schema version must be scalar. Validate them, never branch on them, and omit them on the next authorized write. Reject every other unknown field.

## Project

`AMS CONFIGURATION UPDATE` and `... PROJECT` target `<project-root>/.codex/ams-orchestration.toml`.

When present, validate current/retired fields and file safety; preserve current values; add missing project defaults; remove retired fields; never merge global; do not write when already complete and retired-free. When absent, use valid effective global base values or base defaults, then add `local_llm_lane = false`; invalid global settings block creation.

## Global

`AMS CONFIGURATION UPDATE GLOBAL` targets the global path; `GLOBAL` is mandatory. Validate base current/retired fields; reject project-only local LLM. Preserve current values, add missing base defaults, and remove retired fields. If absent, create the exact disabled base default.

Write atomically only when bytes change, then verify. Never delete, rename, or alter a supported value. Report target, created/updated/unchanged state, current fields added, and retired fields removed. No other command writes global settings.
