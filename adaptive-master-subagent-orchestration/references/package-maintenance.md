# AMS package maintenance

Read fully only for an explicit install, update, repair, rollback, uninstall, downgrade preparation, or package-integrity request. Package completion does not load this reference. Package maintenance is root-controlled: the root may delegate bounded inspection or edits through explicit work orders, but retains transaction, integration, and completion authority. Serialize AMS package/control writers.

## Authority and transaction

Require direct user authority for mutation or uninstall. Finish or roll back any settings write first, but do not stop unrelated project sessions solely for package work.

Standard installers fetch canonical published `main`. Explicit `-Local` (PowerShell) or `--local` (Bash) uses the complete trusted extracted package beside the script without network access; all manifest and transaction checks still apply. Validate two byte-identical manifests, exact safe membership, lengths/hashes, all 24 profile markers/provenance, and complete staging before replacement. Installer locking is package-only: recover only a stable lock older than 30 seconds with a same-host proven-dead PID, or a stable old empty ownerless crash lock; every other pre-existing lock fails closed. Never edit general Codex configuration, project settings, optional companions, operating-system permissions, or unrelated files.

Stage outside the installed root. Back up the prior skill and every eligible profile, install transactionally, verify complete bytes, and roll back on failure. Replace a profile only when missing, byte-identical, or an exact recognized official predecessor; preserve and block on customized, marker-only, malformed, ambiguous, or user-authored files.

The package owns no durable runtime state. Preserve project/global settings and installed profiles across normal uninstall unless separately authorized.

## Marketplace and fallback

Marketplace installation supplies the skill but not custom-agent profiles. The documented profiles-only bootstrap deploys all 24 profiles before a new Codex thread and never replaces the skill. The direct installer deploys both core skill and profiles. Package completion triggers no automatic audit, activation, project pause, or user-action gate.

## Downgrade and uninstall

Before downgrade, back up complete current settings. Older releases may reject newer fields; prepare a separate target-compatible live settings file without destroying the current copy. No convergence/runtime export is required because AMS creates no runtime state.

Marketplace uninstall uses Codex plugin removal. Direct uninstall removes only the skill directory. Profile cleanup and settings deletion require separate explicit authority and proven ownership. Refuse redirected or ambiguous roots.
