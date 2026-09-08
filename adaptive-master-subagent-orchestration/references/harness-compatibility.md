# AMS harness compatibility

Load only in OpenCode or Pi. The shared skill and AMS settings stay unchanged; this reference maps transport and model presets, not authority or model policy.

- OpenCode: use native `task` with the installed AMS agent name as `subagent_type`. Reuse the returned task/session ID for follow-up when supported. Global agents are under `$OPENCODE_CONFIG_DIR/agents`, otherwise `$XDG_CONFIG_HOME/opencode/agents` or `~/.config/opencode/agents`.
- Pi: use the installed `pi-subagents` extension's `subagent` tool. List available agents, pass the AMS name and assignment, and use returned run IDs for status, steering, or resume. Consult that installed tool's schema/guide, not invented Codex commands. Agents are under `$PI_CODING_AGENT_DIR/agents`, otherwise `~/.pi/agent/agents`.

Both use Markdown presets with provider-qualified model IDs. Only provider-catalog matches are installed. Select only registered routes; a preset is not evidence of account access or effective effort. Never install a Codex TOML to repair an OpenCode/Pi route or silently substitute another model. Native harness restrictions and the user's permission/extension settings remain authoritative. Missing delegation is a capability blocker, not permission for the master to implement the project.

Root retains scheduling, supervision, and spawning. Send the existing AMS assignment policy to each child. Use direct peer messaging only when actually exposed; otherwise relay questions, review findings, and corrections through root. Do not emulate a peer bus or change permissions to obtain tools. Parent relay preserves the coder/reviewer loop, not direct-peer transport parity.

The three model-policy switches still apply. In Pi start fresh child context, not a parent fork; OpenCode uses native task context. Do not change the user-selected master. Daybreak, Codex app tasks, and Codex runtime observation are not ported by this installer. Keep optional local endpoints separately authorized and uninstalled unless requested.

Update presets through the repository installer with the selected harness. Differing generated files are preserved for reconciliation. The shared `~/.agents/skills` location is discoverable by both harnesses unless the user's resource settings disable it; custom skill locations need explicit harness configuration.
