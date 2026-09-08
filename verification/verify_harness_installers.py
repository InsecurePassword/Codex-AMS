#!/usr/bin/env python3
"""Exercise native-profile translation and selected-target installs without model calls."""
from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import queue
import threading
import time
import unittest
from unittest.mock import ANY, patch

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

    def test_missing_pi_dependency_keeps_shared_skill(self) -> None:
        self.settings["packages"] = ["npm:keep-other-package"]
        (self.pi / "settings.json").write_text(json.dumps(self.settings), encoding="utf-8")
        result = self.wrapper("pi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pi requires pi-subagents", result.stdout + result.stderr)
        self.assertTrue((self.skill / installer.SKILL / "SKILL.md").exists())
        self.assertFalse((self.pi / "agents").exists())

    def test_dependency_install_is_explicit_and_additive(self) -> None:
        self.settings["packages"] = ["npm:keep-other-package"]
        (self.pi / "settings.json").write_text(json.dumps(self.settings), encoding="utf-8")
        flag = "-InstallPiSubagents" if os.name == "nt" else "--install-pi-subagents"
        self.assert_ok(self.wrapper("pi", flag))
        after = json.loads((self.pi / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(after["packages"], ["npm:keep-other-package", "npm:pi-subagents"])
        self.assertEqual(after["compaction"], self.settings["compaction"])

    def test_custom_profile_collision_preserves_other_targets(self) -> None:
        target = self.oc / "agents/ams_sol_high.md"
        target.parent.mkdir(parents=True)
        target.write_text("custom agent\n", encoding="utf-8")
        result = self.wrapper("all")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), "custom agent\n")
        self.assertTrue((self.skill / installer.SKILL / "SKILL.md").exists())
        self.assertEqual(len(list((self.codex / "agents").glob("*.toml"))), 24)
        self.assertEqual(len(list((self.pi / "agents").glob("*.md"))), 23)

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
        status = installer.install("opencode", "not-configured", "auto", False)
        self.assertEqual(status, 2)
        self.assertTrue((self.skill / installer.SKILL / "SKILL.md").exists())
        self.assertFalse(self.oc.exists())

    def test_only_matching_catalog_models_are_exported(self) -> None:
        with patch.object(installer, "catalog", return_value={"gpt-5.6-sol": {"openai"}}), patch.object(installer, "install_core"):
            installer.install("opencode", "openai", "openai-codex", False)
        self.assertEqual(len(list((self.oc / "agents").glob("*.md"))), 5)

    def test_rollback_preserves_replacement(self) -> None:
        replacement = self.oc / "agents/ams_sol_high.md"
        original = installer.preflight
        count = 0
        def drift(files: dict[Path, bytes]) -> None:
            nonlocal count
            count += 1
            if count == 2:
                replacement.unlink()
                replacement.write_text("replacement from another actor\n", encoding="utf-8")
            original(files)
        with patch.object(installer, "preflight", side_effect=drift):
            self.assertEqual(installer.install("opencode"), 2)
        self.assertEqual(replacement.read_text(encoding="utf-8"), "replacement from another actor\n")
        self.assertEqual(list((self.oc / "agents").glob("*.md")), [replacement])

    def test_remote_source_uses_repository_bytes(self) -> None:
        installer.remote_bytes.cache_clear()
        def remote(path: str) -> bytes:
            return (ROOT / path).read_bytes()
        with patch.object(installer, "remote_bytes", side_effect=remote), \
                patch.object(installer, "catalog", return_value={"gpt-5.6-sol": {"openai"}}), \
                patch.object(installer, "install_core") as core:
            self.assertEqual(installer.install("opencode", local=False), 0)
        self.assertEqual(len(list((self.oc / "agents").glob("*.md"))), 5)
        core.assert_called_once_with({"opencode"}, ANY, False)

    def test_remote_core_stages_verified_package_then_uses_native_local_installer(self) -> None:
        installer.remote_bytes.cache_clear()
        calls: list[list[str]] = []
        def remote(path: str) -> bytes:
            return (ROOT / path).read_bytes()
        def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")
        with patch.object(installer, "remote_bytes", side_effect=remote), \
                patch.object(installer, "_remote_bytes", side_effect=remote), \
                patch.object(installer.subprocess, "run", side_effect=run):
            installer.install_core({"opencode"}, os.environ.copy(), local=False)
        self.assertEqual(len(calls), 1)
        self.assertIn("-Local" if os.name == "nt" else "--local", calls[0])

    def test_remote_codex_skips_harness_catalog(self) -> None:
        with patch.object(installer, "package_profiles") as profiles, \
                patch.object(installer, "install_core") as core:
            self.assertEqual(installer.install("codex", local=False), 0)
        profiles.assert_not_called()
        core.assert_called_once_with({"codex"}, ANY, False)

    def test_auto_finds_nondefault_provider(self) -> None:
        models = {model: {"my-provider"} for model in MODELS}
        with patch.object(installer, "catalog", return_value=models):
            self.assertEqual(installer.install("all"), 0)
        for home in (self.oc, self.pi):
            text = (home / "agents/ams_sol_high.md").read_text()
            self.assertIn('model: "my-provider/gpt-5.6-sol"', text)

    def test_auto_can_use_different_unambiguous_providers(self) -> None:
        models = {"gpt-5.6-sol": {"one"}, "gpt-6-astra": {"two"}}
        with patch.object(installer, "catalog", return_value=models):
            self.assertEqual(installer.install("opencode"), 0)
        self.assertIn('"one/gpt-5.6-sol"', (self.oc / "agents/ams_sol_high.md").read_text())
        self.assertIn('"two/gpt-6-astra"', (self.oc / "agents/ams_astra_high.md").read_text())

    def test_ambiguous_provider_requires_choice_and_keeps_previous_route(self) -> None:
        models = {"gpt-5.6-sol": {"one", "two"}}
        with patch.object(installer, "catalog", return_value=models):
            self.assertEqual(installer.install("opencode"), 2)
            self.assertFalse((self.oc / "agents").exists())
            self.assertEqual(installer.install("opencode", "two"), 0)
            before = {p: p.read_bytes() for p in (self.oc / "agents").glob("*.md")}
            self.assertEqual(installer.install("opencode"), 0)
        self.assertTrue(all(p.read_bytes() == data for p, data in before.items()))

    def test_empty_opencode_catalog_does_not_block_codex_or_pi(self) -> None:
        original = installer.catalog
        def catalog(harness: str, env: dict[str, str]) -> dict[str, set[str]]:
            return {"real-other-model": {"actual-provider"}} if harness == "opencode" else original(harness, env)
        with patch.object(installer, "catalog", side_effect=catalog):
            self.assertEqual(installer.install("all"), 2)
        self.assertTrue((self.skill / installer.SKILL / "SKILL.md").exists())
        self.assertEqual(len(list((self.codex / "agents").glob("*.toml"))), 24)
        self.assertEqual(len(list((self.pi / "agents").glob("*.md"))), 23)
        self.assertFalse((self.oc / "agents").exists())

    def test_no_local_inference_from_working_directory(self) -> None:
        with patch.object(sys, "argv", [str(ROOT / "tools/install_harnesses.py"), "--harness", "codex"]), \
                patch.object(installer, "install", return_value=0) as install:
            self.assertEqual(installer.main(), 0)
        install.assert_called_once_with("codex", "auto", "auto", False, False)

    def test_catalog_respects_current_project_directory(self) -> None:
        result = subprocess.CompletedProcess([], 0, "different/gpt-5.6-sol\n", "")
        with patch.object(installer.subprocess, "run", return_value=result) as run:
            self.assertEqual(installer.catalog("opencode", os.environ.copy()), {"gpt-5.6-sol": {"different"}})
        self.assertEqual(run.call_args.kwargs["cwd"], Path.cwd())

    def test_pi_catalog_does_not_force_offline_or_clear_user_choice(self) -> None:
        for value in (None, "1"):
            with patch.dict(os.environ):
                os.environ.pop("PI_OFFLINE", None)
                if value:
                    os.environ["PI_OFFLINE"] = value
                with patch.object(installer, "catalog", return_value={"gpt-5.6-sol": {"custom"}}) as catalog, patch.object(installer, "install_core"):
                    self.assertEqual(installer.install("pi"), 0)
                self.assertEqual(catalog.call_args.args[1].get("PI_OFFLINE"), value)

    def test_public_download_does_not_require_token_or_contents_api(self) -> None:
        with patch.object(installer.urllib.request, "urlopen", return_value=io.BytesIO(b"content")) as fetch, \
                patch.object(installer, "github_token") as auth:
            self.assertEqual(installer._remote_bytes("SKILL.md"), b"content")
        request = fetch.call_args.args[0]
        self.assertEqual(request.full_url, "https://raw.githubusercontent.com/InsecurePassword/Codex-AMS/main/SKILL.md")
        self.assertFalse(request.has_header("Authorization"))
        auth.assert_not_called()

    def test_remote_manifest_drift_is_rejected(self) -> None:
        with patch.object(installer, "remote_bytes", side_effect=lambda path: (ROOT / path).read_bytes()), \
                patch.object(installer, "_remote_bytes", return_value=b"changed"):
            with self.assertRaisesRegex(ValueError, "manifest changed"):
                installer.stage_remote_package(self.home)

    def test_invalid_manifest_hash_or_alias_is_rejected(self) -> None:
        line = "a" * 64 + "\t1\t" + installer.SKILL + "/SKILL.md\n"
        for body in (line.replace("a" * 64, "oops"), line + line,
                     line + line.replace("SKILL.md", "skill.md"), line.replace("\t1\t", "\t-1\t")):
            with self.subTest(body=body), self.assertRaises(ValueError):
                installer.manifest_entries(b"ams-install-manifest-v1\n" + body.encode())

    def test_rejects_redirected_target(self) -> None:
        outside = self.home / "outside"
        outside.mkdir()
        self.oc.mkdir()
        try:
            (self.oc / "agents").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable on this runner")
        self.assertEqual(installer.install("opencode"), 2)
        self.assertFalse(list(outside.iterdir()))


def codex_skills(executable: str, project: Path, env: dict[str, str]) -> list[dict]:
    """Ask the actual registry used by the picker; never start a model turn."""
    messages: queue.Queue = queue.Queue()
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        process = subprocess.Popen([executable, "app-server"], cwd=project, env=env,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                   text=True, encoding="utf-8", errors="replace")
        def read() -> None:
            assert process.stdout
            for line in process.stdout:
                try:
                    messages.put(json.loads(line))
                except json.JSONDecodeError:
                    continue
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        def send(payload: dict) -> None:
            assert process.stdin
            process.stdin.write(json.dumps(payload) + "\n")
            process.stdin.flush()
        def receive(identifier: int) -> dict:
            end = time.monotonic() + 60
            while time.monotonic() < end:
                message = messages.get(timeout=max(0.1, end - time.monotonic()))
                if message.get("id") == identifier:
                    if "error" in message:
                        raise AssertionError(message["error"])
                    return message["result"]
            raise AssertionError("Codex registry did not respond")
        try:
            send({"id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": "ams_installer_test", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True}}})
            receive(1)
            send({"method": "initialized", "params": {}})
            send({"id": 2, "method": "skills/list", "params": {"cwds": [str(project)], "forceReload": True}})
            data = receive(2)
            entries = data.get("data", [])
            errors = [error for entry in entries for error in entry.get("errors", [])]
            if errors:
                raise AssertionError(f"Native skill parsing errors: {errors}")
            return [skill for entry in entries for skill in entry.get("skills", [])]
        except (OSError, queue.Empty, AssertionError) as error:
            log.seek(0)
            raise AssertionError(f"Codex skill-registry check failed: {error}\n{log.read()}") from error
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            reader.join(timeout=5)
            if process.stdin:
                process.stdin.close()
            if process.stdout:
                process.stdout.close()


def verify_native_codex() -> None:
    executable = shutil.which("codex")
    if not executable:
        raise AssertionError("Native Codex must be installed for this check; no mock or skip is permitted.")
    print(subprocess.check_output([executable, "--version"], text=True).strip(), flush=True)
    with tempfile.TemporaryDirectory(prefix="ams-native-discovery-") as temporary:
        for source in ("standalone", "plugin"):
            home = Path(temporary).resolve() / source
            project = home / "project"
            project.mkdir(parents=True)
            env = os.environ.copy()
            for key in ("AMS_SKILL_HOME", "AMS_INSTALL_PROFILES_ONLY", "AMS_INSTALL_SKILL_ONLY",
                        "OPENAI_API_KEY", "CODEX_API_KEY", "GH_TOKEN", "GITHUB_TOKEN", "PSModulePath"):
                env.pop(key, None)
            env.update(HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home / ".codex"))
            Path(env["CODEX_HOME"]).mkdir()
            if source == "standalone":
                # Keep installation inside the isolated home; no Codex scan-root override.
                env["AMS_SKILL_HOME"] = str(home / ".agents/skills")
                command = [sys.executable, str(ROOT / "tools/install_harnesses.py"), "--harness", "codex", "--local"]
                result = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, timeout=180)
                expected = home / ".agents/skills" / installer.SKILL / "SKILL.md"
                if result.returncode or not expected.is_file():
                    raise AssertionError(result.stdout + result.stderr)
                print(result.stdout, flush=True)
            else:
                for args in (["plugin", "marketplace", "add", str(ROOT)],
                             ["plugin", "add", "Codex-AMS@Codex-AMS"]):
                    result = subprocess.run([executable, *args], cwd=project, env=env, stdin=subprocess.DEVNULL,
                                            capture_output=True, text=True, timeout=120)
                    if result.returncode:
                        raise AssertionError(f"Native plugin install failed: {args}\n{result.stdout}\n{result.stderr}")
            skills = codex_skills(executable, project, env)
            matches = [item for item in skills if item.get("name", "").split(":")[-1] == installer.SKILL]
            if not matches or not any(item.get("enabled") for item in matches):
                raise AssertionError(f"{source}: AMS absent or disabled in native skills/list: {skills}")
            for item in matches:
                if (item.get("interface") or {}).get("displayName") != "AMS":
                    raise AssertionError(f"{source}: missing AMS picker label: {item}")
                if Path(item["path"]).read_bytes() != (ROOT / installer.SKILL / "SKILL.md").read_bytes():
                    raise AssertionError(f"{source}: registry resolved the wrong skill bytes")
            print(f"PASS native Codex {source} registry: " + json.dumps(matches), flush=True)
            if source == "standalone":
                disabled = Path(env["CODEX_HOME"]) / "config.toml"
                disabled.write_text("[[skills.config]]\npath = " + json.dumps(matches[0]["path"]) + "\nenabled = false\n", encoding="utf-8")
                before = disabled.read_bytes()
                result = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, timeout=180)
                if result.returncode or disabled.read_bytes() != before:
                    raise AssertionError("Installer changed or rejected an existing user skill-disable setting")
                after = [item for item in codex_skills(executable, project, env) if item.get("name") == installer.SKILL]
                if not after or any(item.get("enabled") for item in after):
                    raise AssertionError("Native skill-disable setting was not preserved")
                print("PASS user skill-disable configuration preserved (not silently enabled)", flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--codex-discovery"]:
        verify_native_codex()
    else:
        unittest.main()
