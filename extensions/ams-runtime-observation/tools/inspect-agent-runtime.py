#!/usr/bin/env python3
"""Emit allowlisted routing metadata for one exact Codex subagent rollout."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Iterable, NoReturn

THREAD_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAX_ROLLOUT_BYTES = 64 * 1024 * 1024
MAX_LINE_CHARS = 4 * 1024 * 1024
MAX_DIRECTORIES = 10_000
MAX_ENTRIES = 200_000
MAX_DEPTH = 16


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def default_sessions_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "sessions"
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if not home:
        fail("HOME/USERPROFILE is unset and --sessions-dir was not supplied")
    return Path(home) / ".codex" / "sessions"


def _is_reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _windows_final_path(fd: int) -> str:
    import ctypes
    import msvcrt

    handle = msvcrt.get_osfhandle(fd)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = kernel32.GetFinalPathNameByHandleW
    fn.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    fn.restype = ctypes.c_uint32
    size = fn(handle, None, 0, 0)
    if size == 0:
        raise OSError(ctypes.get_last_error(), "GetFinalPathNameByHandleW failed")
    buffer = ctypes.create_unicode_buffer(size + 1)
    written = fn(handle, buffer, len(buffer), 0)
    if written == 0 or written >= len(buffer):
        raise OSError(ctypes.get_last_error(), "GetFinalPathNameByHandleW failed")
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.abspath(value))


def _inside(root: str, child: str) -> bool:
    try:
        return os.path.commonpath([root, child]) == root
    except ValueError:
        return False


def _open_file_at(directory_fd: int, name: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    return os.open(name, flags, dir_fd=directory_fd)


def exact_match_fds_posix(root: Path, thread_id: str) -> list[int]:
    suffix = f"-{thread_id}.jsonl"
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        root_fd = os.open(root, directory_flags)
    except OSError:
        fail("sessions directory could not be opened safely")
    if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
        os.close(root_fd)
        fail("sessions directory is not a safe directory")

    matches: list[int] = []
    pending: list[tuple[int, int]] = [(root_fd, 0)]
    directories = 0
    entries_seen = 0
    try:
        while pending:
            directory_fd, depth = pending.pop()
            directories += 1
            if directories > MAX_DIRECTORIES or depth > MAX_DEPTH:
                fail("sessions-tree traversal bound exceeded")
            try:
                with os.scandir(directory_fd) as entries:
                    for entry in entries:
                        entries_seen += 1
                        if entries_seen > MAX_ENTRIES:
                            fail("sessions-tree entry bound exceeded")
                        exact_name = entry.name.startswith("rollout-") and entry.name.endswith(suffix)
                        try:
                            if entry.is_symlink():
                                if exact_name:
                                    fail("an exact rollout filename match is redirected")
                                continue
                        except OSError:
                            fail("sessions tree could not be enumerated safely")

                        try:
                            child_fd = os.open(entry.name, directory_flags, dir_fd=directory_fd)
                        except OSError:
                            child_fd = -1
                        if child_fd >= 0:
                            info = os.fstat(child_fd)
                            if not stat.S_ISDIR(info.st_mode):
                                os.close(child_fd)
                                fail("sessions tree changed during enumeration")
                            pending.append((child_fd, depth + 1))
                            continue

                        if not exact_name:
                            continue
                        try:
                            file_fd = _open_file_at(directory_fd, entry.name)
                            info = os.fstat(file_fd)
                        except OSError:
                            fail("matched rollout could not be opened safely")
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                            os.close(file_fd)
                            fail("matched rollout is not a safe regular file")
                        matches.append(file_fd)
                        if len(matches) > 1:
                            for pending_fd, _ in pending:
                                try:
                                    os.close(pending_fd)
                                except OSError:
                                    pass
                            pending.clear()
                            return matches
            finally:
                os.close(directory_fd)
        return matches
    except BaseException:
        for directory_fd, _ in pending:
            try:
                os.close(directory_fd)
            except OSError:
                pass
        for file_fd in matches:
            try:
                os.close(file_fd)
            except OSError:
                pass
        raise


def exact_match_fds_windows(root: Path, thread_id: str) -> list[int]:
    suffix = f"-{thread_id}.jsonl"
    root_final = os.path.normcase(os.path.realpath(root))
    matches: list[int] = []
    pending: list[tuple[Path, int]] = [(root, 0)]
    directories = 0
    entries_seen = 0
    while pending:
        directory, depth = pending.pop()
        directories += 1
        if directories > MAX_DIRECTORIES or depth > MAX_DEPTH:
            fail("sessions-tree traversal bound exceeded")
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    entries_seen += 1
                    if entries_seen > MAX_ENTRIES:
                        fail("sessions-tree entry bound exceeded")
                    exact_name = entry.name.startswith("rollout-") and entry.name.endswith(suffix)
                    info = entry.stat(follow_symlinks=False)
                    if _is_reparse(info) or entry.is_symlink():
                        if exact_name:
                            fail("an exact rollout filename match is redirected")
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        pending.append((Path(entry.path), depth + 1))
                        continue
                    if not exact_name:
                        continue
                    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
                    try:
                        fd = os.open(entry.path, flags)
                        opened = os.fstat(fd)
                        final_path = _windows_final_path(fd)
                    except OSError:
                        fail("matched rollout could not be opened safely")
                    if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or not _inside(root_final, final_path):
                        os.close(fd)
                        fail("matched rollout escaped the sessions root or is not a safe regular file")
                    matches.append(fd)
                    if len(matches) > 1:
                        return matches
        except OSError:
            fail("sessions tree could not be enumerated safely")
    return matches


def exact_match_fds(root: Path, thread_id: str) -> list[int]:
    return exact_match_fds_windows(root, thread_id) if os.name == "nt" else exact_match_fds_posix(root, thread_id)


def string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def unique_required(values: Iterable[str | None], label: str, *, allow_none: bool = False) -> str | None:
    items = list(values)
    if not items or (not allow_none and any(value is None or value == "" for value in items)):
        fail(f"missing {label}")
    if len(set(items)) != 1:
        fail(f"conflicting {label}")
    value = items[0]
    if not allow_none and not value:
        fail(f"missing {label}")
    return value


def inspect_rollout_fd(descriptor: int, thread_id: str) -> dict[str, Any]:
    session_payloads: list[dict[str, Any]] = []
    turn_payloads: list[dict[str, Any]] = []
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8", errors="strict", newline="") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                fail("matched rollout is not a safe regular file")
            if opened.st_size <= 0 or opened.st_size > MAX_ROLLOUT_BYTES:
                fail("matched rollout size is invalid")
            for line in handle:
                if len(line) > MAX_LINE_CHARS:
                    fail("rollout contains an oversized JSONL record")
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    fail("rollout contains invalid JSONL")
                if not isinstance(record, dict) or not isinstance(payload := record.get("payload"), dict):
                    continue
                if record.get("type") == "session_meta":
                    session_payloads.append(payload)
                elif record.get("type") == "turn_context":
                    turn_payloads.append(payload)
            final = os.fstat(handle.fileno())
            if (opened.st_size, getattr(opened, "st_mtime_ns", None), opened.st_ino, opened.st_dev) != (
                final.st_size, getattr(final, "st_mtime_ns", None), final.st_ino, final.st_dev
            ):
                fail("rollout changed during inspection")
    except UnicodeDecodeError:
        fail("rollout is not valid UTF-8")
    except OSError:
        fail("rollout could not be read")

    if len(session_payloads) != 1 or not turn_payloads:
        fail("missing or ambiguous session metadata or turn context")
    session = session_payloads[0]
    observed_thread_id = string_or_none(session.get("id"))
    agent_role = string_or_none(session.get("agent_role"))
    if observed_thread_id != thread_id:
        fail("session metadata does not identify the requested thread")
    if not agent_role:
        fail("missing agent role")

    models = [string_or_none(turn.get("model")) for turn in turn_payloads]
    efforts = [string_or_none(turn.get("effort")) for turn in turn_payloads]
    sandboxes = [string_or_none(v.get("type")) if isinstance(v := turn.get("sandbox_policy"), dict) else None for turn in turn_payloads]
    permissions = [string_or_none(v.get("type")) if isinstance(v := turn.get("permission_profile"), dict) else None for turn in turn_payloads]
    working_dirs = [string_or_none(turn.get("cwd")) for turn in turn_payloads]
    return {
        "thread_id": observed_thread_id,
        "parent_thread_id": string_or_none(session.get("parent_thread_id")),
        "agent_role": agent_role,
        "agent_path": string_or_none(session.get("agent_path")),
        "model_provider": string_or_none(session.get("model_provider")),
        "model": unique_required(models, "model"),
        "effort": unique_required(efforts, "effort"),
        "sandbox_policy_type": unique_required(sandboxes, "sandbox policy types", allow_none=True),
        "permission_profile_type": unique_required(permissions, "permission profile types", allow_none=True),
        "cwd": unique_required(working_dirs, "working directories", allow_none=True),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("thread_id", help="exact lowercase subagent thread UUID")
    parser.add_argument("--sessions-dir", type=Path, default=None, help="explicit Codex sessions root")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not THREAD_ID_RE.fullmatch(args.thread_id):
        fail("thread_id must be a lowercase UUID")
    sessions_dir = args.sessions_dir or default_sessions_dir()
    try:
        root_info = sessions_dir.lstat()
    except OSError:
        fail("sessions directory is unavailable")
    if stat.S_ISLNK(root_info.st_mode) or _is_reparse(root_info) or not stat.S_ISDIR(root_info.st_mode):
        fail("sessions directory is not a safe directory")

    matches = exact_match_fds(sessions_dir, args.thread_id)
    if not matches:
        fail("no rollout filename matched the requested thread id")
    if len(matches) != 1:
        for fd in matches:
            try:
                os.close(fd)
            except OSError:
                pass
        fail("multiple rollout filenames matched the requested thread id")
    print(json.dumps(inspect_rollout_fd(matches[0], args.thread_id), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
