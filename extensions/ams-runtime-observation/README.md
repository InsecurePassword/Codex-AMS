# Optional Codex session inspection

This companion reads a limited set of recorded details for a specific local Codex session, such as the model or reasoning setting recorded for that session. Use it when you explicitly need to check those details and the normal display is missing or conflicting.

It does not reveal private reasoning, change models, or grant permissions. Missing evidence stays unknown; the requested model name is not proof of what actually ran.

The normal AMS installer does not install it. Follow [Optional companions and transport limits](../../TECHNICAL%20REFERENCE.md#optional-companions-and-transport-limits) to install the complete folder separately, then restart Codex.

From an active AMS session, ask in chat:

```text
Use ams-runtime-observation to check the recorded model details for
this specific Codex session. Report only the allowed metadata.
```

Provide the actual session/thread ID, not a display title. The companion does not automatically inspect every session and has no persistent AMS on/off setting.

The Windows helper uses PowerShell; the alternative helper requires Python 3.11+. Both inspect Codex session data. This is not a Pi/OpenCode session inspector.

Read [SKILL.md](SKILL.md) for the invocation boundary. Advanced users can inspect the helper interfaces in [Inspect-AgentRuntime.ps1](tools/Inspect-AgentRuntime.ps1) and [inspect-agent-runtime.py](tools/inspect-agent-runtime.py).
