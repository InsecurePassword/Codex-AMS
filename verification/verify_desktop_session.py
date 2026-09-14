#!/usr/bin/env python3
"""Verify safe installation around an already-open, actual packaged Windows Desktop."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import urllib.request
import urllib.parse

from verify_desktop_bootstrap import installer, VERSION

ROOT = Path(__file__).resolve().parents[1]


class DesktopLifecycle(unittest.TestCase):
    def test_closed_desktop_does_not_wait(self) -> None:
        with patch.object(installer, "running_opencode_desktops", return_value={}), \
                patch.object(installer.time, "sleep") as sleep:
            installer.wait_for_opencode_desktop_exit({})
        sleep.assert_not_called()

    def test_waits_for_all_desktop_processes_without_stopping_them(self) -> None:
        with patch.object(installer, "running_opencode_desktops", side_effect=[{1: "app", 2: "server"}, {2: "server"}, {}]), \
                patch.object(installer.time, "sleep") as sleep, \
                patch.object(installer.subprocess, "run") as run:
            installer.wait_for_opencode_desktop_exit({})
        self.assertEqual(sleep.call_count, 2)
        run.assert_not_called()

    def test_timeout_prevents_downloads_and_all_install_writes(self) -> None:
        for target in ("opencode", "all"):
            with self.subTest(target=target), \
                    patch.object(installer, "running_opencode_desktops", return_value={1: "app"}), \
                    patch.object(installer.time, "monotonic", side_effect=[0, 121]), \
                    patch.object(installer, "package_profiles") as source, \
                    patch.object(installer, "install_core") as core, \
                    patch.object(installer, "create_files") as create:
                with self.assertRaisesRegex(RuntimeError, "No AMS files were changed"):
                    installer.install(target)
                source.assert_not_called()
                core.assert_not_called()
                create.assert_not_called()

    def test_codex_only_does_not_require_desktop_exit(self) -> None:
        with patch.object(installer, "wait_for_opencode_desktop_exit") as guard, \
                patch.object(installer, "install_core"):
            self.assertEqual(installer.install("codex"), 0)
        guard.assert_not_called()

    def test_process_check_distinguishes_gui_from_cli(self) -> None:
        rows = [{"id": 11, "path": "/desktop/OpenCode.exe"}, {"id": 12, "path": "/cli/opencode.exe"}]
        with patch.object(installer, "os", types.SimpleNamespace(name="nt")), \
                patch.object(installer.shutil, "which", return_value="powershell.exe"), \
                patch.object(installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(rows), "")) as run, \
                patch.object(installer, "windows_gui", side_effect=[True, False]):
            self.assertEqual(installer.running_opencode_desktops({"PSModulePath": "do-not-inherit"}), {11: "/desktop/OpenCode.exe"})
        self.assertNotIn("PSModulePath", run.call_args.kwargs["env"])
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_uninspectable_desktop_is_not_assumed_closed(self) -> None:
        with patch.object(installer, "os", types.SimpleNamespace(name="nt")), \
                patch.object(installer.shutil, "which", return_value="powershell.exe"), \
                patch.object(installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, '[{"id":11,"path":null}]', "")):
            self.assertIn(11, installer.running_opencode_desktops({}))

    def test_process_query_failure_is_not_success(self) -> None:
        with patch.object(installer, "os", types.SimpleNamespace(name="nt")), \
                patch.object(installer.shutil, "which", return_value="powershell.exe"), \
                patch.object(installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "failed")):
            with self.assertRaisesRegex(RuntimeError, "Could not inspect"):
                installer.running_opencode_desktops({})


def port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return server.getsockname()[1]


def main(desktop: Path) -> None:
    if os.name != "nt":
        raise AssertionError("Packaged Desktop test requires Windows, not a mock.")
    from playwright.sync_api import sync_playwright

    executable = desktop / "OpenCode.exe"
    if installer.desktop_version(executable) != VERSION:
        raise AssertionError("Unexpected Desktop version")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with tempfile.TemporaryDirectory(prefix="ams-desktop-session-") as directory:
        home = Path(directory).resolve()
        config = home / ".config/opencode"
        config.mkdir(parents=True)
        profiles = installer.package_profiles()
        wanted = {p["name"] for p in profiles}
        settings = config / "opencode.json"
        settings.write_text(json.dumps({
            "$schema": "https://opencode.ai/config.json",
            "enabled_providers": ["ams-test"],
            "provider": {"ams-test": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "No model inference",
                "options": {"baseURL": "http://127.0.0.1:9/v1", "apiKey": "fixture-not-a-secret"},
                "models": {p["model"]: {"name": p["model"], "reasoning": True,
                    "limit": {"context": 128000, "output": 16000}} for p in profiles}
            }}
        }), encoding="utf-8")
        before = settings.read_bytes()
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("AMS_", "OPENCODE_", "XDG_", "ELECTRON_"))}
        system = Path(os.environ["SystemRoot"]) / "System32"
        env.update(HOME=str(home), USERPROFILE=str(home),
                   APPDATA=str(home / "AppData/Roaming"), LOCALAPPDATA=str(home / "AppData/Local"),
                   AMS_SKILL_HOME=str(home / ".agents/skills"), CODEX_HOME=str(home / ".codex"),
                   OPENCODE_TEST_HOME=str(home),
                   XDG_DATA_HOME=str(home / "data"), XDG_STATE_HOME=str(home / "state"),
                   XDG_CACHE_HOME=str(home / "cache"),
                   PATH=os.pathsep.join(map(str, (desktop, Path(sys.executable).parent,
                        system / "WindowsPowerShell/v1.0", system))),
                   NO_PROXY="127.0.0.1,localhost,::1", no_proxy="127.0.0.1,localhost,::1")
        for key in ("APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "CODEX_HOME"):
            Path(env[key]).mkdir(parents=True, exist_ok=True)
        process = None
        installing = None
        with (home / "desktop.log").open("w", encoding="utf-8") as log, sync_playwright() as playwright:
            def launch():
                nonlocal process
                debug_port = port()
                process = subprocess.Popen([str(executable), f"--remote-debugging-port={debug_port}"],
                                           cwd=home, env=env, stdout=log, stderr=log)
                deadline = time.monotonic() + 90
                while True:
                    try:
                        with opener.open(f"http://127.0.0.1:{debug_port}/json/version", timeout=2):
                            break
                    except OSError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            log.flush()
                            raise AssertionError("Packaged Desktop did not start: " + (home / "desktop.log").read_text(encoding="utf-8", errors="replace"))
                        time.sleep(1)
                browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.wait_for_event("page", timeout=60000)
                page.wait_for_function("Boolean(window.api?.awaitInitialization)", timeout=60000)
                ready = page.evaluate("() => window.api.awaitInitialization()")
                if urllib.parse.urlsplit(ready["url"]).hostname not in ("127.0.0.1", "localhost", "::1"):
                    raise AssertionError("The isolated Desktop selected a nonlocal server")
                headers = {"Accept": "application/json", "x-opencode-directory": str(home)}
                if ready.get("password"):
                    credentials = (str(ready.get("username") or "opencode") + ":" + ready["password"]).encode()
                    headers["Authorization"] = "Basic " + base64.b64encode(credentials).decode()
                def get(path: str):
                    request = urllib.request.Request(ready["url"].rstrip("/") + path, headers=headers)
                    with opener.open(request, timeout=60) as response:
                        return json.load(response)
                return browser, page, get

            try:
                browser, page, get = launch()
                initial = {item["name"] for item in get("/agent") if item.get("mode") == "subagent"}
                if initial != {"general", "explore"}:
                    raise AssertionError("The pre-install Desktop fixture is not clean")
                print("Desktop before install: " + ", ".join(sorted(initial)), flush=True)
                for iteration in range(2):
                    snapshots = {p: p.read_bytes() for root in (config / "agents", home / ".agents/skills")
                                 if root.exists() for p in root.rglob("*") if p.is_file()}
                    install_log = home / f"install-{iteration}.log"
                    with install_log.open("w", encoding="utf-8") as output:
                        installing = subprocess.Popen([sys.executable, str(ROOT / "tools/install_harnesses.py"),
                            "--harness", "opencode", "--local", "--opencode-provider", "ams-test"],
                            cwd=home, env=env, stdout=output, stderr=output)
                        deadline = time.monotonic() + 40
                        while "WAITING FOR DESKTOP TO CLOSE" not in install_log.read_text(encoding="utf-8", errors="replace"):
                            if installing.poll() is not None or time.monotonic() >= deadline:
                                raise AssertionError("Installer did not detect the real open Desktop: " + install_log.read_text(encoding="utf-8", errors="replace"))
                            time.sleep(0.5)
                        if process.poll() is not None:
                            raise AssertionError("Installer stopped Desktop instead of waiting")
                        if iteration == 0 and ((config / "agents").exists() or (home / ".agents/skills").exists()):
                            raise AssertionError("Installer wrote files before Desktop exited")
                        if any(p.read_bytes() != data for p, data in snapshots.items()):
                            raise AssertionError("Reinstall changed existing files before Desktop exited")
                        # Simulate normal user window-close; no force-kill or credential access by installer.
                        page.evaluate("() => { void window.api.runDesktopMenuAction('window.close') }")
                        process.wait(timeout=30)
                        installing.wait(timeout=300)
                    text = install_log.read_text(encoding="utf-8", errors="replace")
                    print(text, flush=True)
                    if installing.returncode or "Desktop has exited. Continuing installation." not in text:
                        raise AssertionError("Installer did not resume after normal Desktop exit")
                    browser, page, get = launch()
                    names = {item["name"] for item in get("/agent")}
                    tools = get("/experimental/tool?provider=ams-test&model=gpt-5.6-sol")
                    task = next(item for item in tools if item.get("id") == "task")
                    missing = {name for name in wanted if name not in task.get("description", "")}
                    print(f"Actual reopened Desktop: {len(wanted & names)} AMS agents; Task description: {len(wanted - missing)}.", flush=True)
                    if not wanted <= names or missing:
                        raise AssertionError("Reopened Desktop did not expose all AMS agents")
                    if settings.read_bytes() != before:
                        raise AssertionError("Provider settings changed")
                print("PASS actual packaged Desktop: open-app guard, no early writes, normal close, automatic install, reopened server and Task tool expose 23 agents, reinstall; no model calls.", flush=True)
                browser.close()
            finally:
                for child in (installing, process):
                    if child is not None and child.poll() is None:
                        # Only isolated CI processes are forcibly cleaned up on a test failure.
                        subprocess.run(["taskkill.exe", "/PID", str(child.pid), "/T", "/F"], capture_output=True, timeout=30)
                        child.wait(timeout=30)


if __name__ == "__main__":
    if sys.argv[1:] == ["--unit"]:
        unittest.main(argv=[sys.argv[0]])
    else:
        main(Path(sys.argv[1]).resolve())
