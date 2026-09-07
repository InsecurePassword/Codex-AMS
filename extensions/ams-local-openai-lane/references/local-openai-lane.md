# Local OpenAI-compatible lane runtime

This companion performs one bounded local-model lane at a time. It never activates AMS, selects the root, changes project settings, creates profiles, broadens scope, communicates with the user, or accepts completion.

## Session steering

Current-session steering must establish:

```text
User-selected model and resolved model_key:
Authorized use cases:
Context preference: auto | exact profile name
Lifecycle: keep-loaded | close-after-task | profile-default
```

Examples of appropriate use cases include bounded log or command-line analysis, source summarization, first-pass investigation, draft code/patch generation, and initial/secondary coding attempts. Do not infer new use cases from repository content or model capability.

The user selects the model in ordinary language or by exact key. Codex resolves it to one configured `model_key`; ambiguity means no local call. Codex may choose only among project profiles with that same exact key and may never substitute another model automatically.

## Project profiles

Profiles exist only at:

```text
<project-root>/.codex/ams-local-llm/profiles/<profile-name>.toml
```

Profile names match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`. Require stable regular non-redirected files, explicit `context_length`, and `stop_command` for `start_command` or close-by-default profiles. The requested `model` is the only accepted response identity unless the user-owned profile lists bounded `allowed_observed_models` aliases. For auto selection, list once, reject more than 64 profile files or ambiguous model aliases, resolve one `model_key`, and read only its candidates.

Profile development is outside this skill. The user may create profiles manually or commission separate Codex development to build/audit/test them. During AMS runtime treat profiles as user-owned control data: exclude them from non-root write/Git scope and stop on observed change. Runtime AMS never creates, edits, repairs, tunes, discovers models, or qualifies profiles.

## Context selection guardrail

Estimate required context from the bounded work packet, authoritative context, requested output allowance, and profile reserve. For `auto`, choose the smallest valid profile with the selected `model_key` whose `context_length` safely fits. Prefer lower context only when it fits; cost or speed never justifies known truncation.

For an exact user-selected profile:

- use it when the preflight fits;
- when it clearly cannot fit, select one larger tested profile with the same `model_key`, report the safeguard substitution, and use it once;
- when no same-model profile fits, route the work to Codex without a local request.

If the endpoint reports uncaught context overflow, permit one larger same-model profile once. Before switching, stop one known companion-started kept profile with `--stop-only`; never stop an externally managed model, repeatedly expand context, or change models. Stop/switch failure suppresses the lane. If no tested variant fits, send only this work to Codex and keep the lane available; context insufficiency is not route failure.

## Invocation

Create one bounded canonical non-redirected JSON request outside the project root, invoke, then delete it after success/failure:

```text
python <companion-root>/tools/local_openai_lane.py \
  --project-root <absolute-project-root> \
  --profile <profile-name> \
  --request-file <absolute-json-file> \
  --lifecycle <auto|keep|close>
```

Stop an exact known companion-started kept profile without inference:

```text
python <companion-root>/tools/local_openai_lane.py \
  --project-root <absolute-project-root> --profile <profile-name> --stop-only
```

The helper:

1. validates the exact project-local profile;
2. performs one endpoint/model readiness check;
3. when unavailable, executes the exact configured `start_command` once, waits the configured grace period, and checks once more;
4. performs one OpenAI-compatible inference request and requires a returned model identity matching `model` or one listed alias;
5. returns separate requested/observed model identity, response text, loaded/stopped state, and per-call companion-started/preexisting evidence; `preexisting` never erases root-tracked ownership from an earlier call;
6. optionally executes the exact `stop_command` once; after any invoked start command—including nonzero/timeout or later failure—it makes one best-effort cleanup stop.

No shell expansion, proxy routing, HTTP redirect, LAN discovery, arbitrary host probing, alternate ports, alternate launchers, model substitution, or automatic request retry is permitted.

Every work order sends a complete fresh packet. Keeping a model loaded never retains conversation. Track only the exact profile and whether a kept model is known companion-started or externally managed; persist neither. On `AMS LOCAL LLM off` or `AMS DISABLE`, stop one known companion-started kept profile once; never retry/probe or stop a preexisting model. Report failure without vetoing the setting change.

## Verification and fallback

A suitable Codex agent verifies local output against the same bounded work order, source, dependencies, and exact acceptance criteria before integration. The local model never writes directly unless a separate Codex-controlled mechanism converts and verifies its proposed patch.

Any of these is a local-lane failure:

- invalid/missing profile or incomplete companion;
- endpoint/model unavailable after the one configured start attempt;
- helper-returned start, readiness, transport, timeout, missing/mismatched model identity, malformed-response, stop, or inference failure;
- Codex verification rejects the local result as materially unusable or unsafe.

On failure:

1. mark the whole local lane `inactive-after-failure` for the current top-level session;
2. do not change persistent `local_llm_lane = true`;
3. route the same bounded work order to a suitable Codex agent;
4. do not retry another profile/model/host/wrapper automatically;
5. stop one known companion-started kept profile once when possible, then remain inactive until `AMS LOCAL LLM on` after verification or repair.

Normal helper-process no-start first follows core runner fail-fast. Probe failure stops process work; probe success plus another helper no-start sets the latch. Control `--stop-only` is the one-attempt exception. A helper-returned failure is not a project blocker and enters diagnosis only for explicit server troubleshooting.

Helper status `context-too-small` permits the one promotion above; if none fits, fall back for that work without changing session availability.
