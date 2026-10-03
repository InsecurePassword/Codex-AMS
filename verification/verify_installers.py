#!/usr/bin/env python3
"""Transactional fixtures for the release-agnostic AMS Bash/PowerShell installers."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = "adaptive-master-subagent-orchestration"
LOCK_NAME = ".adaptive-master-subagent-orchestration.install.lock"


def frozen_profiles() -> dict[str, bytes]:
    """Exact ordinary profiles in official d4819892, independent of candidate assets."""
    result = {}
    prompt = ("Follow the assigned task and its role, scope, and permissions. Preserve existing work "
              "and secrets. Return concise results, validation, and unresolved blockers to the assigning agent.")
    for family, model in (("sol", "gpt-5.6-sol"), ("terra", "gpt-5.6-terra"),
                          ("luna", "gpt-5.6-luna"), ("astra", "gpt-6-astra"),
                          ("spark", "gpt-5.3-codex-spark")):
        for effort in (("low", "medium", "high") if family == "spark" else ("low", "medium", "high", "xhigh", "max")):
            name = f"ams_{family}_{effort}"
            result[name + ".toml"] = (
                '# managed-by: adaptive-master-subagent-orchestration\n# profile-schema: 3\n'
                f'name = "{name}"\ndescription = "{family.title()} with {effort} reasoning effort."\n'
                f'model = "{model}"\nmodel_reasoning_effort = "{effort}"\n'
                f'developer_instructions = """{prompt}"""\n'
            ).encode("utf-8")
    return result


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


def start_server(root: Path) -> tuple[ThreadingHTTPServer, str]:
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"


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
    if len(profiles) != 36:
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
    local: bool = False,
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
    if local:
        command.append("-Local" if os.name == "nt" else "--local")
    return run(command, env, expect_success=expect_success)


def preservation_races(base: Path, script: Path, environment: dict[str, str], served: Path) -> None:
    """Portable boundary probes for the four audited failures and their tree/identity equivalents.

    Injection copies modify only temporary test scripts. The shipped installers have
    comments at these boundaries, not environment-controlled production fault hooks.
    """
    current = {p.name: p.read_bytes() for p in (served / SKILL / 'assets/agent-profiles').glob('*.toml')}
    old = frozen_profiles()
    cases = (
        ('rollback_created_drift', 'AMS_TRANSACTION_BEFORE_COMMIT', 'spark', 'custom', True),
        ('rollback_replaced_drift', 'AMS_TRANSACTION_BEFORE_COMMIT', 'old', 'custom', True),
        ('retirement_drift_rolls_back', 'AMS_RETIRED_AFTER_BACKUP', 'old', 'retirement_backup', False),
        ('publish_drift', 'AMS_SKILL_AFTER_PUBLICATION', 'current', 'custom', False),
        ('absent_profile_claimed', 'AMS_PROFILE_BEFORE_PUBLICATION', 'none', 'custom', False),
        ('preflight_identity_replaced', 'AMS_TRANSACTION_PREFLIGHT_COMPLETE', 'current', 'same_bytes', False),
        ('published_identity_replaced', 'AMS_TRANSACTION_BEFORE_COMMIT', 'old', 'same_bytes', False),
        ('published_profile_redirected', 'AMS_TRANSACTION_BEFORE_COMMIT', 'old', 'redirect_profile', False),
        ('retired_profile_recreated', 'AMS_TRANSACTION_BEFORE_COMMIT', 'old', 'retirement_recreate', False),
        ('skill_changed', 'AMS_TRANSACTION_BEFORE_COMMIT', 'old', 'skill_edit', False),
        ('skill_identity_replaced', 'AMS_TRANSACTION_BEFORE_COMMIT', 'old', 'skill_same_bytes', False),
        ('skill_redirected', 'AMS_TRANSACTION_BEFORE_COMMIT', 'old', 'skill_redirect', False),
        ('absent_skill_claimed', 'AMS_SKILL_BEFORE_PUBLICATION', 'none', 'skill_claim', False),
    )
    for name, boundary, seed, operation, force_failure in cases:
        case = base / name
        home = case / 'home'
        agents = case / 'codex/agents'
        skill_home = case / 'skills'
        destination = skill_home / SKILL
        home.mkdir(parents=True)
        agents.mkdir(parents=True)
        skill_home.mkdir()
        if seed == 'current': data = current
        elif seed == 'old': data = old
        elif seed == 'spark': data = {'ams_spark_high.toml': old['ams_spark_high.toml']}
        else: data = {}
        for filename, raw in data.items(): (agents / filename).write_bytes(raw)
        if operation != 'skill_claim':
            destination.mkdir()
            (destination / 'old-skill.txt').write_bytes(b'original skill tree\n')
        settings = agents.parent / 'config.toml'
        settings.write_bytes(b'model = "user-selected"\n')
        if operation in ('redirect_profile', 'skill_redirect'):
            probe = case / 'symlink-probe'
            try: probe.symlink_to(home, target_is_directory=True)
            except OSError:
                print(f'SKIP {name}: this runner cannot create symlinks')
                continue
            probe.unlink()
        mutator = case / 'concurrent-writer.py'
        mutator.write_text('import os, pathlib, shutil, sys\n'
            + 'case = pathlib.Path(' + repr(str(case)) + ')\n'
            + 'operation = ' + repr(operation) + '\n'
            + 'boundary = ' + repr(boundary) + '\n' + r"""
if (case / 'mutated').exists(): raise SystemExit(0)
if boundary == 'AMS_PROFILE_BEFORE_PUBLICATION' and sys.argv[1] != 'ams_sol_low.toml': raise SystemExit(0)
if boundary == 'AMS_RETIRED_AFTER_BACKUP' and sys.argv[1] != 'ams_spark_high.toml': raise SystemExit(0)
agents = case / 'codex/agents'
profile = agents / 'ams_sol_low.toml'
skill = case / 'skills/adaptive-master-subagent-orchestration'
custom = b'custom work written concurrently\n'
if operation in ('custom', 'retirement_backup'):
    profile.write_bytes(custom)
elif operation == 'same_bytes':
    replacement = case / 'replacement.toml'
    replacement.write_bytes(profile.read_bytes())
    os.replace(replacement, profile)
elif operation == 'redirect_profile':
    outside = case / 'unowned-profile.toml'
    outside.write_bytes(custom)
    profile.unlink()
    profile.symlink_to(outside)
elif operation == 'retirement_recreate':
    (agents / 'ams_spark_high.toml').write_bytes(custom)
elif operation == 'skill_edit':
    (skill / 'concurrent.txt').write_bytes(custom)
elif operation == 'skill_same_bytes':
    replacement = case / 'replacement-skill'
    shutil.copytree(skill, replacement)
    os.rename(skill, case / 'actor-kept-skill')
    os.rename(replacement, skill)
elif operation == 'skill_redirect':
    outside = case / 'unowned-skill'
    outside.mkdir()
    (outside / 'concurrent.txt').write_bytes(custom)
    os.rename(skill, case / 'actor-kept-skill')
    skill.symlink_to(outside, target_is_directory=True)
elif operation == 'skill_claim':
    skill.mkdir()
    (skill / 'concurrent.txt').write_bytes(custom)
if operation == 'retirement_backup':
    backup = next(agents.glob('.ams-profiles*/originals/ams_spark_high.toml'))
    backup.write_bytes(backup.read_bytes() + b'# concurrent Spark customization\n')
(case / 'mutated').write_bytes(custom)
""", encoding='utf-8', newline='\n')
        text = script.read_text(encoding='utf-8')
        marker = '# ' + boundary
        if text.count(marker) != 1:
            raise AssertionError(f'{name}: ambiguous or missing test boundary')
        if os.name == 'nt':
            quoted = lambda value: "'" + str(value).replace("'", "''") + "'"
            action = '& ' + quoted(sys.executable) + ' ' + quoted(mutator) + ' $ProfileFile'
            if force_failure: action += '\n    throw "Injected later transaction failure"'
        else:
            action = shlex.quote(sys.executable) + ' ' + shlex.quote(str(mutator)) + ' "${profile_file:-}"'
            if force_failure: action += '\nfail "Injected later transaction failure"'
        injected = case / script.name
        injected.write_text(text.replace(marker, marker + '\n' + action), encoding='utf-8', newline='\n')
        env = environment | {'HOME': str(home), 'USERPROFILE': str(home),
                             'AMS_SKILL_HOME': str(skill_home), 'CODEX_HOME': str(agents.parent)}
        result = invoke(injected, env, expect_success=False)
        if not (case / 'mutated').exists():
            raise AssertionError(f'{name}: mutation did not run\n{result.stdout}\n{result.stderr}')
        profile = agents / 'ams_sol_low.toml'
        custom = b'custom work written concurrently\n'
        if operation in ('custom', 'retirement_backup') and profile.read_bytes() != custom:
            raise AssertionError(f'{name}: concurrent custom profile was lost')
        if operation == 'same_bytes' and profile.read_bytes() != current[profile.name]:
            raise AssertionError(f'{name}: same-byte replacement was overwritten by rollback')
        if operation == 'redirect_profile' and (not profile.is_symlink() or (case / 'unowned-profile.toml').read_bytes() != custom):
            raise AssertionError(f'{name}: rollback touched an unowned redirect')
        if operation == 'retirement_recreate' and (agents / 'ams_spark_high.toml').read_bytes() != custom:
            raise AssertionError(f'{name}: recreated retired profile was overwritten')
        if operation in ('skill_edit', 'skill_redirect', 'skill_claim') and (destination / 'concurrent.txt').read_bytes() != custom:
            raise AssertionError(f'{name}: concurrent skill work was lost')
        if operation == 'skill_same_bytes' and (destination / 'SKILL.md').read_bytes() != (served / SKILL / 'SKILL.md').read_bytes():
            raise AssertionError(f'{name}: same-byte replacement skill was overwritten')
        if operation == 'skill_redirect' and not destination.is_symlink():
            raise AssertionError(f'{name}: redirected skill was removed')
        if operation == 'skill_claim' and (destination / SKILL).exists():
            raise AssertionError(f'{name}: skill publication nested inside a conflicting directory')
        if settings.read_bytes() != b'model = "user-selected"\n':
            raise AssertionError(f'{name}: settings changed')
        needs_backup = name in ('rollback_replaced_drift', 'retirement_drift_rolls_back', 'published_identity_replaced',
                                'published_profile_redirected', 'retired_profile_recreated', 'skill_changed',
                                'skill_identity_replaced', 'skill_redirected')
        if needs_backup:
            backup_name = 'ams_spark_high.toml' if operation == 'retirement_recreate' else 'ams_sol_low.toml'
            if operation.startswith('skill_'):
                backups = list(skill_home.glob('.ams-install*/skill-backup/' + SKILL + '/old-skill.txt'))
                if not backups or backups[0].read_bytes() != b'original skill tree\n':
                    raise AssertionError(f'{name}: recoverable old skill backup was not retained')
            else:
                backups = list(agents.glob('.ams-profiles*/originals/' + backup_name))
                if not backups or backups[0].read_bytes() != old[backup_name]:
                    raise AssertionError(f'{name}: recoverable predecessor backup was not retained')
            if 'Transaction backups retained at:' not in result.stdout + result.stderr:
                raise AssertionError(f'{name}: incomplete recovery did not identify retained backups')
        print(f'PASS preservation race: {name}')


def hardlink_prerequisite(base: Path, script: Path, environment: dict[str, str]) -> None:
    """Bash must detect unsupported registry hard links before any live replacement."""
    if os.name == 'nt':
        return  # The PowerShell installer uses native create-only moves, not hard links.
    home, skill_home, codex_home = (base / name for name in ('home', 'skills', 'codex'))
    home.mkdir(parents=True)
    agents = codex_home / 'agents'
    agents.mkdir(parents=True)
    skill = skill_home / SKILL
    skill.mkdir(parents=True)
    (skill / 'user-work.txt').write_bytes(b'preserve installed skill\n')
    (agents / 'ams_sol_low.toml').write_bytes(frozen_profiles()['ams_sol_low.toml'])
    (codex_home / 'config.toml').write_bytes(b'model = "user-selected"\n')
    roots = (skill_home, codex_home)
    before = {p: p.read_bytes() for root in roots for p in root.rglob('*') if p.is_file()}
    directories = {p for root in roots for p in root.rglob('*') if p.is_dir()}
    binary = base / 'bin'
    binary.mkdir()
    blocked = binary / 'ln'
    blocked.write_text('#!/bin/sh\nprintf "fixture: filesystem does not support hard links\\n" >&2\nexit 91\n', encoding='utf-8')
    blocked.chmod(0o700)
    env = environment | {'HOME': str(home), 'USERPROFILE': str(home), 'AMS_SKILL_HOME': str(skill_home),
                         'CODEX_HOME': str(codex_home), 'PATH': str(binary) + os.pathsep + environment.get('PATH', '')}
    env.pop('AMS_INSTALL_SKILL_ONLY', None)
    result = invoke(script, env, expect_success=False)
    if 'requires hard links' not in result.stdout + result.stderr:
        raise AssertionError('Unsupported-hard-link failure did not explain its prerequisite')
    after = {p: p.read_bytes() for root in roots for p in root.rglob('*') if p.is_file()}
    after_directories = {p for root in roots for p in root.rglob('*') if p.is_dir()}
    if after != before or directories != after_directories:
        raise AssertionError('Unsupported hard links changed live files or left transaction residue')
    print('PASS unsupported hard links fail before live mutation')


def configured_root_aliases(base: Path, script: Path, environment: dict[str, str]) -> None:
    """Root ancestor aliases work; root leaves and descendants remain guarded."""
    if os.name == "nt":
        return  # This fixture exercises Bash's physical-root anchoring.
    base.mkdir()
    physical = base.resolve() / "physical"
    physical.mkdir()
    alias = base.resolve() / "alias"
    alias.symlink_to(physical, target_is_directory=True)
    env = environment | {"AMS_SKILL_HOME": str(alias / "skills"), "CODEX_HOME": str(alias / "codex")}
    for _ in range(2):
        invoke(script, env)
        assert_profiles(physical / "codex")
        if (physical / "skills" / SKILL / "SKILL.md").read_bytes() != (ROOT / SKILL / "SKILL.md").read_bytes():
            raise AssertionError("Alias-root skill installation or reinstall failed")
    for kind in ("skill-root", "codex-root", "agents", "profile"):
        case = physical / kind
        case.mkdir()
        outside = case / "outside"
        outside.mkdir()
        (outside / "sentinel").write_bytes(b"unrelated work")
        skills, codex = case / "skills", case / "codex"
        suffix = ""
        if kind == "skill-root":
            skills.symlink_to(outside, target_is_directory=True)
            suffix = "/"  # Root-leaf checks also cover trailing path syntax.
        elif kind == "codex-root":
            codex.symlink_to(outside, target_is_directory=True)
            suffix = "/."
        elif kind == "agents":
            codex.mkdir()
            (codex / "agents").symlink_to(outside, target_is_directory=True)
        else:
            (codex / "agents").mkdir(parents=True)
            target = outside / "profile.toml"
            target.write_bytes((ROOT / SKILL / "assets/agent-profiles/ams_sol_low.toml").read_bytes())
            (codex / "agents/ams_sol_low.toml").symlink_to(target)
        before = {p.name: p.read_bytes() for p in outside.iterdir()}
        selected = environment | {"AMS_SKILL_HOME": str(skills) + (suffix if kind == "skill-root" else ""),
                                  "CODEX_HOME": str(codex) + (suffix if kind == "codex-root" else "")}
        result = invoke(script, selected, expect_success=False)
        if "redirected" not in result.stdout + result.stderr:
            raise AssertionError(f"Missing redirected-path refusal for {kind}")
        if {p.name: p.read_bytes() for p in outside.iterdir()} != before:
            raise AssertionError(f"Redirected {kind} changed unrelated files")
    print("PASS configured-root ancestor aliases install/reinstall; root and descendant redirects refused")


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

            local_script = served / ("install.ps1" if os.name == "nt" else "install.sh")
            patch = patch_powershell if os.name == "nt" else patch_bash
            patch(ROOT / local_script.name, local_script, "http://127.0.0.1:1")
            local_env = environment | {
                "AMS_SKILL_HOME": str(base / "local skills"),
                "CODEX_HOME": str(base / "local codex"),
            }
            local_skill = Path(local_env["AMS_SKILL_HOME"]) / SKILL
            local_codex = Path(local_env["CODEX_HOME"])
            invoke(local_script, local_env, profiles_only=True, local=True)
            if local_skill.exists() or assert_profiles(local_codex) != bootstrap_hashes:
                raise AssertionError("local profiles-only install mismatch")
            for _ in range(2):
                invoke(local_script, local_env, local=True)
                actual = {p.relative_to(local_skill).as_posix(): sha256(p)
                          for p in local_skill.rglob("*") if p.is_file()}
                if actual != skill_hashes or assert_profiles(local_codex) != bootstrap_hashes:
                    raise AssertionError("local full install/reinstall byte mismatch")
            local_profile = local_codex / "agents/ams_terra_low.toml"
            original_profile = local_profile.read_bytes()
            local_profile.write_bytes(original_profile + b"# user customization\n")
            invoke(local_script, local_env, local=True, expect_success=False)
            if local_profile.read_bytes() != original_profile + b"# user customization\n":
                raise AssertionError("local install replaced a customized profile")
            local_profile.write_bytes(original_profile)
            (served / "install-manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            invoke(local_script, local_env, local=True, expect_success=False)
            if actual != {p.relative_to(local_skill).as_posix(): sha256(p)
                          for p in local_skill.rglob("*") if p.is_file()}:
                raise AssertionError("local manifest refusal changed installed files")
            (served / "install-manifest.txt").write_bytes(original_manifest)

            # Official frozen-baseline upgrade and retired Spark removal share rollback.
            upgrade_codex = base / "upgrade-codex"
            upgrade_skill = base / "upgrade-skills"
            agents = upgrade_codex / "agents"
            agents.mkdir(parents=True)
            old = frozen_profiles()
            for name, data in old.items():
                (agents / name).write_bytes(data)
            settings = upgrade_codex / "config.toml"
            settings.write_bytes(b'model = "unchanged"\n')
            keep = upgrade_skill / SKILL / "sentinel.txt"
            keep.parent.mkdir(parents=True)
            keep.write_bytes(b"old skill")
            upgrade_env = environment | {"CODEX_HOME": str(upgrade_codex), "AMS_SKILL_HOME": str(upgrade_skill)}
            failing = base / ("rollback.ps1" if os.name == "nt" else "rollback.sh")
            text = script.read_text(encoding="utf-8")
            anchor = "    $Committed = $true\n" if os.name == "nt" else "\ncommitted=1\n"
            failure = '    throw "Injected transaction failure"\n' if os.name == "nt" else '\nfail "Injected transaction failure"\n'
            if text.count(anchor) != 1:
                raise AssertionError("Could not inject a post-retirement transaction failure")
            failing.write_text(text.replace(anchor, failure), encoding="utf-8", newline="\n")
            invoke(failing, upgrade_env, expect_success=False)
            if {p.name: p.read_bytes() for p in agents.glob("*.toml")} != old or keep.read_bytes() != b"old skill":
                raise AssertionError("Failed upgrade did not restore every predecessor, retired Spark, and prior skill")
            invoke(script, upgrade_env)
            assert_profiles(upgrade_codex)
            if list(agents.glob("ams_spark_*.toml")):
                raise AssertionError("Official retired Spark profiles survived upgrade")
            if settings.read_bytes() != b'model = "unchanged"\n':
                raise AssertionError("Upgrade rewrote general Codex settings")
            # Marker-only custom Spark, directories, and unrelated files survive retirement.
            custom_spark = agents / "ams_spark_medium.toml"
            custom_spark.write_bytes(b"# managed-by: adaptive-master-subagent-orchestration\n# custom\n")
            directory_spark = agents / "ams_spark_high.toml"
            directory_spark.mkdir()
            (directory_spark / "keep").write_bytes(b"user data")
            (agents / "ams_spark_low.toml").write_bytes(old["ams_spark_low.toml"])
            invoke(script, upgrade_env)
            if (agents / "ams_spark_low.toml").exists() or custom_spark.read_bytes() != b"# managed-by: adaptive-master-subagent-orchestration\n# custom\n" or (directory_spark / "keep").read_bytes() != b"user data":
                raise AssertionError("Retirement ownership boundary failed")

            # A retired symlink is unowned even when its referent has official bytes.
            outside = base / "unowned-spark.toml"
            outside.write_bytes(old["ams_spark_low.toml"])
            redirected_spark = agents / "ams_spark_low.toml"
            try:
                redirected_spark.symlink_to(outside)
            except OSError:
                pass  # Windows runners may not grant symlink creation.
            else:
                invoke(script, upgrade_env)
                if not redirected_spark.is_symlink() or outside.read_bytes() != old["ams_spark_low.toml"]:
                    raise AssertionError("Retirement followed or removed an unowned Spark redirect")

            configured_root_aliases(base / "root-alias-fixture", script, environment)
            hardlink_prerequisite(base / "hardlink-fixture", script, environment)
            preservation_races(base / "race-fixtures", script, environment, served)

            print(
                "PASS: offline profiles-only/install/reinstall/collision/manifest checks; "
                "profiles-only, full install, idempotence, collision refusal, "
                "active/stale/malformed lock handling, manifest refusal, exact baseline upgrade, "
                "Spark retirement, custom preservation, and transactional rollback"
            )
        finally:
            server.shutdown()
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
