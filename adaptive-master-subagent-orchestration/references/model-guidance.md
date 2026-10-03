# AMS model guidance

Load only when `model_guidance = true`. Recommendations, not capabilities or a mandatory ladder; runtime explicit-selection and legacy rules still apply.

Luna 6: Low for supplied procedural commands without analysis, including when another agent reads logs; Medium for straightforward interpretation; High for contextual results or focused implementation. For documentation/general writing, prefer High for source-grounded drafting, Xhigh for multi-section reconciliation and completeness, Max for whole-manual consistency. Keep integral troubleshooting commands with their owner when splitting wastes context; do not relabel routine runs to retain an expensive owner.

Sol 6.1: High for normal coding, diagnosis, integration, architecture, and review. Xhigh for audit discovery, hypotheses, and alternatives; Max for deep finding analysis or difficult synthesis. Exploration need not follow failure.

For an assigned security audit of local/LAN-only software not intended for Internet exposure, select Sol 6.1 Xhigh. For an assigned security audit of Internet-exposed software, select Astra Xhigh. Neither requires a prior finding or failed Sol attempt. Audit authorized surfaces and relevant reachable callees/controls; exposure does not reroute ordinary development or authorize unrelated review.

Astra High remains available for targeted post-solution verification; Xhigh/Max for ramifications and solutions. Other automatic Astra use needs evidence of an unresolved reasoning need or relevant Sol limitation, not importance or "might be better". Use only needed effort and available tools; UI/3D alone does not select Astra.

Only ordinary Sol/Astra Xhigh/Max profiles encourage novel approaches and extrapolation by default. Luna/Terra preserve honest reporting and explicit task flexibility.
