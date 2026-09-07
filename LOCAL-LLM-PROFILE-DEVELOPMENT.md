# Local LLM Profile Development

This repository-only guide is not an AMS skill and is never loaded during orchestration. Use a separate Codex development interaction to create, audit, and qualify project-local profiles before enabling `ams-local-openai-lane`.

## Development boundary

Provide Codex with:

- the backend and version, such as LM Studio or llama.cpp;
- available local model(s) and exact endpoint model identifiers;
- known-good load/unload commands;
- intended context variants and memory placement;
- endpoint URL and authentication environment-variable name, if any;
- desired output/token/time limits.

Codex may build or audit profiles as ordinary project development work. AMS runtime must not create, edit, repair, tune, discover, or qualify them.

## Location and naming

```text
<project-root>/.codex/ams-local-llm/profiles/<profile-name>.toml
```

Use one file per exact runtime configuration, for example:

```text
qwen38-32k.toml
qwen38-128k-ram-kv.toml
```

Variants of the same model use the same `model_key` and different `context_length` values. The endpoint `model` is the exact identifier sent to the OpenAI-compatible API.

## Profile contract

```toml
profile_version = 1
name = "qwen38-32k"
model_key = "qwen38"
context_length = 32768
base_url = "http://127.0.0.1:1234/v1"
api = "chat_completions" # or "responses"
model = "qwen38"
# Optional only when the endpoint reports a known alias for the same selected model.
allowed_observed_models = ["qwen38"]
readiness_path = "/models"

readiness_timeout_seconds = 5
startup_grace_seconds = 5
request_timeout_seconds = 600
command_timeout_seconds = 45
context_reserve_tokens = 2048
max_output_tokens = 8192
temperature = 0.2
keep_loaded_default = true

start_command = ["<exact executable>", "<arg1>", "<arg2>"]
stop_command = ["<exact executable>", "<arg1>"]
# api_key_env = "LOCAL_LLM_API_KEY"
```

`context_length` is mandatory; `start_command` or `keep_loaded_default = false` requires `stop_command`. Tables, shell command strings, embedded credentials, unknown fields, endpoint queries/fragments, redirects, invalid environment-variable names, and profiles outside a non-redirected project profile directory are rejected. Commands are argument arrays executed without a shell. The default readiness/start/grace budget is about 60 seconds; use tested backend-specific limits when needed.

## Required qualification

Before runtime use, test each profile independently:

1. strict TOML/path validation;
2. endpoint already online;
3. endpoint offline followed by the one configured start command;
4. one chat/responses inference request;
5. configured keep-loaded behavior;
6. normal close and `--stop-only` when applicable;
7. readiness and inference timeouts;
8. context preflight below and above the profile limit;
9. same-`model_key` promotion from each smaller context variant;
10. failure without retrying another host, port, launcher, or model;
11. cleanup stop after request failure and after a start command partially starts then exits nonzero or times out;
12. stable non-redirected profile/request reads, request storage outside the project root, and no credentials/prompts/output in failure diagnostics.

Use the bundled helper directly during qualification:

```text
python extensions/ams-local-openai-lane/tools/local_openai_lane.py \
  --project-root <absolute-project-root> \
  --profile <profile-name> \
  --request-file <absolute-request.json> \
  --lifecycle <auto|keep|close>
```

Test unload separately with `--stop-only`; it accepts no request file.

Do not enable the AMS project setting until the selected profiles pass qualification.

## Model identity qualification

Each profile requests one exact `model`. The endpoint response must return that identity. Add `allowed_observed_models` only for tested aliases of the same user-selected model; never use it to authorize automatic model substitution. Qualification must test exact match, missing identity, rejected mismatch, and every allowed alias.
