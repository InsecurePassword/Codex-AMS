# Codex AMS

**Give your AI coding app a team of helpers.**

AMS stands for Adaptive Master-Subagent Orchestration. It is a set of instructions for **Codex, OpenCode, and Pi**. You choose the main AI model and describe a job. AMS helps that model split the job into smaller tasks, give them to other AI agents, check their work, and keep going.

If a helper gets stuck, the main agent asks for a closer look instead of treating every problem as the end of the job. Your existing permissions and project rules still apply.

## Start here

1. **[Install AMS](INSTALLATION.md)** for the coding app you use. The installer downloads the files directly; you do not need a ZIP or a copy of this repository.
2. Open your project in a **new chat** in that app.
3. **[Start your first task](PRODUCT%20DOCUMENTATION.md#start-your-first-task)** and tell AMS what you want done.

Already installed? Use the same [installation command](INSTALLATION.md) to update it, then start a new chat.

## What you can do

Ask AMS to fix a bug, build a feature, review a change, or work through an agreed project plan. Give it a clear goal and say what it should leave alone.

For example, after loading the skill:

```text
Use AMS to fix the failing login test. Keep the existing design.
Have another agent review the fix, run the relevant tests, and report the result.
```

You can keep AMS's model advice or turn it off and let the main agent choose. The [user guide](PRODUCT%20DOCUMENTATION.md#let-the-main-agent-choose) explains the three switches. Turning those switches off does not remove delegation or help with stuck tasks.

## What to expect

AMS does not install Codex, OpenCode, Pi, or the AI models themselves. You need a working coding app and access to suitable models. AI use can spend credits or use your subscription allowance; more helpers are not always cheaper.

Installation does not automatically enable AMS in every project. It also does not change your main model, passwords, provider settings, or permissions. The Pi install can add its required subagent extension when you choose that option.

Agents can exchange review questions and corrections. Whether they talk directly or through the main agent depends on the app's tools. Browser or computer control also requires tools already available in that app; AMS does not install a desktop-control program.

## Guides

| I want to... | Read this |
|---|---|
| Install, update, or fix a setup problem | [Installation](INSTALLATION.md) |
| Start work, change settings, or stop AMS | [User guide](PRODUCT%20DOCUMENTATION.md) |
| Understand the exact settings, rules, and file layout | [Technical reference](TECHNICAL%20REFERENCE.md) |
| Set up an optional local-model connection | [Local-model companion](extensions/ams-local-openai-lane/README.md) |

Most users only need the first two guides. The technical files are separate so you do not have to learn AMS's internal rules to use it.
