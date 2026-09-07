#!/usr/bin/env python3
"""Execute one bounded request against a project-local OpenAI-compatible profile."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

PROFILE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
MAX_PROFILE_BYTES = 64 * 1024
MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
MAX_COMMAND_OUTPUT = 16 * 1024
MAX_ERROR_BYTES = 64 * 1024
ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
CONTEXT_ERROR_RE = re.compile(
    r"context|token.*limit|maximum.*token|too many tokens|context length|prompt.*long",
    re.IGNORECASE,
)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


HTTP_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler())


class LaneError(Exception):
    def __init__(
        self,
        status: str,
        message: str,
        *,
        detail: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.detail = detail
        self.evidence = evidence or {}


def emit(payload: dict[str, Any], code: int) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    raise SystemExit(code)


def same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(os.path.normpath(str(right)))


def require_type(data: dict[str, Any], key: str, expected: type) -> Any:
    value = data.get(key)
    if type(value) is not expected:  # bool must not satisfy int
        raise LaneError("invalid-profile", f"profile field {key!r} must be {expected.__name__}")
    return value


def bounded_int(data: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    value = data.get(key, default)
    if type(value) is not int or not low <= value <= high:
        raise LaneError("invalid-profile", f"profile field {key!r} must be an integer in {low}..{high}")
    return value


def stable_read(path: Path, maximum: int, status: str, label: str) -> bytes:
    try:
        before = path.stat()
        if before.st_size <= 0 or before.st_size > maximum:
            raise LaneError(status, f"{label} size is outside the allowed bound")
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise LaneError(status, f"{label} is missing or unreadable") from exc
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if identity(before) != identity(after) or len(raw) != before.st_size:
        raise LaneError(status, f"{label} changed while being read")
    return raw


def optional_command(data: dict[str, Any], key: str) -> list[str] | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not value or len(value) > 64:
        raise LaneError("invalid-profile", f"profile field {key!r} must be a non-empty string array")
    if any(type(item) is not str or not item or "\x00" in item or len(item) > 4096 for item in value):
        raise LaneError("invalid-profile", f"profile field {key!r} contains an invalid argument")
    return list(value)


def safe_profile_path(project_root: Path, profile_name: str) -> Path:
    if not PROFILE_RE.fullmatch(profile_name):
        raise LaneError("invalid-profile", "invalid profile name")
    if not project_root.is_absolute() or project_root.is_symlink():
        raise LaneError("invalid-profile", "project root must be an absolute non-redirected directory")
    expected_root = Path(os.path.abspath(project_root))
    try:
        root = project_root.resolve(strict=True)
    except OSError as exc:
        raise LaneError("invalid-profile", "project root is missing or unreadable") from exc
    if not root.is_dir() or not same_path(expected_root, root):
        raise LaneError("invalid-profile", "project root must be a canonical non-redirected directory")

    current = root
    for part in (".codex", "ams-local-llm", "profiles"):
        current = current / part
        if current.is_symlink():
            raise LaneError("invalid-profile", "profile path must not be redirected")
    profile_root = current
    candidate = profile_root / f"{profile_name}.toml"
    if candidate.is_symlink():
        raise LaneError("invalid-profile", "profile path must not be redirected")
    try:
        resolved_root = profile_root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise LaneError("invalid-profile", "profile or profile directory is missing") from exc
    if (
        not same_path(profile_root, resolved_root)
        or not same_path(candidate, resolved)
        or resolved.parent != resolved_root
        or not resolved.is_file()
    ):
        raise LaneError("invalid-profile", "profile must be a regular non-redirected file in the project profile directory")
    try:
        resolved_root.relative_to(root)
    except ValueError as exc:
        raise LaneError("invalid-profile", "profile directory escapes the project root") from exc
    return resolved


def read_profile(project_root: Path, profile_name: str) -> dict[str, Any]:
    path = safe_profile_path(project_root, profile_name)
    raw = stable_read(path, MAX_PROFILE_BYTES, "invalid-profile", "profile")
    if raw.startswith(b"\xef\xbb\xbf") or b"\x00" in raw or b"\r" in raw:
        raise LaneError("invalid-profile", "profile must be UTF-8/LF without BOM, NUL, or CR")
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise LaneError("invalid-profile", "profile is not valid UTF-8 TOML", detail=str(exc)) from exc
    if any(isinstance(value, dict) for value in data.values()):
        raise LaneError("invalid-profile", "profile tables are not supported")

    allowed = {
        "profile_version",
        "name",
        "model_key",
        "context_length",
        "base_url",
        "api",
        "model",
        "allowed_observed_models",
        "readiness_path",
        "api_key_env",
        "readiness_timeout_seconds",
        "startup_grace_seconds",
        "request_timeout_seconds",
        "command_timeout_seconds",
        "context_reserve_tokens",
        "max_output_tokens",
        "temperature",
        "keep_loaded_default",
        "start_command",
        "stop_command",
    }
    unknown = set(data) - allowed
    if unknown:
        raise LaneError("invalid-profile", f"unsupported profile fields: {', '.join(sorted(unknown))}")

    if require_type(data, "profile_version", int) != 1:
        raise LaneError("invalid-profile", "profile_version must equal 1")
    if require_type(data, "name", str) != profile_name:
        raise LaneError("invalid-profile", "profile name does not match its filename")
    model_key = require_type(data, "model_key", str)
    model = require_type(data, "model", str)
    context_length = require_type(data, "context_length", int)
    base_url = require_type(data, "base_url", str).rstrip("/")
    api = data.get("api", "chat_completions")
    if api not in {"chat_completions", "responses"}:
        raise LaneError("invalid-profile", "api must be chat_completions or responses")
    if not model_key or len(model_key) > 256 or not model or len(model) > 512:
        raise LaneError("invalid-profile", "model_key/model is empty or too long")
    aliases = data.get("allowed_observed_models", [])
    if not isinstance(aliases, list) or len(aliases) > 16:
        raise LaneError("invalid-profile", "allowed_observed_models must be a string array with at most 16 entries")
    allowed_observed_models: list[str] = [model]
    for alias in aliases:
        if type(alias) is not str or not alias or len(alias) > 512 or "\x00" in alias:
            raise LaneError("invalid-profile", "allowed_observed_models contains an invalid model identifier")
        if alias not in allowed_observed_models:
            allowed_observed_models.append(alias)
    if not 2048 <= context_length <= 4_194_304:
        raise LaneError("invalid-profile", "context_length must be an integer in 2048..4194304")
    parsed = urllib.parse.urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise LaneError("invalid-profile", "base_url must be an exact HTTP(S) endpoint without credentials, query, or fragment")

    readiness_path = data.get("readiness_path", "/models")
    parsed_readiness = urllib.parse.urlparse(readiness_path) if type(readiness_path) is str else None
    if (
        parsed_readiness is None
        or not readiness_path.startswith("/")
        or readiness_path.startswith("//")
        or parsed_readiness.scheme
        or parsed_readiness.netloc
        or parsed_readiness.query
        or parsed_readiness.fragment
        or "\x00" in readiness_path
    ):
        raise LaneError("invalid-profile", "readiness_path must be an absolute path without authority, query, or fragment")
    api_key_env = data.get("api_key_env", "")
    if type(api_key_env) is not str or (api_key_env and not ENV_NAME_RE.fullmatch(api_key_env)):
        raise LaneError("invalid-profile", "api_key_env must be empty or a valid environment-variable name")
    temperature = data.get("temperature", 0.2)
    if type(temperature) not in {int, float} or isinstance(temperature, bool) or not 0 <= float(temperature) <= 2:
        raise LaneError("invalid-profile", "temperature must be numeric in 0..2")
    keep = data.get("keep_loaded_default", True)
    if type(keep) is not bool:
        raise LaneError("invalid-profile", "keep_loaded_default must be Boolean")

    start_command = optional_command(data, "start_command")
    stop_command = optional_command(data, "stop_command")
    if start_command and not stop_command:
        raise LaneError("invalid-profile", "start_command requires stop_command")
    if not keep and not stop_command:
        raise LaneError("invalid-profile", "keep_loaded_default=false requires stop_command")

    normalized = dict(data)
    normalized.update(
        {
            "model_key": model_key,
            "model": model,
            "allowed_observed_models": allowed_observed_models,
            "base_url": base_url,
            "api": api,
            "readiness_path": readiness_path,
            "api_key_env": api_key_env,
            "context_length": context_length,
            "readiness_timeout_seconds": bounded_int(data, "readiness_timeout_seconds", 5, 1, 60),
            "startup_grace_seconds": bounded_int(data, "startup_grace_seconds", 5, 0, 60),
            "request_timeout_seconds": bounded_int(data, "request_timeout_seconds", 600, 1, 7200),
            "command_timeout_seconds": bounded_int(data, "command_timeout_seconds", 45, 1, 600),
            "context_reserve_tokens": bounded_int(data, "context_reserve_tokens", 2048, 0, 131072),
            "max_output_tokens": bounded_int(data, "max_output_tokens", 8192, 1, 262144),
            "temperature": float(temperature),
            "keep_loaded_default": keep,
            "start_command": start_command,
            "stop_command": stop_command,
        }
    )
    return normalized


def read_request(path_text: str, project_root: Path) -> dict[str, Any]:
    source_path = Path(path_text)
    if not source_path.is_absolute() or source_path.is_symlink():
        raise LaneError("invalid-request", "request file must be absolute, regular, and non-redirected")
    expected = Path(os.path.abspath(source_path))
    try:
        path = source_path.resolve(strict=True)
    except OSError as exc:
        raise LaneError("invalid-request", "request file is missing or unreadable") from exc
    if not path.is_file() or not same_path(expected, path):
        raise LaneError("invalid-request", "request file must be canonical, regular, and non-redirected")
    try:
        path.relative_to(project_root.resolve(strict=True))
    except ValueError:
        pass
    else:
        raise LaneError("invalid-request", "request file must be outside the project root")
    raw = stable_read(path, MAX_REQUEST_BYTES, "invalid-request", "request file")
    if len(raw) > MAX_REQUEST_BYTES or b"\x00" in raw:
        raise LaneError("invalid-request", "request exceeds size bound or contains NUL")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaneError("invalid-request", "request is not valid UTF-8 JSON", detail=str(exc)) from exc
    if not isinstance(data, dict):
        raise LaneError("invalid-request", "request root must be an object")
    allowed = {"system", "user", "estimated_input_tokens", "max_output_tokens"}
    unknown = set(data) - allowed
    if unknown:
        raise LaneError("invalid-request", f"unsupported request fields: {', '.join(sorted(unknown))}")
    system = data.get("system", "")
    user = data.get("user")
    if type(system) is not str or type(user) is not str or not user:
        raise LaneError("invalid-request", "system must be a string and user must be a non-empty string")
    estimate = data.get("estimated_input_tokens", 0)
    output = data.get("max_output_tokens", 0)
    if (
        type(estimate) is not int
        or not 0 <= estimate <= 4_194_304
        or type(output) is not int
        or not 0 <= output <= 262_144
    ):
        raise LaneError("invalid-request", "token estimates are outside the allowed bounds")
    return {"system": system, "user": user, "estimated_input_tokens": estimate, "max_output_tokens": output}


def auth_headers(profile: dict[str, Any]) -> dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    env_name = profile["api_key_env"]
    if env_name:
        token = os.environ.get(env_name)
        if not token:
            raise LaneError("unavailable", f"required API-key environment variable {env_name!r} is unset")
        if len(token) > 8192 or "\r" in token or "\n" in token:
            raise LaneError("unavailable", "configured API key is invalid")
        headers["Authorization"] = f"Bearer {token}"
    return headers


def urlopen_json(request: urllib.request.Request, timeout: int) -> tuple[int, dict[str, Any]]:
    try:
        with HTTP_OPENER.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_ERROR_BYTES + 1)
        text = raw.decode("utf-8", errors="replace")
        status = "context-too-small" if CONTEXT_ERROR_RE.search(text) else "request-failed"
        raise LaneError(status, f"endpoint returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LaneError("unavailable", "endpoint request failed", detail=str(exc)) from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise LaneError("malformed-response", "endpoint response exceeds size bound")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaneError("malformed-response", "endpoint response is not valid UTF-8 JSON", detail=str(exc)) from exc
    if not isinstance(payload, dict):
        raise LaneError("malformed-response", "endpoint response root is not an object")
    return status, payload


def readiness(profile: dict[str, Any], headers: dict[str, str]) -> bool:
    request = urllib.request.Request(profile["base_url"] + profile["readiness_path"], headers=headers, method="GET")
    try:
        _, payload = urlopen_json(request, profile["readiness_timeout_seconds"])
    except LaneError as exc:
        if exc.status == "unavailable":
            return False
        raise
    data = payload.get("data")
    if not isinstance(data, list):
        return True  # endpoint is alive; some compatible servers omit a canonical model list
    ids = {item.get("id") for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)}
    return not ids or profile["model"] in ids


def run_command(command: list[str], timeout: int, label: str) -> None:
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            timeout=timeout,
            check=False,
        )
    except OSError as exc:
        raise LaneError("unavailable", f"{label} command failed to execute") from exc
    except subprocess.TimeoutExpired as exc:
        raise LaneError("unavailable", f"{label} command timed out") from exc
    if completed.returncode != 0:
        raise LaneError("unavailable", f"{label} command exited {completed.returncode}")


def context_preflight(profile: dict[str, Any], request_data: dict[str, Any]) -> tuple[int, int, int]:
    raw = (request_data["system"] + "\n" + request_data["user"]).encode("utf-8")
    conservative = len(raw)  # safe fallback: at most one token per UTF-8 byte
    estimated = request_data["estimated_input_tokens"] or conservative
    requested_output = request_data["max_output_tokens"]
    if requested_output and requested_output > profile["max_output_tokens"]:
        raise LaneError("invalid-request", "requested output exceeds the selected profile limit")
    output = requested_output or profile["max_output_tokens"]
    required = estimated + output + profile["context_reserve_tokens"]
    if required > profile["context_length"]:
        raise LaneError(
            "context-too-small",
            "profile context is too small for the bounded request",
            detail=f"required_context_length={required}",
        )
    return estimated, output, required


def extract_chat_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise LaneError("malformed-response", "chat response has no choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise LaneError("malformed-response", "chat response has no message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "".join(parts)
    raise LaneError("malformed-response", "chat response content is missing")


def extract_responses_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    output = payload.get("output")
    parts: list[str] = []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for entry in content:
                if isinstance(entry, dict) and isinstance(entry.get("text"), str):
                    parts.append(entry["text"])
    if parts:
        return "".join(parts)
    raise LaneError("malformed-response", "responses output text is missing")


def infer(
    profile: dict[str, Any], request_data: dict[str, Any], headers: dict[str, str], output_tokens: int
) -> tuple[str, str]:
    if profile["api"] == "chat_completions":
        endpoint = profile["base_url"] + "/chat/completions"
        messages: list[dict[str, str]] = []
        if request_data["system"]:
            messages.append({"role": "system", "content": request_data["system"]})
        messages.append({"role": "user", "content": request_data["user"]})
        body = {
            "model": profile["model"],
            "messages": messages,
            "max_tokens": output_tokens,
            "temperature": profile["temperature"],
            "stream": False,
        }
        extractor = extract_chat_text
    else:
        endpoint = profile["base_url"] + "/responses"
        body = {
            "model": profile["model"],
            "input": request_data["user"],
            "max_output_tokens": output_tokens,
            "temperature": profile["temperature"],
        }
        if request_data["system"]:
            body["instructions"] = request_data["system"]
        extractor = extract_responses_text
    encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(endpoint, data=encoded, headers=headers, method="POST")
    _, payload = urlopen_json(request, profile["request_timeout_seconds"])
    observed_model = payload.get("model")
    if type(observed_model) is not str or not observed_model or len(observed_model) > 512:
        raise LaneError("model-identity-missing", "local response omitted a usable model identity")
    if observed_model not in profile["allowed_observed_models"]:
        raise LaneError(
            "model-mismatch",
            "local endpoint returned a model outside the selected profile",
            detail=f"requested_model={profile['model']} observed_model={observed_model}",
            evidence={"observed_model": observed_model},
        )
    text = extractor(payload)
    if not text.strip():
        raise LaneError("malformed-response", "local model returned empty output")
    return text, observed_model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--request-file")
    parser.add_argument("--lifecycle", choices=("auto", "keep", "close"), default="auto")
    parser.add_argument("--stop-only", action="store_true")
    args = parser.parse_args()

    start_attempted = False
    started = False
    stop_attempted = False
    profile: dict[str, Any] | None = None
    try:
        project_root = Path(args.project_root)
        profile = read_profile(project_root, args.profile)
        if args.stop_only:
            if args.request_file:
                raise LaneError("invalid-request", "--stop-only cannot use --request-file")
            if not profile["stop_command"]:
                raise LaneError("unavailable", "profile has no stop_command")
            stop_attempted = True
            run_command(profile["stop_command"], profile["command_timeout_seconds"], "stop")
            emit({"status": "stopped", "profile": profile["name"], "model_key": profile["model_key"]}, 0)
        if not args.request_file:
            raise LaneError("invalid-request", "--request-file is required unless --stop-only is used")
        request_data = read_request(args.request_file, project_root)
        estimated, output_tokens, required = context_preflight(profile, request_data)
        headers = auth_headers(profile)

        if not readiness(profile, headers):
            if not profile["start_command"]:
                raise LaneError("unavailable", "endpoint/model is unavailable and no start_command is configured")
            start_attempted = True
            run_command(profile["start_command"], profile["command_timeout_seconds"], "start")
            started = True
            if profile["startup_grace_seconds"]:
                time.sleep(profile["startup_grace_seconds"])
            if not readiness(profile, headers):
                raise LaneError("unavailable", "endpoint/model remains unavailable after the one start attempt")

        response_text, observed_model = infer(profile, request_data, headers, output_tokens)
        should_close = args.lifecycle == "close" or (args.lifecycle == "auto" and not profile["keep_loaded_default"])
        if should_close and not profile["stop_command"]:
            raise LaneError("unavailable", "close requested but profile has no stop_command")
        if should_close:
            stop_attempted = True
            run_command(profile["stop_command"], profile["command_timeout_seconds"], "stop")

        emit(
            {
                "status": "complete",
                "profile": profile["name"],
                "model_key": profile["model_key"],
                "requested_model": profile["model"],
                "observed_model": observed_model,
                "context_length": profile["context_length"],
                "estimated_input_tokens": estimated,
                "required_context_length": required,
                "started_model": started,
                "lifecycle": args.lifecycle,
                "model_state": "stopped" if should_close else "kept",
                "load_ownership": "none" if should_close else ("companion-started" if started else "preexisting"),
                "response_text": response_text,
            },
            0,
        )
    except LaneError as exc:
        cleanup = "not-needed"
        if start_attempted and profile and profile.get("stop_command") and not stop_attempted:
            try:
                stop_attempted = True
                run_command(profile["stop_command"], profile["command_timeout_seconds"], "cleanup-stop")
                cleanup = "stopped"
            except LaneError:
                cleanup = "stop-failed"
        payload: dict[str, Any] = {"status": exc.status, "error": exc.message}
        if exc.detail:
            payload["detail"] = exc.detail[:MAX_COMMAND_OUTPUT]
        payload.update(exc.evidence)
        if profile:
            payload.update(
                {
                    "profile": profile.get("name", args.profile),
                    "model_key": profile.get("model_key"),
                    "requested_model": profile.get("model"),
                    "context_length": profile.get("context_length"),
                    "cleanup": cleanup,
                }
            )
        emit(payload, 10 if exc.status == "context-too-small" else 20)
    return 0


if __name__ == "__main__":
    main()
