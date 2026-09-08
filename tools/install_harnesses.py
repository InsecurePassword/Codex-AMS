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
    # Public installs use raw downloads, not one rate-limited API request per file.
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{REF}/{quoted}"
    headers = {"User-Agent": "AMS-Tree-Installer"}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(1048577)
    except urllib.error.HTTPError as error:
        token = github_token() if error.code in (401, 403, 404) else None
        if not token:
            raise ValueError(f"Repository download failed (HTTP {error.code}): {path}. "
                             "Check connectivity and repository access; no files were substituted.") from error
        url = f"https://api.github.com/repos/{REPOSITORY}/contents/{quoted}?ref={REF}"
        headers.update(Accept="application/vnd.github.raw+json", Authorization=f"Bearer {token}")
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
            data = response.read(1048577)
    if len(data) > 1048576:
        raise ValueError(f"Repository file exceeds the installation size limit: {path}")
    return data


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
    if (not data.startswith(b"ams-install-manifest-v1\n") or not data.endswith(b"\n")
            or b"\r" in data or len(data) > 262144):
        raise ValueError("Invalid installation manifest.")
    entries: dict[str, tuple[str, int]] = {}
    folded: set[str] = set()
    for row in data.decode("utf-8").splitlines()[1:]:
        digest, length_text, name = row.split("\t")
        parts = name.split("/")
        if (parts[0] != SKILL or any(part in ("", ".", "..") for part in parts)
                or not re.fullmatch(r"[A-Za-z0-9._/-]+", name) or name.casefold() in folded
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not length_text.isdecimal() or not 0 < int(length_text) <= 1048576):
            raise ValueError(f"Unsafe or duplicate manifest entry: {name}")
        entries[name] = (digest, int(length_text))
        folded.add(name.casefold())
    if not entries or sum(size for _, size in entries.values()) > 104857600:
        raise ValueError("Installation manifest has invalid membership or total size.")
    return entries


def package_profiles(local: bool = True) -> list[dict[str, str]]:
    entries = manifest_entries(source_bytes("install-manifest.txt", local))
    names = sorted(name for name in entries if "/assets/agent-profiles/" in name and name.endswith(".toml"))
    if len(names) != 24:
        raise ValueError(f"Expected 24 manifest-listed model profiles, found {len(names)}.")
    profiles = []
    for name in names:
        data = source_bytes(name, local)
        digest, length = entries[name]
        if len(data) != length or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Package integrity check failed: {name}")
        profile = tomllib.loads(data.decode("utf-8"))
        if profile["name"] != Path(name).stem:
            raise ValueError(f"Profile name mismatch: {name}")
        if profile["name"] != "ams_daybreak_blue_max":
            profiles.append(profile)
    return profiles


def cli(harness: str, arguments: list[str], *, env: dict[str, str]) -> str:
    executable = shutil.which(harness)
    if not executable:
        raise ValueError(f"{harness} is not on PATH. Install the harness first.")
    result = subprocess.run([executable, *arguments], cwd=Path.cwd(), env=env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if result.returncode:
        raise RuntimeError(f"{harness} {' '.join(arguments)} failed (exit {result.returncode}); no model was invoked.")
    return re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)


def catalog(harness: str, env: dict[str, str]) -> dict[str, set[str]]:
    output = cli(harness, ["models"] if harness == "opencode" else ["--list-models"], env=env)
    models: dict[str, set[str]] = {}
    for line in output.splitlines():
        fields = line.split()
        if harness == "opencode" and len(fields) == 1 and "/" in fields[0]:
            provider, model = fields[0].split("/", 1)
        elif harness == "pi" and len(fields) >= 2 and fields[0].lower() != "provider":
            provider, model = fields[:2]
        else:
            continue
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", provider) and model:
            models.setdefault(model, set()).add(provider)
    return models


def select_profiles(profiles: list[dict[str, str]], models: dict[str, set[str]],
                    harness: str, provider: str, agent_home: Path) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    for profile in profiles:
        candidates = models.get(profile["model"], set())
        if provider != "auto":
            candidates = candidates & {provider}
        if not candidates:
            continue
        target = agent_home / (profile["name"] + ".md")
        safe_path(target)
        if len(candidates) > 1:
            # Reinstall keeps an exact previously generated route; never guess a paid provider.
            prior = target.read_bytes() if target.is_file() else None
            previous = [p for p in candidates if prior == render(profile, harness, p)]
            if len(previous) != 1:
                raise ValueError(f"{profile['model']} is listed by multiple providers: "
                                 f"{', '.join(sorted(candidates))}. Select --{harness}-provider NAME.")
            candidates = set(previous)
        files[target] = render(profile, harness, next(iter(candidates)))
    if not files:
        providers = sorted({p for available in models.values() for p in available})
        examples = ", ".join(sorted(models)[:8]) or "(empty model catalog)"
        raise ValueError("No exact AMS model IDs found" +
                         (f" under provider {provider!r}" if provider != "auto" else " in any provider") +
                         f". Listed providers: {', '.join(providers) or '(none)'}. "
                         f"Model examples: {examples}. No model names were substituted.")
    return files


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
            command = [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Local"]
            native_env.pop("PSModulePath", None)
        else:
            command = ["bash", str(script), "--local"]
        subprocess.run(command, cwd=package_root, env=native_env, check=True, timeout=300)


def install(harness: str, opencode_provider: str = "auto", pi_provider: str = "auto",
            install_pi: bool = False, local: bool = True) -> int:
    targets = {"codex", "opencode", "pi"} if harness == "all" else {harness}
    if not targets <= {"codex", "opencode", "pi"}:
        raise ValueError("Unknown harness.")
    if install_pi and "pi" not in targets:
        raise ValueError("Installing pi-subagents requires the pi or all target.")
    env = os.environ.copy()
    if env.get("AMS_INSTALL_PROFILES_ONLY", "1") != "1":
        raise ValueError("AMS_INSTALL_PROFILES_ONLY must be unset or exactly 1.")
    providers = {"opencode": opencode_provider, "pi": pi_provider}
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", p) for p in providers.values()):
        raise ValueError("Invalid provider name.")
    homes = {
        "pi": home_path("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent"),
        "opencode": home_path("OPENCODE_CONFIG_DIR", home_path("XDG_CONFIG_HOME", Path.home() / ".config") / "opencode"),
    }
    if {"pi", "opencode"} <= targets and homes["pi"] == homes["opencode"]:
        raise ValueError("OpenCode and Pi must have separate agent directories.")
    env["PI_CODING_AGENT_DIR"] = str(homes["pi"])
    profiles = package_profiles(local) if targets - {"codex"} else []
    # Model catalogs do not control installation of the shared skill or Codex's registry.
    install_core(targets, env, local)
    if env.get("AMS_INSTALL_PROFILES_ONLY") != "1":
        skill = home_path("AMS_SKILL_HOME", Path.home() / ".agents/skills") / SKILL / "SKILL.md"
        print(f"Shared AMS skill installed: {skill}")
    if "codex" in targets:
        print("codex: skill/profile installation completed.")
    incomplete: list[str] = []
    for target in sorted(targets - {"codex"}):
        created: list[tuple[Path, tuple[int, int], bytes]] = []
        try:
            models = catalog(target, env)
            files = select_profiles(profiles, models, target, providers[target], homes[target] / "agents")
            preflight(files)
            if target == "pi" and not pi_package(homes["pi"]):
                if not install_pi:
                    raise ValueError("Pi requires pi-subagents. Add --install-pi-subagents to permit its installation.")
                package_env = env.copy()
                cli("pi", ["install", "npm:pi-subagents"], env=package_env)
                if not pi_package(homes["pi"]):
                    raise RuntimeError("Pi did not register pi-subagents.")
            create_files(files, created)
            preflight(files)
            if any(not p.is_file() or p.read_bytes() != data for p, data in files.items()):
                raise ValueError("Final native agent verification failed.")
            print(f"{target}: {len(files)} native agent presets installed in {homes[target] / 'agents'}")
            omitted = len(profiles) - len(files)
            if omitted:
                print(f"{target}: {omitted} presets omitted because their exact model IDs are not listed.")
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            rollback(created)
            incomplete.append(target)
            print(f"{target}: NOT CONFIGURED: {error}", file=sys.stderr)
        except BaseException:
            rollback(created)
            raise
    print("Restart the selected apps to reload skills and agents. In Codex type $ and select AMS.")
    print(f"Exact Codex skill name: ${SKILL}. Pi: /skill:{SKILL}.")
    print("Providers, credentials, permissions, compaction, and AMS project settings were not changed.")
    if incomplete:
        print(f"Partial installation: {', '.join(incomplete)} still need configuration. "
              "Successful targets and the shared skill were retained.", file=sys.stderr)
        return 2
    print("All selected targets installed. Model access and effective effort still depend on the harness/provider.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=("codex", "opencode", "pi", "all"), required=True)
    parser.add_argument("--opencode-provider", default="auto", help="Provider ID, or auto (default).")
    parser.add_argument("--pi-provider", default="auto", help="Provider ID, or auto (default).")
    parser.add_argument("--install-pi-subagents", action="store_true")
    parser.add_argument("--local", action="store_true", help="Use the complete package beside this script instead of downloading.")
    args = parser.parse_args()
    try:
        return install(args.harness, args.opencode_provider, args.pi_provider,
                       args.install_pi_subagents, args.local)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
