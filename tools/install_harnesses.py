#!/usr/bin/env python3
"""Install shared AMS instructions and native OpenCode/Pi model presets from a local package."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

if sys.version_info < (3, 11):
    raise SystemExit("OpenCode/Pi installation requires Python 3.11 or newer.")
import tomllib

ROOT = Path(__file__).resolve().parents[1]
SKILL = "adaptive-master-subagent-orchestration"
MARKER = "<!-- managed-by: adaptive-master-subagent-orchestration -->"


def safe_path(path: Path) -> None:
    """Reject redirected targets without changing any filesystem permissions."""
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Redirected installation path: {part}")
        if part != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"Installation parent is not a directory: {part}")


def home_path(variable: str, default: Path) -> Path:
    return Path(os.path.abspath(Path(os.environ.get(variable) or default).expanduser()))


def package_profiles() -> list[dict[str, str]]:
    """Verify the entire local manifest before translating any model profiles."""
    manifest = (ROOT / "install-manifest.txt").read_bytes()
    if not manifest.startswith(b"ams-install-manifest-v1\n") or b"\r" in manifest:
        raise ValueError("Invalid local installation manifest.")
    entries: set[str] = set()
    profiles = []
    for row in manifest.decode("utf-8").splitlines()[1:]:
        digest, length, name = row.split("\t")
        parts = name.split("/")
        if (parts[0] != SKILL or any(p in ("", ".", "..") for p in parts)
                or not re.fullmatch(r"[A-Za-z0-9._/-]+", name) or name in entries):
            raise ValueError(f"Unsafe or duplicate manifest path: {name}")
        path = ROOT / name
        safe_path(path)
        data = path.read_bytes()
        if len(data) != int(length) or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Local package integrity check failed: {name}")
        entries.add(name)
        if path.parent.name == "agent-profiles" and path.suffix == ".toml":
            profile = tomllib.loads(data.decode("utf-8"))
            if profile["name"] != path.stem:
                raise ValueError(f"Profile name mismatch: {name}")
            if path.stem != "ams_daybreak_blue_max":
                profiles.append(profile)
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / SKILL).rglob("*") if p.is_file()}
    if entries != actual:
        raise ValueError("Local core membership does not match the manifest.")
    return profiles


def cli(harness: str, arguments: list[str], *, env: dict[str, str]) -> str:
    executable = shutil.which(harness)
    if not executable:
        raise ValueError(f"{harness} is not on PATH. Install the harness first.")
    result = subprocess.run([executable, *arguments], cwd=Path.home(), env=env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if result.returncode:
        raise RuntimeError(f"{harness} {' '.join(arguments)} failed (exit {result.returncode}); no model was invoked.")
    return re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)


def catalog(harness: str, provider: str, env: dict[str, str]) -> set[str]:
    output = cli(harness, ["models"] if harness == "opencode" else ["--list-models"], env=env)
    models: set[str] = set()
    for line in output.splitlines():
        fields = line.split()
        if harness == "opencode" and len(fields) == 1 and fields[0].startswith(provider + "/"):
            models.add(fields[0].split("/", 1)[1])
        elif harness == "pi" and len(fields) >= 2 and fields[0] == provider:
            models.add(fields[1])
    return models


def pi_package(pi_home: Path) -> bool:
    settings = pi_home / "settings.json"
    if not settings.exists():
        return False
    data = json.loads(settings.read_text(encoding="utf-8-sig"))
    for item in data.get("packages", []):
        source = item.get("source", "") if isinstance(item, dict) else item
        if isinstance(source, str) and (re.fullmatch(r"npm:pi-subagents(?:@[^\s]+)?", source)
                                       or source.startswith("git:github.com/nicobailon/pi-subagents")):
            if isinstance(item, dict) and item.get("extensions") == []:
                raise ValueError("pi-subagents extensions are disabled; enable them with pi config before installing AMS.")
            return True
    return False


def render(profile: dict[str, str], harness: str, provider: str) -> bytes:
    fields = {
        "description": profile["description"],
        "model": f"{provider}/{profile['model']}",
    }
    if harness == "opencode":
        fields.update(mode="subagent", reasoningEffort=profile["model_reasoning_effort"])
    else:
        fields.update(name=profile["name"], thinking=profile["model_reasoning_effort"], systemPromptMode="append")
    # JSON-quoted strings are valid YAML; no YAML dependency or provider settings edits.
    frontmatter = "\n".join(f"{key}: {json.dumps(value)}" for key, value in fields.items())
    return (f"---\n{frontmatter}\n---\n{MARKER}\n\n{profile['developer_instructions'].strip()}\n").encode("utf-8")


def preflight(files: dict[Path, bytes]) -> None:
    for path, data in files.items():
        safe_path(path)
        if path.exists() and (not path.is_file() or path.read_bytes() != data):
            raise ValueError(f"Preserving differing agent file: {path}. Reconcile it before reinstalling.")


def create_files(files: dict[Path, bytes], created: list[tuple[Path, tuple[int, int], bytes]]) -> None:
    for path, data in files.items():
        safe_path(path)
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError(f"Agent changed after preflight: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".ams-install-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            identity = Path(temporary).stat()
            # Link is create-only on Windows and Unix; it never overwrites another actor's file.
            os.link(temporary, path)
            created.append((path, (identity.st_dev, identity.st_ino), data))
        finally:
            Path(temporary).unlink(missing_ok=True)


def rollback(created: list[tuple[Path, tuple[int, int], bytes]]) -> None:
    for path, identity, data in reversed(created):
        try:
            info = path.lstat()
            if (stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == identity
                    and path.read_bytes() == data):
                path.unlink()
        except OSError:
            pass


def install_core(targets: set[str], env: dict[str, str]) -> None:
    native_env = env.copy()
    native_env.pop("AMS_INSTALL_SKILL_ONLY", None)
    if "codex" not in targets:
        if native_env.get("AMS_INSTALL_PROFILES_ONLY") == "1":
            return
        native_env["AMS_INSTALL_SKILL_ONLY"] = "1"
    if os.name == "nt":
        executable = shutil.which("powershell.exe")
        if not executable:
            raise ValueError("Windows PowerShell is required for the existing core installer.")
        command = [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install.ps1"), "-Local"]
        native_env.pop("PSModulePath", None)
    else:
        command = ["bash", str(ROOT / "install.sh"), "--local"]
    subprocess.run(command, cwd=ROOT, env=native_env, check=True, timeout=300)


def install(harness: str, opencode_provider: str, pi_provider: str, install_pi: bool) -> None:
    targets = {"codex", "opencode", "pi"} if harness == "all" else {harness}
    if install_pi and "pi" not in targets:
        raise ValueError("Installing pi-subagents requires the pi or all target.")
    env = os.environ.copy()
    if env.get("AMS_INSTALL_PROFILES_ONLY", "1") != "1":
        raise ValueError("AMS_INSTALL_PROFILES_ONLY must be unset or exactly 1.")
    providers = {"opencode": opencode_provider, "pi": pi_provider}
    for provider in providers.values():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", provider):
            raise ValueError("Provider names may contain only letters, digits, dot, underscore, and hyphen.")
    profiles = package_profiles()
    pi_home = home_path("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent")
    opencode_home = home_path("OPENCODE_CONFIG_DIR", home_path("XDG_CONFIG_HOME", Path.home() / ".config") / "opencode")
    homes = {"opencode": opencode_home, "pi": pi_home}
    env["PI_CODING_AGENT_DIR"] = str(pi_home)
    env["PI_OFFLINE"] = "1"
    files: dict[Path, bytes] = {}
    summaries: list[str] = []
    for target in sorted(targets - {"codex"}):
        available = catalog(target, providers[target], env)
        selected = [p for p in profiles if p["model"] in available]
        if not selected:
            raise ValueError(f"No AMS models listed for {target} provider {providers[target]!r}. Configure that provider or select its exact provider ID; no model substitution was made.")
        for profile in selected:
            path = homes[target] / "agents" / (profile["name"] + ".md")
            if path in files:
                raise ValueError("OpenCode and Pi must have separate agent directories.")
            files[path] = render(profile, target, providers[target])
        missing = sorted({p["model"] for p in profiles} - available)
        summaries.append(f"{target}: {len(selected)} native agent presets in {homes[target] / 'agents'}")
        if missing:
            summaries.append(f"{target}: not advertised by this provider, not installed: {', '.join(missing)}")
    preflight(files)
    if "pi" in targets and not pi_package(pi_home):
        if not install_pi:
            raise ValueError("Pi requires pi-subagents. Re-run with -InstallPiSubagents (PowerShell) or --install-pi-subagents (Bash) to install it through pi; this explicitly permits that package download.")
        package_env = env.copy()
        package_env.pop("PI_OFFLINE", None)
        cli("pi", ["install", "npm:pi-subagents"], env=package_env)
        if not pi_package(pi_home):
            raise RuntimeError("Pi did not register pi-subagents; no AMS files were installed.")
    created: list[tuple[Path, tuple[int, int], bytes]] = []
    try:
        create_files(files, created)
        install_core(targets, env)
        preflight(files)
        if any(not p.is_file() or p.read_bytes() != data for p, data in files.items()):
            raise ValueError("Final native agent verification failed.")
    except BaseException:
        rollback(created)
        raise
    for summary in summaries:
        print(summary)
    print("Selected harness installation complete. Restart selected harnesses; in Pi run /subagents-doctor.")
    print("Catalog membership and file bytes checked, not model access or live inference. Daybreak and optional companions remain Codex-only.")
    print("Existing models, credentials, permissions, compaction, and AMS project settings were not changed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=("opencode", "pi", "all"), required=True)
    parser.add_argument("--opencode-provider", default="openai")
    parser.add_argument("--pi-provider", default="openai-codex")
    parser.add_argument("--install-pi-subagents", action="store_true")
    args = parser.parse_args()
    try:
        install(args.harness, args.opencode_provider, args.pi_provider, args.install_pi_subagents)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
