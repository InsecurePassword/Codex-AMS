#!/usr/bin/env python3
"""Adversarial fixtures for the optional AMS runtime-observation companion."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "extensions/ams-runtime-observation/tools/inspect-agent-runtime.py"
ID = "11111111-1111-7111-8111-111111111111"
ALLOWLIST = {
    "thread_id", "parent_thread_id", "agent_role", "agent_path", "model_provider",
    "model", "effort", "sandbox_policy_type", "permission_profile_type", "cwd",
}


def write(path: Path, model: str = "gpt-5.6-terra", effort: str = "high") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {"type": "response_item", "payload": {"prompt": "DO_NOT_LEAK"}},
        {"type": "session_meta", "payload": {"id": ID, "parent_thread_id": "00000000-0000-7000-8000-000000000000", "agent_role": "ams_terra_high", "agent_path": "/root/a", "model_provider": "openai"}},
        {"type": "turn_context", "payload": {"model": model, "effort": effort, "sandbox_policy": {"type": "danger-full-access"}, "permission_profile": {"type": "disabled"}, "cwd": "/fixture"}},
    ]
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), ID, "--sessions-dir", str(root)], text=True, capture_output=True)


def load_helper():
    spec = importlib.util.spec_from_file_location("ams_observer_fixture", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Observation(unittest.TestCase):
    def test_valid_allowlist_and_no_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            write(Path(td) / f"2026/08/03/rollout-x-{ID}.jsonl")
            result = run(Path(td))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("DO_NOT_LEAK", result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(data["model"], "gpt-5.6-terra")
            self.assertEqual(set(data), ALLOWLIST)

    def test_duplicate_match_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            write(Path(td) / f"a/rollout-x-{ID}.jsonl")
            write(Path(td) / f"b/rollout-y-{ID}.jsonl")
            self.assertNotEqual(run(Path(td)).returncode, 0)

    @unittest.skipIf(os.name == "nt", "symlink fixture uses Unix semantics")
    def test_exact_symlink_match_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); target = root / "target.jsonl"; write(target)
            (root / f"rollout-x-{ID}.jsonl").symlink_to(target)
            result = run(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("redirected", result.stderr)

    @unittest.skipIf(os.name == "nt", "descriptor-relative fixture uses POSIX semantics")
    def test_ancestor_replacement_cannot_escape_root(self) -> None:
        helper = load_helper()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); root = base / "sessions"; day = root / "day"; outside = base / "outside"
            inside_file = day / f"rollout-x-{ID}.jsonl"; outside_file = outside / f"rollout-x-{ID}.jsonl"
            write(inside_file, model="gpt-5.6-terra"); write(outside_file, model="gpt-5.6-sol")
            day_inode = day.stat().st_ino; real_scandir = helper.os.scandir; swapped = False

            def hostile_scandir(target):
                nonlocal swapped
                if isinstance(target, int) and not swapped and os.fstat(target).st_ino == day_inode:
                    day.rename(root / "day-original")
                    day.symlink_to(outside, target_is_directory=True)
                    swapped = True
                return real_scandir(target)

            helper.os.scandir = hostile_scandir
            try:
                matches = helper.exact_match_fds_posix(root, ID)
                self.assertEqual(len(matches), 1)
                observed = helper.inspect_rollout_fd(matches[0], ID)
            finally:
                helper.os.scandir = real_scandir
            self.assertTrue(swapped)
            self.assertEqual(observed["model"], "gpt-5.6-terra")

    def test_invalid_json_fails_without_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / f"rollout-x-{ID}.jsonl"
            path.write_text('{"prompt":"SECRET"\n', encoding="utf-8")
            result = run(Path(td))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("SECRET", result.stderr + result.stdout)

    def test_conflicting_model_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / f"rollout-x-{ID}.jsonl"; write(path)
            extra = {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high", "sandbox_policy": {"type": "danger-full-access"}, "permission_profile": {"type": "disabled"}, "cwd": "/fixture"}}
            path.write_text(path.read_text(encoding="utf-8") + json.dumps(extra) + "\n", encoding="utf-8")
            self.assertNotEqual(run(Path(td)).returncode, 0)

    def test_invalid_id_fails(self) -> None:
        result = subprocess.run([sys.executable, str(SCRIPT), "invalid", "--sessions-dir", str(ROOT)], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
