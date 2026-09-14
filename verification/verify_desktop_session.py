#!/usr/bin/env python3
"""Exercise the actual packaged Desktop server, not the standalone CLI registry."""
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
import urllib.request
import urllib.parse

from verify_desktop_bootstrap import installer, VERSION

ROOT = Path(__file__).resolve().parents[1]


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
        result = subprocess.run([sys.executable, str(ROOT / "tools/install_harnesses.py"),
                                 "--harness", "opencode", "--local", "--opencode-provider", "ams-test"],
                                cwd=home, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=300)
        print(result.stdout, flush=True)
        if result.returncode:
            raise AssertionError(result.stderr)
        debug_port = port()
        with (home / "desktop.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(executable), f"--remote-debugging-port={debug_port}"],
                                       cwd=home, env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 90
                while True:
                    try:
                        with opener.open(f"http://127.0.0.1:{debug_port}/json/version", timeout=2):
                            break
                    except OSError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            raise AssertionError("Packaged Desktop did not start its test debugging endpoint")
                        time.sleep(1)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
                    context = browser.contexts[0]
                    page = context.pages[0] if context.pages else context.wait_for_event("page", timeout=60000)
                    page.wait_for_function("Boolean(window.api?.awaitInitialization)", timeout=60000)
                    ready = page.evaluate("() => window.api.awaitInitialization()")
                    address = urllib.parse.urlsplit(ready["url"])
                    if address.hostname not in ("127.0.0.1", "localhost", "::1"):
                        raise AssertionError("The isolated Desktop selected a nonlocal server")
                    headers = {"Accept": "application/json", "x-opencode-directory": str(home)}
                    if ready.get("password"):
                        credentials = (str(ready.get("username") or "opencode") + ":" + ready["password"]).encode()
                        headers["Authorization"] = "Basic " + base64.b64encode(credentials).decode()
                    def get(path: str):
                        request = urllib.request.Request(ready["url"].rstrip("/") + path, headers=headers)
                        with opener.open(request, timeout=60) as response:
                            return json.load(response)
                    agents = get("/agent")
                    names = {item["name"] for item in agents}
                    wanted = {p["name"] for p in profiles}
                    print("Actual Desktop /agent names: " + ", ".join(sorted(names)), flush=True)
                    if not wanted <= names:
                        raise AssertionError("Desktop server missing: " + ", ".join(sorted(wanted - names)))
                    print("Desktop config agent count: " + str(len(get("/config").get("agent", {}))), flush=True)
                    tools = get("/experimental/tool?provider=ams-test&model=gpt-5.6-sol")
                    task = next(item for item in tools if item.get("id") == "task")
                    description = task.get("description", "")
                    missing = {name for name in wanted if name not in description}
                    print("Desktop task description AMS matches: " + str(len(wanted - missing)), flush=True)
                    if missing:
                        raise AssertionError("Desktop Task tool missing: " + ", ".join(sorted(missing)))
                    if settings.read_bytes() != before:
                        raise AssertionError("Provider settings changed")
                    print("PASS actual packaged Desktop server and Task tool expose all 23 AMS agents; no model calls.", flush=True)
                    browser.close()
            finally:
                subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=30)
                process.wait(timeout=30)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
