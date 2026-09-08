#!/usr/bin/env python3
"""Install shared AMS instructions and native OpenCode/Pi model presets."""
from __future__ import annotations

import argparse
from functools import lru_cache
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
import urllib.error
import urllib.parse
import urllib.request

if sys.version_info < (3, 11):
    raise SystemExit("OpenCode/Pi installation requires Python 3.11 or newer.")
import tomllib

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[1] if SCRIPT.name != "<stdin>" else Path.cwd()
LOCAL_PACKAGE = SCRIPT.name != "<stdin>" and (ROOT / "install-manifest.txt").is_file()
REPOSITORY = "InsecurePassword/Codex-AMS"
REF = "main"
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


@lru_cache(maxsize=1)
def github_token() -> str | None:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()
    gh = shutil.which("gh")
    if gh:
        result = subprocess.run([gh, "auth", "token"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return None


def _remote_bytes(path: str) -> bytes:
    quoted = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    url = f"https://api.github.com/repos/{REPOSITORY}/contents/{quoted}?ref={REF}"
    headers = {
        "Accept": "application/vnd.github.raw+json",
        "User-Agent": "AMS-Tree-Installer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code in (401, 403, 404):
            raise ValueError(
                "Remote repository access failed. Authenticate GitHub CLI with `gh auth login` "
                "or set GH_TOKEN/GITHUB_TOKEN with read access to InsecurePassword/Codex-AMS."
            ) from error
        raise


@lru_cache(maxsize=None)
def remote_bytes(path: str) -> bytes:
    return _remote_bytes(path)


def source_bytes(path: str, local: bool) -> bytes:
    if local:
        source = ROOT / path
        safe_path(source)
        return source.read_bytes()
    return remote_bytes(path)


def manifest_entries(data: bytes) -> dict[str, tuple[str, int]]:
    if not data.startswith(b"ams-install-manifest-v1\n") or b"\r" in data:
        raise ValueError("Invalid installation manifest.")
    entries: dict[str, tuple[str, int]] = {}
    for row in data.decode("utf-8").splitlines()[1:]:
        digest, length_text, name = row.split("\t")
        parts = name.split("/")
        if (parts[0] != SKILL or any(part in ("", ".", "..") for part in parts)
                or not re.fullmatch(r"[A-Za-z0-9._/-]+", name) or name in entries):
            raise ValueError(f"Unsafe or duplicate manifest path: {name}")
        entries[name] = (digest, int(length_text))
    if not entries:
        raise ValueError("Installation manifest contains no package files.")
    return entries


def package_profiles(local: bool = True) -> list[dict[str, str]]:
    """Verify manifest-listed model profiles before translating them."""
    entries = manifest_entries(source_bytes("install-manifest.txt", local))
    profile_entries = sorted(
        name for name in entries
        if "/assets/agent-profiles/" in name and name.endswith(".toml")
    )
    if len(profile_entries) != 24:
        raise ValueError(f"Expected 24 manifest-listed model profiles, found {len(profile_entries)}.")
    profiles: list[dict[str, str]] = []
    for name in profile_entries:
        data = source_bytes(name, local)
        digest, length = entries[name]
        if len(data) != length or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Package integrity check failed: {name}")
        profile = tomllib.loads(data.decode("utf-8"))
        stem = Path(name).stem
        if profile["name"] != stem:
            raise ValueError(f"Profile name mismatch: {name}")
        if stem != "ams_daybreak_blue_max":
            profiles.append(profile)
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


def stage_remote_package(root: Path) -> Path:
    manifest = remote_bytes("install-manifest.txt")
    entries = manifest_entries(manifest)
    (root / "install-manifest.txt").write_bytes(manifest)
    for name, (digest, length) in entries.items():
        data = remote_bytes(name)
        if len(data) != length or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Package integrity check failed: {name}")
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    script_name = "install.ps1" if os.name == "nt" else "install.sh"
    script = root / script_name
    script.write_bytes(remote_bytes(script_name))
    if _remote_bytes("install-manifest.txt") != manifest:
        raise ValueError("Installation manifest changed during download; retry the install.")
    return script


def install_core(targets: set[str], env: dict[str, str], local: bool) -> None:
    native_env = env.copy()
    native_env.pop("AMS_INSTALL_SKILL_ONLY", None)
    if "codex" not in targets:
        if native_env.get("AMS_INSTALL_PROFILES_ONLY") == "1":
            return
        native_env["AMS_INSTALL_SKILL_ONLY"] = "1"
    with tempfile.TemporaryDirectory(prefix="ams-bootstrap-") as temporary:
        package_root = ROOT if local else Path(temporary)
        script = (ROOT / ("install.ps1" if os.name == "nt" else "install.sh")
                  if local else stage_remote_package(package_root))
        if os.name == "nt":
            executable = shutil.which("powershell.exe")
            if not executable:
                raise ValueError("Windows PowerShell is required for the core installer.")
            command = [executable, "-NoProfile", "-ExecutionPolicy", "Bypass",
                       "-File", str(script), "-Local"]
            native_env.pop("PSModulePath", None)
        else:
            command = ["bash", str(script), "--local"]
        subprocess.run(command, cwd=package_root, env=native_env, check=True, timeout=300)


def install(harness: str, opencode_provider: str, pi_provider: str,
            install_pi: bool, local: bool = True) -> None:
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
    profiles = package_profiles(local) if targets - {"codex"} else []
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
        install_core(targets, env, local)
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
    parser.add_argument("--harness", choices=("codex", "opencode", "pi", "all"), required=True)
    parser.add_argument("--opencode-provider", default="openai")
    parser.add_argument("--pi-provider", default="openai-codex")
    parser.add_argument("--install-pi-subagents", action="store_true")
    parser.add_argument("--local", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        install(args.harness, args.opencode_provider, args.pi_provider,
                args.install_pi_subagents, args.local or LOCAL_PACKAGE)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
