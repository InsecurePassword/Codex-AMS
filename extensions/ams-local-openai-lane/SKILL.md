---
name: ams-local-openai-lane
description: "Optional AMS companion for explicitly authorized project-local OpenAI-compatible model work with Codex verification and immediate Codex fallback."
---

# AMS local OpenAI-compatible lane

Invoke only from the active AMS root after all gates pass:

1. a trusted project root and effective **project-local** `local_llm_lane = true`;
2. local-lane session state is not `inactive-after-failure`;
3. current-session user steering names the user-selected model, resolved unambiguously to one configured `model_key`, plus permitted use cases and optional context/lifecycle preference;
4. the candidate work is within those use cases and the current AMS work order;
5. no authoritative project-native local-model lane supersedes this companion.

The setting alone authorizes no call. Implicit invocation is disabled. Never inspect profiles, probe an endpoint, start a model, or send work when any gate fails.

Read `references/local-openai-lane.md` fully before use. Execute only the exact helper path beneath this companion. Local output is work product, not acceptance evidence, until a Codex agent verifies it.
