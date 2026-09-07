# AMS Local OpenAI Lane

Optional AMS companion for explicitly authorized work through a project-configured OpenAI-compatible endpoint such as LM Studio or llama.cpp.

Core AMS never installs it and never loads or invokes it unless project-local `local_llm_lane = true`, the current-session lane has not failed, and current-session user steering selects the model and permitted use cases.

Profiles are project-local under:

```text
<project-root>/.codex/ams-local-llm/profiles/*.toml
```

Profile creation, tuning, backend setup, and qualification are separate development work. This companion consumes existing tested profiles; it does not create, edit, repair, tune, discover, or qualify them.
