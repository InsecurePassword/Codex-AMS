# Optional local-model connection

This companion lets AMS send a specific task to a model you run through an OpenAI-compatible server, such as LM Studio or llama.cpp. A suitable Codex agent must check the returned work before it is accepted.

It is separate from OpenCode/Pi's own provider settings. The normal AMS installer does not install this companion or set up a model server.

## Before using it

Follow [Optional companions and transport limits](../../TECHNICAL%20REFERENCE.md#optional-companions-and-transport-limits) for separate installation. You also need Python 3.11+, a working model server, and tested connection profiles for the project. Creating those profiles is separate setup work; use the [local-model development guide](../../LOCAL-LLM-PROFILE-DEVELOPMENT.md).

Profiles belong in:

```text
<project-root>/.codex/ams-local-llm/profiles/*.toml
```

The active AMS session only reads those tested profiles. It does not create, tune, or repair them while doing your task.

## Use it in Codex

After setup, load AMS and send this in chat:

```text
AMS LOCAL LLM on
```

Then name the configured model and the work it may do. For example, after replacing the model name with your own:

```text
Use my configured model ExampleLocal only to summarize these logs.
Have a Codex agent verify the result. Keep the model loaded afterward.
```

The setting alone does not authorize a request. You must select the model and permitted use in the current session. AMS may choose a tested context-size variant of that same model; it does not silently choose another model.

Send `AMS LOCAL LLM off` to disable new local work. It tries to stop only a kept model known to have been started by this companion, not one you started yourself. A local-model failure does not automatically stop the whole project; the unchanged task can return to a Codex agent.

See [SKILL.md](SKILL.md) and [the runtime reference](references/local-openai-lane.md) for exact limits and failure behavior. This companion has not been ported or qualified for OpenCode/Pi by the multi-harness installer.
