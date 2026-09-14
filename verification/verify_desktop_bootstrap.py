#!/usr/bin/env python3
"""Regression tests for production Windows Desktop installs without a bundled CLI."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ams_installer", ROOT / "tools/install_harnesses.py")
assert spec and spec.loader
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
VERSION = "1.18.30"
ASSET = "opencode-windows-x64-baseline.zip"


def asar(path: Path, *, name: str = "@opencode-ai/desktop", version: str = VERSION) -> None:
    data = json.dumps({"name": name, "version": version}).encode()
    index = json.dumps({"files": {"package.json": {"offset": "0", "size": len(data)}}}).encode()
    payload = struct.pack("<I", len(index)) + index
    payload += b"\0" * (-len(payload) % 4)
    header = struct.pack("<I", len(payload)) + payload
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<II", 4, len(header)) + header + data)


def release(data: bytes) -> dict:
    return {"tag_name": "v" + VERSION, "draft": False, "prerelease": False, "assets": [{
        "name": ASSET, "size": len(data), "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
        "browser_download_url": f"https://github.com/anomalyco/opencode/releases/download/v{VERSION}/{ASSET}"}]}


def archive(names: tuple[str, ...] = ("opencode.exe",)) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as bundle:
        for name in names:
            bundle.writestr(name, b"fixture-cli-not-executed")
    return stream.getvalue()


class DesktopBootstrap(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.exe = self.home / "desktop/OpenCode.exe"
        self.asar = self.exe.parent / "resources/app.asar"

    def test_reads_real_asar_layout_without_launching_desktop(self) -> None:
        asar(self.asar)
        with patch.object(installer.subprocess, "run") as run:
            self.assertEqual(installer.desktop_version(self.exe), VERSION)
        run.assert_not_called()

    def test_no_asar_is_not_misidentified_as_electron_desktop(self) -> None:
        self.assertIsNone(installer.desktop_version(self.exe))

    def test_rejects_wrong_package_and_nonrelease_version(self) -> None:
        for name, version in (("other-app", VERSION), ("@opencode-ai/desktop", "../../main"),
                              ("@opencode-ai/desktop", "1.18.30-beta")):
            asar(self.asar, name=name, version=version)
            with self.assertRaises(ValueError):
                installer.desktop_version(self.exe)

    def test_rejects_invalid_or_truncated_asar(self) -> None:
        self.asar.parent.mkdir(parents=True)
        for data in (b"bad", struct.pack("<II", 4, 0xFFFFFFFF), struct.pack("<II", 4, 100)):
            self.asar.write_bytes(data)
            with self.assertRaises(ValueError):
                installer.desktop_version(self.exe)

    def download(self, data: bytes, metadata: dict | None = None) -> str:
        with patch.object(installer.platform, "machine", return_value="AMD64"), \
                patch.object(installer.urllib.request, "urlopen", side_effect=[
                    io.BytesIO(json.dumps(metadata or release(data)).encode()), io.BytesIO(data)]):
            return installer.download_desktop_cli(VERSION, self.home)

    def test_download_verifies_hash_and_extracts_only_cli(self) -> None:
        data = archive(("opencode.exe", "not-installed.txt"))
        path = Path(self.download(data))
        self.assertEqual(path.read_bytes(), b"fixture-cli-not-executed")
        self.assertFalse((self.home / "not-installed.txt").exists())

    def test_checksum_failure_never_publishes_executable(self) -> None:
        data = archive()
        metadata = release(data)
        metadata["assets"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.download(data, metadata)
        self.assertFalse((self.home / "opencode.exe").exists())

    def test_untrusted_metadata_rejected_before_binary_download(self) -> None:
        for field, value in (("digest", ""), ("size", -1), ("browser_download_url", "https://example.com/payload.zip")):
            metadata = release(archive())
            metadata["assets"][0][field] = value
            with patch.object(installer.platform, "machine", return_value="AMD64"), \
                    patch.object(installer.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(metadata).encode())) as fetch:
                with self.assertRaises(ValueError):
                    installer.download_desktop_cli(VERSION, self.home)
                self.assertEqual(fetch.call_count, 1)
                self.assertFalse(fetch.call_args.args[0].has_header("Authorization"))

    def test_rejects_wrong_release_and_unsafe_archive_members(self) -> None:
        metadata = release(archive())
        metadata["tag_name"] = "v0.0.0"
        with self.assertRaises(ValueError):
            self.download(archive(), metadata)
        for names in (("../opencode.exe",), ("opencode.exe", "nested/opencode.exe")):
            (self.home / ASSET).unlink(missing_ok=True)
            with self.assertRaises(ValueError):
                self.download(archive(names))
            self.assertFalse((self.home / "opencode.exe").exists())

    def test_desktop_without_cli_uses_matching_release(self) -> None:
        asar(self.asar)
        self.exe.write_bytes(b"fixture-gui-not-executed")
        # The Windows filesystem is case-insensitive; use lower-case in this portable fixture.
        lower = self.exe.with_name("opencode.exe")
        if lower != self.exe:
            self.exe.rename(lower)
        fake_os = types.SimpleNamespace(name="nt", path=os.path, pathsep=os.pathsep)
        with patch.object(installer, "os", fake_os), patch.object(installer, "windows_gui", return_value=True), \
                patch.object(installer, "download_desktop_cli", return_value=str(self.home / "downloaded.exe")) as download, \
                patch.object(installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, VERSION + "\n", "")) as run:
            result = installer.opencode_cli({"PATH": str(lower.parent)}, self.home)
        self.assertEqual(result, str(self.home / "downloaded.exe"))
        download.assert_called_once_with(VERSION, self.home)
        self.assertEqual(run.call_args.args[0], [result, "--version"])

    def test_downloaded_version_mismatch_is_rejected(self) -> None:
        asar(self.asar)
        lower = self.exe.with_name("opencode.exe")
        lower.write_bytes(b"gui")
        fake_os = types.SimpleNamespace(name="nt", path=os.path, pathsep=os.pathsep)
        with patch.object(installer, "os", fake_os), patch.object(installer, "windows_gui", return_value=True), \
                patch.object(installer, "download_desktop_cli", return_value="downloaded.exe"), \
                patch.object(installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "0.0.0\n", "")):
            with self.assertRaisesRegex(ValueError, "exact Desktop version"):
                installer.opencode_cli({"PATH": str(lower.parent)}, self.home)

    def test_temporary_cli_removed_on_success_and_failure(self) -> None:
        profile = {"name": "ams_sol_high", "model": "gpt-5.6-sol", "description": "Sol", "model_reasoning_effort": "high", "developer_instructions": "Assigned task only."}
        for fail in (False, True):
            paths = []
            config = self.home / str(fail)
            def select(_env: dict, directory: Path) -> str:
                executable = directory / "opencode.exe"
                executable.write_bytes(b"fixture")
                paths.append(executable)
                return str(executable)
            with patch.dict(os.environ, {"OPENCODE_CONFIG_DIR": str(config)}), \
                    patch.object(installer, "package_profiles", return_value=[profile]), \
                    patch.object(installer, "install_core"), patch.object(installer, "opencode_cli", side_effect=select), \
                    patch.object(installer, "catalog", return_value={profile["model"]: {"test"}}), \
                    patch.object(installer, "verify_opencode_agents", side_effect=ValueError("missing agent") if fail else None):
                self.assertEqual(installer.install("opencode"), 2 if fail else 0)
            self.assertTrue(paths and all(not p.parent.exists() for p in paths))
            self.assertEqual((config / "agents/ams_sol_high.md").exists(), not fail)


def native(desktop: Path) -> None:
    """Use the official unpacked production app, with no sidecar CLI and no npm CLI on PATH."""
    if os.name != "nt":
        raise AssertionError("The production Desktop regression must execute on Windows.")
    executable = desktop / "OpenCode.exe"
    if not installer.windows_gui(executable) or installer.desktop_version(executable) != VERSION:
        raise AssertionError("Expected the official production Windows Desktop package.")
    if list(desktop.rglob("opencode-cli.exe")):
        raise AssertionError("This regression requires the production package with no CLI binary.")
    with tempfile.TemporaryDirectory(prefix="ams-production-desktop-") as temporary:
        home = Path(temporary).resolve()
        config = home / ".config/opencode"
        config.mkdir(parents=True)
        models = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra", "gpt-5.3-codex-spark")
        settings = config / "opencode.json"
        settings.write_text(json.dumps({"$schema": "https://opencode.ai/config.json", "enabled_providers": ["ams-test"], "provider": {
            "ams-test": {"npm": "@ai-sdk/openai-compatible", "name": "No inference fixture", "options": {"baseURL": "http://127.0.0.1:9/v1", "apiKey": "fixture-not-a-secret"},
                         "models": {m: {"name": m, "reasoning": True, "limit": {"context": 128000, "output": 16000}} for m in models}}}}), encoding="utf-8")
        before = settings.read_bytes()
        env = os.environ.copy()
        for key in tuple(env):
            if key.startswith(("AMS_", "OPENCODE_", "XDG_")):
                env.pop(key)
        system = Path(os.environ["SystemRoot"]) / "System32"
        env.update(HOME=str(home), USERPROFILE=str(home), AMS_SKILL_HOME=str(home / ".agents/skills"),
                   OPENCODE_TEST_HOME=str(home), XDG_DATA_HOME=str(home / "data"), XDG_STATE_HOME=str(home / "state"), XDG_CACHE_HOME=str(home / "cache"),
                   LOCALAPPDATA=str(home / "AppData/Local"),
                   PATH=os.pathsep.join(map(str, (desktop, Path(sys.executable).parent, system / "WindowsPowerShell/v1.0", system))))
        # Intentionally no OPENCODE_CONFIG_DIR, XDG_CONFIG_HOME or AMS_OPENCODE_CLI.
        command = [sys.executable, str(ROOT / "tools/install_harnesses.py"), "--harness", "opencode", "--opencode-provider", "ams-test", "--local"]
        for _ in range(2):
            result = subprocess.run(command, cwd=home, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            print(result.stdout, flush=True)
            if result.returncode:
                raise AssertionError(result.stderr)
            if "downloading temporary official CLI " + VERSION not in result.stdout or "all 23 installed agents confirmed" not in result.stdout:
                raise AssertionError("The Desktop-only bootstrap and native registry check did not execute.")
            files = list((config / "agents").glob("ams_*.md"))
            if len(files) != 23 or settings.read_bytes() != before:
                raise AssertionError("Missing presets or changed provider settings.")
        print("PASS official production Desktop without bundled CLI: temporary matching release, 23 registered agents, default agent directory, reinstall; no model calls.", flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--native":
        native(Path(sys.argv[2]).resolve())
    else:
        unittest.main()
