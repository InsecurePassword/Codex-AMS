#!/usr/bin/env python3
"""Exercise native-profile translation and selected-target installs without model calls."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_harnesses", ROOT / "tools/install_harnesses.py")
assert spec and spec.loader
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra", "gpt-5.3-codex-spark")


class HarnessInstall(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.pi = self.home / "pi-profile"
        self.oc = self.home / "opencode"
        self.codex = self.home / "codex"
        self.skill = self.home / "skills"
        self.pi.mkdir()
        self.settings = {"packages": ["npm:pi-subagents", "npm:keep-other-package"],
                         "compaction": {"enabled": True}, "defaultProvider": "unchanged"}
        (self.pi / "settings.json").write_text(json.dumps(self.settings), encoding="utf-8")
        fake = self.bin / "catalog.py"
        fake.write_text('''import json, os, pathlib, sys
name, *args = sys.argv[1:]
models = %r
if name == "opencode" and args == ["models"]:
    print("\\n".join("openai/"+m for m in models))
elif name == "pi" and args == ["--list-models"]:
    print("provider model context max-out reasoning images")
    for m in models: print("openai-codex", m, "128k 32k yes yes")
elif name == "pi" and args == ["install", "npm:pi-subagents"]:
    p = pathlib.Path(os.environ["PI_CODING_AGENT_DIR"]) / "settings.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("packages", []).append("npm:pi-subagents")
    p.write_text(json.dumps(data), encoding="utf-8")
else:
    raise SystemExit("Unexpected invocation: " + repr(sys.argv))
''' % (MODELS,), encoding="utf-8")
        for name in ("pi", "opencode"):
            if os.name == "nt":
                (self.bin / (name + ".cmd")).write_text(f'@echo off\r\n"{sys.executable}" "{fake}" {name} %*\r\n', encoding="utf-8")
            else:
                target = self.bin / name
                target.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" {name} "$@"\n', encoding="utf-8")
                target.chmod(0o700)
        environment = {
            "HOME": str(self.home), "USERPROFILE": str(self.home),
            "AMS_SKILL_HOME": str(self.skill), "CODEX_HOME": str(self.codex),
            "PI_CODING_AGENT_DIR": str(self.pi), "OPENCODE_CONFIG_DIR": str(self.oc),
            "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
        }
        self.context = patch.dict(os.environ, environment)
        self.context.start()
        self.addCleanup(self.context.stop)
        for key in ("AMS_INSTALL_PROFILES_ONLY", "AMS_INSTALL_SKILL_ONLY"):
            os.environ.pop(key, None)

    def wrapper(self, harness: str, *extra: str) -> subprocess.CompletedProcess[str]:
        if os.name == "nt":
            command = [shutil.which("powershell.exe") or "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install.ps1"), "-Local", "-Harness", harness]
        else:
            command = ["bash", str(ROOT / "install.sh"), "--local", "--harness", harness]
        env = os.environ.copy()
        env.pop("PSModulePath", None)
        return subprocess.run([*command, *extra], cwd=ROOT, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=180)

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_targets_and_reinstall_preserve_settings(self) -> None:
        self.codex.mkdir()
        (self.codex / "config.toml").write_text('model = "leave-me-alone"\n', encoding="utf-8")
        self.oc.mkdir()
        (self.oc / "opencode.jsonc").write_text('// keep comments\n{"permission":{"bash":"ask"}}\n', encoding="utf-8")
        before = {p: p.read_bytes() for p in (self.pi / "settings.json", self.codex / "config.toml", self.oc / "opencode.jsonc")}
        self.assert_ok(self.wrapper("all"))
        self.assertEqual(len(list((self.codex / "agents").glob("*.toml"))), 24)
        for target in (self.pi, self.oc):
            agents = sorted((target / "agents").glob("*.md"))
            self.assertEqual(len(agents), 23)
            self.assertFalse(any("daybreak" in p.name for p in agents))
        self.assertEqual(len([p for p in (self.skill / installer.SKILL).rglob("*") if p.is_file()]), 44)
        snapshots = {p: p.read_bytes() for folder in (self.pi, self.oc, self.codex) for p in folder.rglob("*") if p.is_file()}
        self.assert_ok(self.wrapper("all"))
        self.assertTrue(all(p.read_bytes() == data for p, data in snapshots.items()))
        self.assertTrue(all(p.read_bytes() == data for p, data in before.items()))
        self.assertFalse(any(self.home.rglob(".ams-install-*")))

    def test_opencode_only_does_not_touch_codex_or_pi(self) -> None:
        before = (self.pi / "settings.json").read_bytes()
        self.assert_ok(self.wrapper("opencode"))
        self.assertFalse(self.codex.exists())
        self.assertFalse((self.pi / "agents").exists())
        self.assertEqual((self.pi / "settings.json").read_bytes(), before)
        self.assertTrue((self.skill / installer.SKILL / "SKILL.md").is_file())

    def test_pi_only_honors_selected_profile(self) -> None:
        self.assert_ok(self.wrapper("pi"))
        self.assertEqual(len(list((self.pi / "agents").glob("*.md"))), 23)
        self.assertFalse(self.oc.exists())
        self.assertFalse(self.codex.exists())
        self.assertFalse((self.home / ".pi/agent").exists())

    def test_profiles_only_does_not_install_skill_or_codex(self) -> None:
        os.environ["AMS_INSTALL_PROFILES_ONLY"] = "1"
        self.assert_ok(self.wrapper("opencode"))
        self.assertFalse(self.skill.exists())
        self.assertFalse(self.codex.exists())

    def test_missing_pi_dependency_fails_before_ams_writes(self) -> None:
        self.settings["packages"] = ["npm:keep-other-package"]
        (self.pi / "settings.json").write_text(json.dumps(self.settings), encoding="utf-8")
        result = self.wrapper("pi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pi requires pi-subagents", result.stdout + result.stderr)
        self.assertFalse(self.skill.exists())
        self.assertFalse((self.pi / "agents").exists())

    def test_dependency_install_is_explicit_and_additive(self) -> None:
        self.settings["packages"] = ["npm:keep-other-package"]
        (self.pi / "settings.json").write_text(json.dumps(self.settings), encoding="utf-8")
        flag = "-InstallPiSubagents" if os.name == "nt" else "--install-pi-subagents"
        self.assert_ok(self.wrapper("pi", flag))
        after = json.loads((self.pi / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(after["packages"], ["npm:keep-other-package", "npm:pi-subagents"])
        self.assertEqual(after["compaction"], self.settings["compaction"])

    def test_custom_profile_collision_preserved_before_core_install(self) -> None:
        target = self.oc / "agents/ams_sol_high.md"
        target.parent.mkdir(parents=True)
        target.write_text("custom agent\n", encoding="utf-8")
        result = self.wrapper("all")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), "custom agent\n")
        self.assertFalse(self.skill.exists())
        self.assertFalse(self.codex.exists())
        self.assertFalse((self.pi / "agents").exists())

    def test_render_uses_native_fields_and_no_authority_overrides(self) -> None:
        for p in installer.package_profiles():
            for harness in ("pi", "opencode"):
                text = installer.render(p, harness, "exact-provider").decode()
                fields = dict((key, json.loads(value.strip())) for key, value in
                              (line.split(":", 1) for line in text.split("---\n")[1].splitlines()))
                self.assertEqual(fields["model"], "exact-provider/" + p["model"])
                self.assertEqual(fields["thinking" if harness == "pi" else "reasoningEffort"], p["model_reasoning_effort"])
                self.assertNotIn("permission", fields)
                self.assertNotIn("tools", fields)
                self.assertNotIn("spawn", text)
                self.assertIn(p["developer_instructions"], text)

    def test_unavailable_provider_never_substitutes_model(self) -> None:
        with self.assertRaisesRegex(ValueError, "No AMS models"):
            installer.install("opencode", "not-configured", "openai-codex", False)
        self.assertFalse(self.skill.exists())
        self.assertFalse(self.oc.exists())

    def test_only_matching_catalog_models_are_exported(self) -> None:
        with patch.object(installer, "catalog", return_value={"gpt-5.6-sol"}), patch.object(installer, "install_core"):
            installer.install("opencode", "openai", "openai-codex", False)
        self.assertEqual(len(list((self.oc / "agents").glob("*.md"))), 5)

    def test_rollback_preserves_replacement(self) -> None:
        replacement = self.oc / "agents/ams_sol_high.md"
        def fail_native(*_args: object) -> None:
            replacement.unlink()
            replacement.write_text("replacement from another actor\n", encoding="utf-8")
            raise RuntimeError("simulated native install failure")
        with patch.object(installer, "install_core", side_effect=fail_native):
            with self.assertRaisesRegex(RuntimeError, "simulated"):
                installer.install("opencode", "openai", "openai-codex", False)
        self.assertEqual(replacement.read_text(encoding="utf-8"), "replacement from another actor\n")
        self.assertEqual(list((self.oc / "agents").glob("*.md")), [replacement])

    def test_rejects_redirected_target(self) -> None:
        outside = self.home / "outside"
        outside.mkdir()
        self.oc.mkdir()
        try:
            (self.oc / "agents").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable on this runner")
        with self.assertRaisesRegex(ValueError, "Redirected"):
            installer.install("opencode", "openai", "openai-codex", False)
        self.assertFalse(list(outside.iterdir()))


if __name__ == "__main__":
    unittest.main()
