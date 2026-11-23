---
name: adaptive-master-subagent-orchestration
description: "Top-level AMS delegation, autonomous recovery, and optional model policies."
---

# Adaptive Master-Subagent Orchestration

Use only in the trusted current top-level root. Root model/effort is externally selected; AMS does not select, require, infer, or attest it. Root owns the objective, automation boundary, routing, physical spawning, ownership, integration, acceptance, completion, and user communication. Non-root sessions follow only their work order/profile and never activate AMS.

Handle AMS control commands per `references/project-control.md` before activation/default creation. `AMS STATUS` never writes. Only explicit `GLOBAL` update writes global settings. For control-only requests, return.

Resolve settings: project `.codex/ams-orchestration.toml` replaces `$CODEX_HOME/ams-orchestration.toml` (`~/.codex/ams-orchestration.toml` if unset). Invalid project settings block implicit activation. If neither exists in a trusted stable project, create the exact disabled project defaults; explicit invocation may continue, implicit stops.

Explicit invocation activates the current boundary. Implicit activation needs effective `enabled = true` and `allow_implicit_invocation = true` in a trusted root. Session steering overrides settings only as project control permits.

For active work load `references/runtime-core.md` and its gated references only; missing material blocks only that capability. Daybreak is refusal-triggered; package completion triggers nothing.

Before sizing delegation, use the active harness’s effective limit when exposed; in Codex read only concurrency settings from trusted `.codex/config.toml` and `$CODEX_HOME/config.toml` (`~/.codex/config.toml` if unset) if readable, without edits or exposing credentials or unrelated values.
