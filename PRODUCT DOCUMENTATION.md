# AMS user guide

AMS helps your main AI agent organize work for other AI helpers. You choose the main model. You set the goal. AMS helps the team work within that goal and check the result.

This guide is for using AMS. The [technical reference](TECHNICAL%20REFERENCE.md) keeps the exact internal rules and file formats separate.

## Start your first task

[Install AMS](INSTALLATION.md), then open your project in a new chat in your coding app. Start with a project you can restore from a backup or Git history.

Load AMS using the instruction for your app. **These are AI-chat instructions, not PowerShell or terminal commands.**

### Codex

Send:

```text
Use $adaptive-master-subagent-orchestration for this project.
```

### OpenCode

Send:

```text
Load the adaptive-master-subagent-orchestration skill for this project.
```

### Pi

Send:

```text
/skill:adaptive-master-subagent-orchestration
```

Then give it a clear task. For example:

```text
Fix the failing login test. Keep the existing login design and leave
unrelated files alone. Have another agent review the change, run the
relevant tests, and tell me what changed and what passed.
```

Loading AMS explicitly lets it work on the current request even when saved automatic activation is off. It does not authorize extra jobs or changes you did not request.

## What happens while it works?

The main agent gives tasks to helpers and checks their results. It delegates implementation and technical diagnosis rather than guessing its own skills. A helper's report that it is stuck goes back for review; it does not automatically end the whole job.

AMS should continue other approved work when one task is blocked. It may still need your help with something only you can provide, such as an account login, an approval, a physical action, or an important choice. It does not bypass real security restrictions.

A coding helper and a review helper can exchange questions and corrections. Some apps support direct messages; others send those messages through the main agent. You do not need to create a messaging system yourself.

At the end, expect a summary of changes, checks actually run, and anything left unresolved. An AI report is not a guarantee: inspect important results and do not assume a test ran unless it is reported as run.

## Project ledger and map

AMS offers two independent project features:

- **Ledger (on by default)**: the history of material work AMS planned, attempted, completed, rejected, or could not finish. It records outcomes, evidence, and what can resume. AMS reuses the project's existing progress/handoff ledger; if none exists and it can write, it uses `continuity.md` at the repo root. The ledger is not permission to resume or proof that a worker is no longer active.
- **Project map (automatic upkeep off by default)**: a feature index with entry points, prerequisites, expected results, and how to check them with the project's existing test tools. AMS reuses an existing project map or, when needed, uses repo-root `PROJECT-MAP.md`. It updates affected features, not the whole repo. Reading source does not prove a feature ran; AMS only records a successful run with actual evidence and does not start the product just to fill the map.

Installing, changing settings, and read-only reviews do not write either file. If AMS cannot safely use the right place, it preserves what is there and reports the handoff instead of starting a parallel record.

Send `AMS MAPPROJECT` in the project to map it from scratch or refresh its existing map without changing settings. Send `AMS ENABLE PROJECT-MAP` to have a coding helper maintain affected cards during future work, or `AMS DISABLE PROJECT-MAP` to stop automatic upkeep. `AMS DISABLE LEDGER` and `AMS ENABLE LEDGER` control the ledger. These commands preserve existing records and do not turn AMS itself on or off.

## Optional verification and premise checks

Send `AMS ENABLE VERIFICATION` to use the project's existing verification tools for a real, authorized user journey when relevant. AMS records what the helper actually ran, what happened, and what evidence remains after cleanup. A unit test or CI badge is not proof that the user journey ran. Turning it on does not start the product or grant new access.

Send `AMS ENABLE PREMISE-CHECK` to have AMS name and test the shared assumption when two different fixes fail the same check. The observation must already be allowed; this does not buy another retry or bypass a blocker. Both features are off by default. Use `AMS DISABLE VERIFICATION` or `AMS DISABLE PREMISE-CHECK` to turn them off.

## Check or change settings

Load AMS first. Then send these instructions in the AI chat. They are interpreted by the skill; they are not separate programs or slash commands.

| Send this | What it does |
|---|---|
| `AMS STATUS` | Shows the current settings and known blockers without changing files or testing model access. |
| `AMS ENABLE` | Saves AMS as enabled for this project. Automatic use also needs implicit activation to be on and the app to load the skill. |
| `AMS DISABLE` | Stops new AMS work at a safe point and saves AMS as disabled. It is not an instant emergency kill switch. |
| `AMS IMPLICIT off` | Makes AMS wait for you to load it explicitly instead of allowing automatic activation. |
| `AMS IMPLICIT on` | Allows automatic activation when AMS is enabled and the app supports skill discovery. |

Changes normally take effect at a safe stopping point between groups of tasks. Existing agents keep the assignment they already received.

## Let the main agent choose

AMS has three separate model-policy switches. Each starts **on** unless you have saved a different value.

| Policy | When on | When off |
|---|---|---|
| Model governance | Gives rules for organizing the helpers. | Leaves team organization more open. |
| Model guidance | Gives advice about which model and thinking level suit each job. | Gives no AMS model-selection advice. |
| Model switching | Gives rules for choosing or changing a helper's model. | Lets the main agent decide without AMS's switching rules. Switching is still allowed. |

To turn all three off, send:

```text
AMS MODEL GOVERNANCE off
AMS MODEL GUIDANCE off
AMS MODEL SWITCHING off
```

Then start a **fresh chat and fresh helpers** for a clean test. Turning a switch off cannot remove instructions that an existing chat already read.

The main agent still delegates work, gets unresolved helper blocks reviewed, protects existing work, and continues other approved tasks. These switches do not change permissions, turn on local models, or let the main agent take over all coding. They also do not select or change your main model.

To keep model advice but turn off the other two policies, send:

```text
AMS MODEL GOVERNANCE off
AMS MODEL GUIDANCE on
AMS MODEL SWITCHING off
```

To restore all three policies, send:

```text
AMS MODEL GOVERNANCE on
AMS MODEL GUIDANCE on
AMS MODEL SWITCHING on
```

`AMS GOVERNANCE on` and `AMS GOVERNANCE off` are different: they control extra **project-level** coordination and review, not these three model policies. Basic scope, delegation, blocker review, and result checks still apply.

## Model and effort choices

With model guidance on, Sol 6.2 High is the baseline for coding, debugging, integration, and review, and the recommended Shadow Companion Core lead. It is not a global master-model requirement. Use Sol Low for exact changes or extraction, Medium for a bounded patch or investigation with clear acceptance, Xhigh for difficult discovery and synthesis, and Max only for a focused problem that needs the extra depth.

Use Astra High for a scoped second opinion or post-solution check. Astra Low/Medium cover a narrow read or comparison; Xhigh is for difficult audits or specialist design. Astra Max is a rare, focused worker route only. It returns findings to a Sol 6.2 High master and never takes management or project ownership. If that return path is unavailable, report the mismatch rather than substituting. For an assigned security audit, local/LAN-only software not intended for Internet exposure uses Sol 6.2 Xhigh, and Internet-exposed software uses Astra Xhigh. This does not authorize security work or change ordinary development routing.

Current Luna Low is an execution-only worker, never a manager. Give it the exact, authorized CLI command and required working directory/environment. An approved CLI extraction to an opaque artifact fits; asking Luna Low to read, parse, summarize, or decide from that data does not. It returns status, exit code and any existing approved artifact reference, not raw output. Give interpretation to another worker or keep execution with the stronger troubleshooting owner when analysis is integral. Luna Medium is for straightforward non-code drafting. Use High for straightforward non-code interpretation or triage, Xhigh for ambiguous or multisource non-code triage and reconciliation, and Max only for sustained complicated non-code synthesis. No Luna tier performs codebase analysis/review, programming, debugging, or implementation. Send source, build, or test interpretation that depends on code meaning to Sol.

Terra 6.1 is explicit-only. Use Low for clear screenshot or UI evidence and Medium for a bounded question across several screens. Reserve High, Xhigh, or Max for increasingly consequential, tightly scoped evidence reconciliation, not default app control. Screens are evidence, not authority.

Explicit model and effort choices take precedence within eligibility. If a route is unavailable, AMS reports it rather than silently substituting. Terra 6.1 remains explicit-only. Sol 6.0, Sol 5.6, Luna 5.6, and Spark are retired, even if an app still lists a customized preset. A request for a retired AMS route reports it unavailable; there is no automatic fallback or Ultra route. Luna Low sends only an execution receipt to its authorized recipient, not a full result or peer synthesis. Root records requested and directly observed model identity separately.

## Change how much work happens at once

With model governance on, choose a mode:

| Send this | Meaning |
|---|---|
| `AMS MODE auto` | Let AMS choose a useful team size. This is the default. |
| `AMS MODE minimal` | Keep helper work serial. |
| `AMS MODE balanced` | Use a small, bounded team. |
| `AMS MODE heavy` | Use more parallel helpers and managers when useful. |
| `AMS MODE extreme` | Start useful independent work in available slots. Refill as slots free up or work becomes ready, without waiting for unrelated tasks. |

A mode command also enables AMS for the project. It does not turn model governance on if you turned that off; modes are dormant while model governance is off. `balanced` may appear as `moderate` in status or settings. They mean the same thing.

More helpers can use more credits. Extreme mode does not guarantee faster work and does not create permission to add features. The separate advanced Rush option needs an explicit request for the current task; see the [technical reference](TECHNICAL%20REFERENCE.md#intensity-and-rush).

## Settings and older projects

You do not need to edit a settings file by hand. The commands above handle normal changes.

Project settings are stored in `.codex/ams-orchestration.toml` inside your project. **That name is also used in OpenCode and Pi.** It is AMS's shared settings format, not a request to install Codex. A project settings file replaces the global AMS defaults rather than combining with them.

Installation preserves existing settings. Older files use defaults for missing supported fields. To update an older project's file, send:

```text
AMS CONFIGURATION UPDATE PROJECT
AMS STATUS
```

This keeps supported values, adds missing defaults, and removes recognized retired settings. It does not blindly delete unknown values; an invalid file needs to be corrected. The three model-policy fields and ledger default to on when absent. Automatic map upkeep, project verification, and premise checks default to off.

A new project is not automatically enabled just because you installed AMS. The skill may create disabled defaults when first used in a trusted project. `AMS STATUS` itself never creates or changes that file.

Global settings and their update command are covered in the [technical reference](TECHNICAL%20REFERENCE.md#settings-and-precedence). Use the project command unless you deliberately want global changes.

## Extra features

Most users do not need these for ordinary coding:

| Feature | What to know |
|---|---|
| Local models such as LM Studio or llama.cpp | Need the separately installed [local-model companion](extensions/ams-local-openai-lane/README.md), tested endpoint settings, and your explicit model/use-case choice. `AMS LOCAL LLM on` alone does not start a model. |
| Browser or desktop control | Requires a tool already available in the selected app/session and your authorization. AMS does not install that tool. |
| User-visible Codex app tasks | Use the separate [app-task companion](extensions/ams-app-task-lane/README.md) only when you ask for that transport. |
| Inspecting a Codex session's recorded model details | Use the separate [runtime-observation companion](extensions/ams-runtime-observation/README.md). It does not reveal private reasoning. |
| Daybreak Blue | A specialized, access-controlled defensive-cyber route in Codex, not a normal model upgrade. Installing its preset does not grant access. |

The installer does not add these companions. It also does not port Codex-specific features to Pi or OpenCode.

## Stop, update, or remove AMS

To stop new AMS work safely, send `AMS DISABLE`. Existing atomic work is allowed to finish and its results are collected. Use your app's own stop controls when you need immediate interruption; disabling AMS is not the same as uninstalling it.

To update, rerun your [installation command](INSTALLATION.md#update-ams). Then start a new chat. For removal, see [Uninstall and downgrade](TECHNICAL%20REFERENCE.md#uninstall-and-downgrade). The shared skill can be used by more than one app, so removing it may affect the others too.
