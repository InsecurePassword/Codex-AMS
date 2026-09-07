---
name: ams-runtime-observation
description: "Optional AMS companion for directly requested bounded local routing-metadata corroboration."
---

# AMS runtime observation

Implicit invocation is disabled. Invoke only from an active AMS root when the user directly requests local runtime observation for a specific session and public metadata is insufficient or conflicting. Core AMS never loads this companion from a setting.

Observation records only allowlisted metadata available through the bundled helper. It grants no permission, changes no route, and never converts expected/requested identity into observed identity. Resolve and execute only the exact helper path beneath this companion. Missing or incomplete tooling blocks only the requested observation.
