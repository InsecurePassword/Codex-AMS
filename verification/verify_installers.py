#!/usr/bin/env python3
"""Transactional fixtures for the release-agnostic AMS Bash/PowerShell installers."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = "adaptive-master-subagent-orchestration"
LOCK_NAME = ".adaptive-master-subagent-orchestration.install.lock"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    command: list[str],
    environment: dict[str, str],
    expect_success: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, env=environment, text=True, capture_output=True, timeout=120)
    if expect_success and result.returncode != 0:
        raise AssertionError(
            f"command failed: {command}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if not expect_success and result.returncode == 0:
        raise AssertionError(f"command unexpectedly succeeded: {command}\nstdout:\n{result.stdout}")
    return result


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(root: Path) -> tuple[subprocess.Popen[str], str]:
    port = free_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(root)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(40):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return process, url
        except OSError:
            time.sleep(0.05)
    process.terminate()
    raise AssertionError("fixture HTTP server did not start")


def patch_bash(source: Path, destination: Path, url: str) -> None:
    text = source.read_text(encoding="utf-8")
    text, count = re.subn(
        r'^raw_base_url="[^"]+"$',
        f'raw_base_url="{url}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise AssertionError("could not patch Bash raw_base_url")
    destination.write_text(text, encoding="utf-8", newline="\n")
    destination.chmod(0o700)


def patch_powershell(source: Path, destination: Path, url: str) -> None:
    text = source.read_text(encoding="utf-8")
    text, count = re.subn(
        r'^\$RawBaseUrl = "[^"]+"$',
        f'$RawBaseUrl = "{url}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise AssertionError("could not patch PowerShell RawBaseUrl")
    destination.write_text(text, encoding="utf-8", newline="\n")


def current_host() -> str:
    if os.name == "nt":
        return os.environ.get("COMPUTERNAME") or socket.gethostname()
    result = subprocess.run(["hostname"], text=True, capture_output=True, check=True)
    return result.stdout.strip()


def write_owner(lock: Path, *, host: str, pid: int, acquired: int, token: str = "a" * 32) -> None:
    lock.mkdir(parents=True, exist_ok=False)
    text = (
        "ams-install-lock-v1\n"
        f"owner_token\t{token}\n"
        f"host\t{host}\n"
        f"pid\t{pid}\n"
        f"acquired_epoch\t{acquired}\n"
    )
    (lock / "owner.log").write_text(text, encoding="utf-8", newline="\n")


def assert_profiles(codex_home: Path) -> dict[str, str]:
    profiles = sorted((codex_home / "agents").glob("ams_*.toml"))
    if len(profiles) != 24:
        raise AssertionError(f"installed profile inventory mismatch: {len(profiles)}")
    return {path.name: sha256(path) for path in profiles}


def assert_skill(skill_home: Path) -> Path:
    skill = skill_home / SKILL
    if not skill.is_dir():
        raise AssertionError("installed skill missing")
    if (skill / "VERSION").exists():
        raise AssertionError("release identity file was installed")
    if (skill / "references/convergence-control.md").exists():
        raise AssertionError("removed convergence module was installed")
    if not (skill / "references/scope-dependency-control.md").is_file():
        raise AssertionError("scope/dependency core missing")
    if not (skill / "references/daybreak-blue.md").is_file():
        raise AssertionError("Daybreak Blue reference missing")
    if not (skill / "references/computer-use.md").is_file():
        raise AssertionError("computer-use reference missing")
    if not (skill / "assets/agent-profiles/ams_daybreak_blue_max.toml").is_file():
        raise AssertionError("Daybreak Blue profile missing")
    if not (skill / "assets/agent-profiles/ams_astra_medium.toml").is_file():
        raise AssertionError("Astra profile missing")
    return skill


def invoke(
    script: Path,
    environment: dict[str, str],
    *,
    profiles_only: bool = False,
    expect_success: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = environment.copy()
    if profiles_only:
        env["AMS_INSTALL_PROFILES_ONLY"] = "1"
    else:
        env.pop("AMS_INSTALL_PROFILES_ONLY", None)
    if os.name == "nt":
        executable = shutil.which("powershell.exe") or shutil.which("powershell")
        if not executable:
            raise AssertionError("Windows PowerShell not found")
        command = [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    else:
        executable = shutil.which("bash")
        if not executable:
            raise AssertionError("Bash not found")
        command = [executable, str(script)]
    return run(command, env, expect_success=expect_success)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary_directory:
        base = Path(temporary_directory)
        served = base / "served"
        shutil.copytree(
            ROOT,
            served,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "reports"),
        )
        server, url = start_server(served)
        try:
            home = base / "home"
            skill_home = base / "skills"
            codex_home = base / "codex"
            home.mkdir()
            skill_home.mkdir()
            codex_home.mkdir()
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "USERPROFILE": str(home),
                    "AMS_SKILL_HOME": str(skill_home),
                    "CODEX_HOME": str(codex_home),
                }
            )

            script = base / ("install-test.ps1" if os.name == "nt" else "install-test.sh")
            if os.name == "nt":
                patch_powershell(ROOT / "install.ps1", script, url)
            else:
                patch_bash(ROOT / "install.sh", script, url)

            # Profiles-only bootstrap changes only the registry and upgrades an exact recognized predecessor.
            sentinel_skill = skill_home / SKILL
            sentinel_skill.mkdir()
            (sentinel_skill / "sentinel.txt").write_text("preserve", encoding="utf-8")
            prior_profile = ROOT / "verification/fixtures/prior-profiles/ams_luna_medium.toml"
            prior_target = codex_home / "agents/ams_luna_medium.toml"
            prior_target.parent.mkdir(parents=True, exist_ok=True)
            prior_target.write_bytes(prior_profile.read_bytes())
            prior_hash = sha256(prior_target)
            result = invoke(script, environment, profiles_only=True)
            if "profile registry bootstrap only" not in result.stdout:
                raise AssertionError("profiles-only completion message missing")
            bootstrap_hashes = assert_profiles(codex_home)
            if bootstrap_hashes["ams_luna_medium.toml"] == prior_hash:
                raise AssertionError("recognized predecessor profile was not upgraded")
            if (sentinel_skill / "sentinel.txt").read_text(encoding="utf-8") != "preserve":
                raise AssertionError("profiles-only bootstrap replaced the skill")

            # Full install replaces the skill, leaves byte-identical profiles unchanged, and creates no runtime state.
            result = invoke(script, environment)
            if "Installed Adaptive Master-Subagent Orchestration." not in result.stdout:
                raise AssertionError("full-install completion message missing")
            assert_skill(skill_home)
            if bootstrap_hashes != assert_profiles(codex_home):
                raise AssertionError("full install changed byte-identical bootstrapped profiles")
            if (codex_home / "ams-runtime").exists() or (skill_home / SKILL / ".runtime").exists():
                raise AssertionError("installer created removed runtime state")

            # Reinstall is idempotent.
            installed_skill = skill_home / SKILL
            skill_hashes = {
                path.relative_to(installed_skill).as_posix(): sha256(path)
                for path in installed_skill.rglob("*")
                if path.is_file()
            }
            invoke(script, environment)
            if skill_hashes != {
                path.relative_to(installed_skill).as_posix(): sha256(path)
                for path in installed_skill.rglob("*")
                if path.is_file()
            }:
                raise AssertionError("idempotent reinstall changed core bytes")
            if bootstrap_hashes != assert_profiles(codex_home):
                raise AssertionError("idempotent reinstall changed profile bytes")

            # Customized profile blocks before skill replacement and remains unchanged.
            custom = codex_home / "agents/ams_terra_low.toml"
            custom.write_text(
                custom.read_text(encoding="utf-8") + "# user customization\n",
                encoding="utf-8",
                newline="\n",
            )
            custom_hash = sha256(custom)
            sentinel = installed_skill / "local-sentinel.txt"
            sentinel.write_text("keep", encoding="utf-8")
            invoke(script, environment, expect_success=False)
            if sha256(custom) != custom_hash or sentinel.read_text(encoding="utf-8") != "keep":
                raise AssertionError("profile collision refusal mutated profile or skill")
            custom.write_bytes((served / SKILL / "assets/agent-profiles/ams_terra_low.toml").read_bytes())
            sentinel.unlink()

            lock = codex_home / LOCK_NAME
            host = current_host()
            now = int(time.time())

            # A live same-host owner blocks without mutation.
            write_owner(lock, host=host, pid=os.getpid(), acquired=now)
            before = assert_profiles(codex_home)
            invoke(script, environment, expect_success=False)
            if before != assert_profiles(codex_home):
                raise AssertionError("active-lock refusal mutated profiles")
            shutil.rmtree(lock)

            # A stale same-host dead owner is quarantined and recovered.
            write_owner(lock, host=host, pid=2_147_483_647, acquired=now - 120, token="b" * 32)
            invoke(script, environment)
            if lock.exists():
                raise AssertionError("stale dead-owner lock remained after successful transaction")
            if list(codex_home.glob(f"{LOCK_NAME}.stale.*")):
                raise AssertionError("stale-lock quarantine residue remained")

            # An old ownerless crash lock is also recoverable.
            lock.mkdir()
            old = now - 120
            os.utime(lock, (old, old))
            invoke(script, environment, profiles_only=True)
            if lock.exists():
                raise AssertionError("stale ownerless lock remained after recovery")

            # Foreign-host and malformed lock records fail closed.
            write_owner(lock, host="different-host", pid=2_147_483_647, acquired=now - 120, token="c" * 32)
            invoke(script, environment, expect_success=False)
            shutil.rmtree(lock)
            lock.mkdir()
            (lock / "owner.log").write_text("malformed\n", encoding="utf-8", newline="\n")
            invoke(script, environment, expect_success=False)
            shutil.rmtree(lock)

            # A corrupted served manifest fails before replacement.
            original_manifest = (served / "install-manifest.txt").read_bytes()
            lines = original_manifest.decode("utf-8").splitlines()
            digest, length, path = lines[-1].split("\t")
            lines[-1] = f"{'0' * 64}\t{length}\t{path}"
            (served / "install-manifest.txt").write_text(
                "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
            )
            marker = installed_skill / "manifest-refusal.txt"
            marker.write_text("keep", encoding="utf-8")
            invoke(script, environment, expect_success=False)
            if marker.read_text(encoding="utf-8") != "keep":
                raise AssertionError("manifest refusal replaced installed skill")
            (served / "install-manifest.txt").write_bytes(original_manifest)

            print(
                "PASS: profiles-only, full install, idempotence, collision refusal, "
                "active/stale/malformed lock handling, and manifest refusal"
            )
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
