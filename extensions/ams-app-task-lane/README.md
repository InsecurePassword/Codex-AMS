# Optional Codex app tasks

This companion lets an active AMS session use a separate, user-visible Codex app task when you explicitly ask for one. Most users do not need it for ordinary agent delegation.

It is not included in the normal AMS install. For separate setup, follow [Optional companions and transport limits](../../TECHNICAL%20REFERENCE.md#optional-companions-and-transport-limits). Copy the complete companion, not just its skill file.

After installation, ask the active AMS agent in chat:

```text
Use the ams-app-task-lane companion for this approved task.
Do not push changes or open a pull request unless I authorize it.
```

The current app must expose the required task/thread tools. Installing this folder does not add those tools or grant access. If they are missing, this transport cannot run; other approved AMS work can continue.

The main agent still owns review and acceptance. An app task saying it is done does not by itself finish your project. This companion is not an OpenCode/Pi transport adapter and has no persistent AMS on/off setting.

The exact instructions are in [SKILL.md](SKILL.md) and [the transport reference](references/app-task-lane.md). They are for the agent and advanced users.
