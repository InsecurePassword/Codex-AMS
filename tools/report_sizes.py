#!/usr/bin/env python3
"""Compare the current AMS installed core with the selected working baseline."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "verification/fixtures/baseline-install-manifest-working-current.txt"
CURRENT = ROOT / "install-manifest.txt"
BASE_LABEL = "Codex-AMS main 57dc12782cc1ea0d16d9c151afdb9cf8ea4bfddf"
EXTENSIONS = (
    ROOT / "extensions/ams-app-task-lane",
    ROOT / "extensions/ams-runtime-observation",
    ROOT / "extensions/ams-local-openai-lane",
)


def manifest(path: Path, *, allow_legacy_version: bool) -> dict[str, dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "ams-install-manifest-v1":
        raise ValueError(f"invalid manifest header: {path}")
    start = 1
    if len(lines) > 1 and lines[1].startswith("version\t"):
        if not allow_legacy_version:
            raise ValueError(f"release-version line is forbidden in current manifest: {path}")
        start = 2
    out: dict[str, dict[str, Any]] = {}
    for line in lines[start:]:
        digest, length, repo_path = line.split("\t")
        out[repo_path] = {"sha256": digest, "bytes": int(length)}
    return out


def record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def build() -> dict[str, Any]:
    before = manifest(BASE, allow_legacy_version=True)
    after = manifest(CURRENT, allow_legacy_version=False)
    rows: list[dict[str, Any]] = []
    for path in sorted(set(before) | set(after)):
        baseline = before.get(path)
        candidate = after.get(path)
        baseline_bytes = baseline["bytes"] if baseline else 0
        candidate_bytes = candidate["bytes"] if candidate else 0
        status = (
            "added"
            if baseline is None
            else "removed"
            if candidate is None
            else "unchanged"
            if baseline["sha256"] == candidate["sha256"]
            else "modified"
        )
        rows.append(
            {
                "path": path,
                "status": status,
                "baseline_bytes": baseline_bytes,
                "candidate_bytes": candidate_bytes,
                "delta_bytes": candidate_bytes - baseline_bytes,
                "baseline_sha256": baseline["sha256"] if baseline else None,
                "candidate_sha256": candidate["sha256"] if candidate else None,
            }
        )

    companions: dict[str, Any] = {}
    for extension in EXTENSIONS:
        items = [
            record(path)
            for path in sorted(extension.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        ]
        companions[extension.name] = {
            "file_count": len(items),
            "bytes": sum(item["bytes"] for item in items),
            "files": items,
        }

    baseline_total = sum(item["bytes"] for item in before.values())
    candidate_total = sum(item["bytes"] for item in after.values())
    return {
        "comparison_baseline": {
            "label": BASE_LABEL,
            "file_count": len(before),
            "bytes": baseline_total,
        },
        "candidate": {"file_count": len(after), "bytes": candidate_total},
        "core_delta": {
            "file_count": len(after) - len(before),
            "bytes": candidate_total - baseline_total,
            "percent": round((candidate_total - baseline_total) * 100 / baseline_total, 4),
        },
        "core_files": rows,
        "companions": companions,
    }


def csv_text(rows: list[dict[str, Any]]) -> str:
    handle = io.StringIO(newline="")
    fields = (
        "path",
        "status",
        "baseline_bytes",
        "candidate_bytes",
        "delta_bytes",
        "baseline_sha256",
        "candidate_sha256",
    )
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def markdown_text(report: dict[str, Any]) -> str:
    lines = [
        "# AMS current-update bloat assessment",
        "",
        f"- Working baseline: **{report['comparison_baseline']['bytes']:,} bytes / {report['comparison_baseline']['file_count']} files** (`{report['comparison_baseline']['label']}`).",
        f"- Current update: **{report['candidate']['bytes']:,} bytes / {report['candidate']['file_count']} files**.",
        f"- Delta: **{report['core_delta']['bytes']:+,} bytes / {report['core_delta']['file_count']:+d} files ({report['core_delta']['percent']:+.2f}%)**.",
        "",
        "| File | Status | Baseline | Update | Delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in report["core_files"]:
        lines.append(
            f"| `{item['path']}` | {item['status']} | {item['baseline_bytes']:,} | {item['candidate_bytes']:,} | {item['delta_bytes']:+,} |"
        )
    lines.extend(["", "## Separate companions", ""])
    for name, item in report["companions"].items():
        lines.append(f"- `{name}`: **{item['bytes']:,} bytes / {item['file_count']} files**, excluded from core.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "csv", "md", "summary"), default="summary")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build()
    if args.format == "json":
        text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    elif args.format == "csv":
        text = csv_text(report["core_files"])
    elif args.format == "md":
        text = markdown_text(report)
    else:
        text = (
            f"Core package: {report['comparison_baseline']['bytes']} -> {report['candidate']['bytes']} "
            f"({report['core_delta']['bytes']:+d})\n"
        )
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
