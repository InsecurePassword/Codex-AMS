---
name: adaptive-master-subagent-orchestration
description: "Top-level AMS delegation, autonomous recovery, and optional model policies."
---

# Adaptive Master-Subagent Orchestration

Use only in the trusted current top-level root. Root model/effort is externally selected; AMS does not select, require, infer, or attest it. Root owns the objective, automation boundary, routing, physical spawning, ownership, integration, acceptance, completion, and user communication. Non-root sessions follow only their work order/profile and never activate AMS.

Handle AMS control commands through `references/project-control.md` before activation or default creation. `AMS STATUS` never writes; normal commands write project settings, and only explicit `GLOBAL` update writes global settings. For control-only requests, return after handling the command.

Resolve settings: project `.codex/ams-orchestration.toml`; otherwise `$CODEX_HOME/ams-orchestration.toml` or `~/.codex/ams-orchestration.toml`; otherwise none. Project replaces global. `references/project-control.md` defines the exact schema, controls, availability, and continuity. Invalid project settings block implicit activation. With no file in a trusted stable project, create its exact disabled project default; explicit invocation may continue, but implicit activation stops for that turn.

Explicit invocation activates the current automation boundary. Implicit activation requires a trusted root and effective `enabled = true` plus `allow_implicit_invocation = true`. Valid current-session steering overrides persistence only where project control permits.

For active work load `references/runtime-core.md`, then only references selected by its gates. Missing required material blocks only that capability. Daybreak is refusal-triggered; package completion triggers nothing.
