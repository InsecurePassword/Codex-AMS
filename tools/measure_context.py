#!/usr/bin/env python3
"""Measure revision-specific AMS-authored context without claiming provider tokens."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "adaptive-master-subagent-orchestration"
BUDGET_PATH = ROOT / "tools/context-budget.json"
BASELINE_PATH = ROOT / "tools/context-baseline-working-current.json"

SCENARIOS = {
    "bootstrap_skill": ["SKILL.md"],
    "active_core": ["SKILL.md", "references/project-control.md", "references/runtime-core.md", "references/scope-dependency-control.md"],
    "active_governance": ["SKILL.md", "references/project-control.md", "references/runtime-core.md", "references/scope-dependency-control.md", "references/project-governance.md"],
}

MODEL_POLICIES = ["references/model-governance.md", "references/model-guidance.md", "references/model-switching.md"]

LAZY_REFERENCES = [
    *MODEL_POLICIES,
    "references/blocker-diagnosis.md",
    "references/configuration-maintenance.md",
    "references/computer-use.md",
    "references/daybreak-blue.md",
    "references/hierarchy-control.md",
    "references/intensity-control.md",
    "references/package-maintenance.md",
    "references/profile-management.md",
    "references/root-execution-fallback.md",
    "references/zergling-rush.md",
]

COMPANIONS = {
    "ams_app_task_lane": [ROOT / "extensions/ams-app-task-lane/SKILL.md", ROOT / "extensions/ams-app-task-lane/references/app-task-lane.md"],
    "ams_runtime_observation": [ROOT / "extensions/ams-runtime-observation/SKILL.md"],
    "ams_local_openai_lane": [ROOT / "extensions/ams-local-openai-lane/SKILL.md", ROOT / "extensions/ams-local-openai-lane/references/local-openai-lane.md"],
}


def token_estimates(size: int) -> dict[str, object]:
    return {"estimated_tokens": math.ceil(size / 4), "conservative_token_range": [math.ceil(size / 6), math.ceil(size / 2)]}


def metrics(paths: Iterable[Path]) -> dict[str, object]:
    components: list[dict[str, object]] = []
    combined = b""
    for path in paths:
        data = path.read_bytes()
        text = data.decode("utf-8")
        combined += data
        components.append({"path": path.relative_to(ROOT).as_posix(), "characters": len(text), "bytes": len(data), "lines": len(text.splitlines()), "sha256": hashlib.sha256(data).hexdigest()})
    size = len(combined)
    return {"components": components, "characters": len(combined.decode("utf-8")), "bytes": size, "lines": sum(int(item["lines"]) for item in components), "sha256": hashlib.sha256(combined).hexdigest(), **token_estimates(size)}


def baseline_scenarios() -> tuple[str, dict[str, int]]:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    sizes = {path: int(value["bytes"]) for path, value in baseline["components"].items()}
    old = {
        "bootstrap_skill": sizes["SKILL.md"],
        "active_core": sizes["SKILL.md"] + sizes["references/project-control.md"] + sizes["references/runtime-core.md"],
        "active_governance": sizes["SKILL.md"] + sizes["references/project-control.md"] + sizes["references/runtime-core.md"] + sizes["references/project-governance.md"],
    }
    return str(baseline["baseline"]), old


def build_report(model_policies: bool = True) -> dict[str, object]:
    source, baseline = baseline_scenarios()
    scenarios = {name: metrics([PACKAGE / path for path in paths + (MODEL_POLICIES if model_policies and name != "bootstrap_skill" else [])]) for name, paths in SCENARIOS.items()}
    for name, item in scenarios.items():
        item["baseline_bytes"] = baseline[name]
        item["delta_bytes"] = int(item["bytes"]) - baseline[name]
    return {
        "measurement": "UTF-8 bytes with offline token estimates only",
        "comparison_baseline": source,
        "model_policies": "on" if model_policies else "off",
        "boundary": {
            "bootstrap_skill": "always-loaded SKILL.md",
            "active_core": "SKILL + project control + runtime core + scope/dependency control + selected model policies",
            "active_governance": "active core + compact project governance",
            "lazy_references": "incremental only when selected",
            "companions": "separate skills excluded from core manifest",
        },
        "scenarios": scenarios,
        "lazy_references": {path: metrics([PACKAGE / path]) for path in LAZY_REFERENCES},
        "companions": {name: metrics(paths) for name, paths in COMPANIONS.items()},
    }


def check_budget(report: dict[str, object]) -> list[str]:
    budget = json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []
    for name, maximum in budget["scenario_max_bytes"].items():
        actual = int(report["scenarios"][name]["bytes"])
        if actual > int(maximum):
            problems.append(f"{name}: {actual} > {maximum}")
    for name, maximum in budget["scenario_max_delta_bytes"].items():
        actual = int(report["scenarios"][name]["delta_bytes"])
        if actual > int(maximum):
            problems.append(f"{name} delta: {actual} > {maximum}")
    for path, maximum in budget["lazy_reference_max_bytes"].items():
        actual = int(report["lazy_references"][path]["bytes"])
        if actual > int(maximum):
            problems.append(f"{path}: {actual} > {maximum}")
    for name, maximum in budget["companion_max_bytes"].items():
        actual = int(report["companions"][name]["bytes"])
        if actual > int(maximum):
            problems.append(f"companion {name}: {actual} > {maximum}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--model-policies", choices=("on", "off"), default="on")
    args = parser.parse_args()
    report = build_report(args.model_policies == "on")
    problems = check_budget(report) if args.check else []
    report["budget_check"] = {"passed": not problems, "problems": problems}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, item in report["scenarios"].items():
            print(f"{name}: {item['bytes']} bytes; delta={item['delta_bytes']:+d}; ~{item['estimated_tokens']} tokens")
        for path, item in report["lazy_references"].items():
            print(f"lazy {path}: {item['bytes']} bytes; ~{item['estimated_tokens']} tokens")
        for name, item in report["companions"].items():
            print(f"companion {name}: {item['bytes']} bytes; ~{item['estimated_tokens']} tokens")
        for problem in problems:
            print(f"error: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
