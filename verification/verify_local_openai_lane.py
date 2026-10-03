#!/usr/bin/env python3
"""Runtime fixtures for the optional AMS local OpenAI-compatible lane."""
from __future__ import annotations

import json
import http.client
import importlib.util
import io
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "extensions/ams-local-openai-lane/tools/local_openai_lane.py"


class Handler(BaseHTTPRequestHandler):
    gets = 0
    posts = 0
    response_model = "qwen38"
    omit_model = False

    def log_message(self, *_args) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        type(self).gets += 1
        body = json.dumps({"data": [{"id": "qwen38"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        type(self).posts += 1
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        assert request["model"] == "qwen38"
        if self.path.endswith("/responses"):
            payload = {"output_text": "local response result"}
        else:
            payload = {"choices": [{"message": {"content": "local result"}}]}
        if not type(self).omit_model:
            payload["model"] = type(self).response_model
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def profile_text(
    base_url: str,
    *,
    context: int = 32768,
    api: str = "chat_completions",
    start_command: list[str] | None = None,
    stop_command: list[str] | None = None,
    keep_loaded: bool = True,
    allowed_observed_models: list[str] | None = None,
) -> str:
    lines = [
        "profile_version = 1",
        'name = "qwen38-32k"',
        'model_key = "qwen38"',
        f"context_length = {context}",
        f'base_url = "{base_url}"',
        f'api = "{api}"',
        'model = "qwen38"',
        'readiness_path = "/models"',
        "readiness_timeout_seconds = 2",
        "startup_grace_seconds = 0",
        "request_timeout_seconds = 5",
        "command_timeout_seconds = 5",
        "context_reserve_tokens = 1024",
        "max_output_tokens = 1024",
        f"keep_loaded_default = {'true' if keep_loaded else 'false'}",
    ]
    if allowed_observed_models is not None:
        quoted = ", ".join(json.dumps(item) for item in allowed_observed_models)
        lines.append(f"allowed_observed_models = [{quoted}]")
    if start_command:
        quoted = ", ".join(json.dumps(item) for item in start_command)
        lines.append(f"start_command = [{quoted}]")
    if stop_command:
        quoted = ", ".join(json.dumps(item) for item in stop_command)
        lines.append(f"stop_command = [{quoted}]")
    return "\n".join(lines) + "\n"


def make_project(root: Path, profile: str, request: dict[str, object]) -> tuple[Path, Path]:
    root = root.resolve(strict=True)
    project = root / "project"
    profile_dir = project / ".codex/ams-local-llm/profiles"
    profile_dir.mkdir(parents=True)
    (profile_dir / "qwen38-32k.toml").write_text(profile, encoding="utf-8", newline="\n")
    request_path = root / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8", newline="\n")
    return project, request_path


def run_helper(project: Path, request_path: Path, *, env: dict[str, str] | None = None, lifecycle: str = "keep") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER), "--project-root", str(project), "--profile", "qwen38-32k", "--request-file", str(request_path), "--lifecycle", lifecycle],
        text=True,
        capture_output=True,
        timeout=15,
        env=env,
    )


def run_stop(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER), "--project-root", str(project), "--profile", "qwen38-32k", "--stop-only"],
        text=True,
        capture_output=True,
        timeout=15,
    )


class LocalLane(unittest.TestCase):
    def setUp(self) -> None:
        Handler.gets = 0
        Handler.posts = 0
        Handler.response_model = "qwen38"
        Handler.omit_model = False

    def test_protocol_failures_after_start_cleanup_once_without_response_leaks(self) -> None:
        spec = importlib.util.spec_from_file_location("cleanup_lane", HELPER)
        assert spec and spec.loader
        lane = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lane)
        sentinel = "PRIVATE_RESPONSE_SENTINEL"

        class MemorySocket:
            def __init__(self, raw):
                self.raw = raw

            def makefile(self, *args, **kwargs):
                return io.BytesIO(self.raw)

        def response(raw):
            result = http.client.HTTPResponse(MemorySocket(raw))
            result.begin()  # Exercise the real parser, not a fabricated exception.
            return result

        good = b'HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\n{"data": []}'
        truncated = (b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n40\r\n'
                     + sentinel.encode())
        for phase in ("readiness", "inference"):
            for failure in ("open", "read", "error-body"):
                with self.subTest(phase=phase, failure=failure), tempfile.TemporaryDirectory() as td:
                    project, request = make_project(
                        Path(td), profile_text("http://127.0.0.1:1/v1", start_command=["fixture-start"],
                                               stop_command=["fixture-stop"]),
                        {"user": "fixture only", "estimated_input_tokens": 32, "max_output_tokens": 16},
                    )
                    calls = []
                    commands = []
                    def open_fixture(req, timeout):
                        calls.append(req.method)
                        if len(calls) == 1:
                            raise lane.urllib.error.URLError("fixture unavailable before start")
                        if phase == "inference" and len(calls) == 2:
                            return response(good)
                        if failure == "open":
                            return response((sentinel + "\r\n").encode())
                        parsed = response(truncated)
                        if failure == "error-body":
                            raise lane.urllib.error.HTTPError(req.full_url, 500, "fixture", {}, parsed)
                        return parsed
                    def command_fixture(command, timeout, label):
                        commands.append((command, label))
                    out, err = io.StringIO(), io.StringIO()
                    argv = [str(HELPER), "--project-root", str(project), "--profile", "qwen38-32k",
                            "--request-file", str(request), "--lifecycle", "keep"]
                    with patch.object(sys, "argv", argv), patch.object(lane.HTTP_OPENER, "open", side_effect=open_fixture), \
                            patch.object(lane, "run_command", side_effect=command_fixture), \
                            redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit) as raised:
                        lane.main()
                    self.assertEqual(raised.exception.code, 20)
                    payload = json.loads(out.getvalue())
                    self.assertEqual(payload["status"], "malformed-response")
                    self.assertEqual(payload["cleanup"], "stopped")
                    self.assertNotIn("detail", payload)
                    self.assertEqual(commands, [(["fixture-start"], "start"), (["fixture-stop"], "cleanup-stop")])
                    self.assertEqual(calls, ["GET", "GET"] if phase == "readiness" else ["GET", "GET", "POST"])
                    self.assertNotIn(sentinel, out.getvalue() + err.getvalue())
                    self.assertEqual(err.getvalue(), "")

    def test_remote_disconnect_preserves_one_start_and_cleanup_contract(self) -> None:
        spec = importlib.util.spec_from_file_location("disconnect_lane", HELPER)
        assert spec and spec.loader
        lane = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lane)

        class MemorySocket:
            def __init__(self, raw):
                self.raw = raw

            def makefile(self, *args, **kwargs):
                return io.BytesIO(self.raw)

        def response(payload):
            if payload is None:
                raw = b""  # Real HTTP parser raises RemoteDisconnected at EOF.
            else:
                body = json.dumps(payload).encode()
                raw = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
            result = http.client.HTTPResponse(MemorySocket(raw))
            result.begin()
            return result

        for outcome in ("recovered", "readiness-disconnect", "inference-disconnect"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td), profile_text("http://127.0.0.1:1/v1", start_command=["fixture-start"],
                                           stop_command=["fixture-stop"]),
                    {"user": "fixture only", "estimated_input_tokens": 32, "max_output_tokens": 16},
                )
                calls, commands = [], []
                def open_fixture(req, timeout):
                    calls.append(req.method)
                    if len(calls) == 1 or (len(calls) == 2 and outcome == "readiness-disconnect"):
                        return response(None)
                    if len(calls) == 2:
                        return response({"data": []})
                    if outcome == "inference-disconnect":
                        return response(None)
                    return response({"model": "qwen38", "choices": [{"message": {"content": "fixture success"}}]})
                def command_fixture(command, timeout, label):
                    commands.append((command, label))
                out, err = io.StringIO(), io.StringIO()
                argv = [str(HELPER), "--project-root", str(project), "--profile", "qwen38-32k",
                        "--request-file", str(request), "--lifecycle", "keep"]
                with patch.object(sys, "argv", argv), patch.object(lane.HTTP_OPENER, "open", side_effect=open_fixture), \
                        patch.object(lane, "run_command", side_effect=command_fixture), \
                        redirect_stdout(out), redirect_stderr(err), self.assertRaises(SystemExit) as raised:
                    lane.main()
                payload = json.loads(out.getvalue())
                self.assertEqual(err.getvalue(), "")
                self.assertEqual(calls, ["GET", "GET"] if outcome == "readiness-disconnect" else ["GET", "GET", "POST"])
                expected = [(["fixture-start"], "start")]
                if outcome == "recovered":
                    self.assertEqual(raised.exception.code, 0)
                    self.assertEqual(payload["status"], "complete")
                    self.assertEqual(payload["load_ownership"], "companion-started")
                    self.assertTrue(payload["started_model"])
                else:
                    self.assertEqual(raised.exception.code, 20)
                    self.assertEqual(payload["status"], "unavailable")
                    self.assertEqual(payload["cleanup"], "stopped")
                    expected.append((["fixture-stop"], "cleanup-stop"))
                self.assertEqual(commands, expected)

    def test_online_single_readiness_and_single_inference(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td),
                    profile_text(f"http://127.0.0.1:{server.server_port}/v1"),
                    {"system": "bounded", "user": "analyze this", "estimated_input_tokens": 20, "max_output_tokens": 64},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "complete")
                self.assertEqual(payload["response_text"], "local result")
                self.assertEqual(payload["requested_model"], "qwen38")
                self.assertEqual(payload["observed_model"], "qwen38")
                self.assertEqual(payload["model_state"], "kept")
                self.assertEqual(payload["load_ownership"], "preexisting")
                self.assertEqual(Handler.gets, 1)
                self.assertEqual(Handler.posts, 1)
        finally:
            server.shutdown()
            server.server_close()


    def test_responses_api_and_close_command(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                marker = root / "stop-count.txt"
                command = [sys.executable, "-c", f"from pathlib import Path; p=Path({str(marker)!r}); p.write_text('stopped')"]
                project, request = make_project(
                    root,
                    profile_text(f"http://127.0.0.1:{server.server_port}/v1", api="responses", stop_command=command, keep_loaded=False),
                    {"system": "bounded", "user": "analyze", "max_output_tokens": 64},
                )
                result = subprocess.run(
                    [sys.executable, str(HELPER), "--project-root", str(project), "--profile", "qwen38-32k", "--request-file", str(request), "--lifecycle", "auto"],
                    text=True, capture_output=True, timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["response_text"], "local response result")
                self.assertEqual(marker.read_text(), "stopped")
        finally:
            server.shutdown()
            server.server_close()


    def test_missing_chat_model_identity_fails_closed(self) -> None:
        Handler.omit_model = True
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td), profile_text(f"http://127.0.0.1:{server.server_port}/v1"),
                    {"system": "", "user": "small", "max_output_tokens": 64},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 20)
                self.assertEqual(json.loads(result.stdout)["status"], "model-identity-missing")
        finally:
            server.shutdown(); server.server_close()

    def test_mismatched_chat_model_identity_fails_closed(self) -> None:
        Handler.response_model = "different-model"
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td), profile_text(f"http://127.0.0.1:{server.server_port}/v1"),
                    {"system": "", "user": "small", "max_output_tokens": 64},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 20)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "model-mismatch")
                self.assertEqual(payload["requested_model"], "qwen38")
                self.assertEqual(payload["observed_model"], "different-model")
        finally:
            server.shutdown(); server.server_close()

    def test_missing_responses_model_identity_fails_closed(self) -> None:
        Handler.omit_model = True
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td), profile_text(f"http://127.0.0.1:{server.server_port}/v1", api="responses"),
                    {"system": "", "user": "small", "max_output_tokens": 64},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 20)
                self.assertEqual(json.loads(result.stdout)["status"], "model-identity-missing")
        finally:
            server.shutdown(); server.server_close()

    def test_mismatched_responses_model_identity_fails_closed(self) -> None:
        Handler.response_model = "different-model"
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td), profile_text(f"http://127.0.0.1:{server.server_port}/v1", api="responses"),
                    {"system": "", "user": "small", "max_output_tokens": 64},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 20)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "model-mismatch")
                self.assertEqual(payload["requested_model"], "qwen38")
                self.assertEqual(payload["observed_model"], "different-model")
        finally:
            server.shutdown(); server.server_close()

    def test_explicit_same_model_alias_is_accepted(self) -> None:
        Handler.response_model = "qwen38-alias"
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td),
                    profile_text(
                        f"http://127.0.0.1:{server.server_port}/v1",
                        allowed_observed_models=["qwen38-alias"],
                    ),
                    {"system": "", "user": "small", "max_output_tokens": 64},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["requested_model"], "qwen38")
                self.assertEqual(payload["observed_model"], "qwen38-alias")
        finally:
            server.shutdown(); server.server_close()

    def test_context_too_small_makes_no_network_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project, request = make_project(
                Path(td),
                profile_text("http://127.0.0.1:1/v1", context=2048),
                {"system": "", "user": "x" * 10000, "estimated_input_tokens": 8000, "max_output_tokens": 1024},
            )
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 10)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "context-too-small")

    def test_start_command_runs_once_then_failure_is_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = root / "start-count.txt"
            stopped = root / "stop-count.txt"
            command = [sys.executable, "-c", f"from pathlib import Path; p=Path({str(marker)!r}); p.write_text((p.read_text() if p.exists() else '')+'x')"]
            stop = [sys.executable, "-c", f"from pathlib import Path; p=Path({str(stopped)!r}); p.write_text((p.read_text() if p.exists() else '')+'x')"]
            project, request = make_project(
                root,
                profile_text("http://127.0.0.1:1/v1", start_command=command, stop_command=stop),
                {"system": "", "user": "small request", "max_output_tokens": 64},
            )
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "unavailable")
            self.assertEqual(marker.read_text(), "x")
            self.assertEqual(stopped.read_text(), "x")
            self.assertEqual(payload["cleanup"], "stopped")

    def test_nonzero_start_after_partial_resource_creation_runs_cleanup_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = root / "partially-started.txt"
            start = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('started'); raise SystemExit(7)"]
            stop = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).unlink(missing_ok=True)"]
            project, request = make_project(
                root,
                profile_text("http://127.0.0.1:1/v1", start_command=start, stop_command=stop),
                {"system": "", "user": "small request", "max_output_tokens": 64},
            )
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "unavailable")
            self.assertEqual(payload["cleanup"], "stopped")
            self.assertFalse(marker.exists())

    def test_stop_only_runs_exact_stop_without_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = root / "stopped.txt"
            stop = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('stopped')"]
            project, _ = make_project(
                root,
                profile_text("http://127.0.0.1:1/v1", stop_command=stop),
                {"system": "", "user": "unused"},
            )
            result = run_stop(project)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "stopped")
            self.assertEqual(marker.read_text(), "stopped")

    def test_context_length_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            text = profile_text("http://127.0.0.1:1/v1").replace("context_length = 32768\n", "")
            project, request = make_project(root, text, {"system": "", "user": "small"})
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-profile")

    def test_close_semantics_require_stop_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, request = make_project(
                root,
                profile_text("http://127.0.0.1:1/v1", keep_loaded=False),
                {"system": "", "user": "small"},
            )
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-profile")

    def test_start_command_requires_stop_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            start = [sys.executable, "-c", "pass"]
            project, request = make_project(
                root, profile_text("http://127.0.0.1:1/v1", start_command=start),
                {"system": "", "user": "small"},
            )
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-profile")

    def test_supplied_token_estimate_avoids_byte_overpromotion(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td),
                    profile_text(f"http://127.0.0.1:{server.server_port}/v1", context=4096),
                    {"system": "", "user": "x" * 6000, "estimated_input_tokens": 1000, "max_output_tokens": 1024},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["estimated_input_tokens"], 1000)
        finally:
            server.shutdown(); server.server_close()

    def test_request_inside_project_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, _ = make_project(root, profile_text("http://127.0.0.1:1/v1"), {"system": "", "user": "small"})
            request = project / "request.json"
            request.write_text(json.dumps({"system": "", "user": "small"}), encoding="utf-8")
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-request")

    def test_redirected_request_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(strict=True)
            project, request = make_project(root, profile_text("http://127.0.0.1:1/v1"), {"system": "", "user": "small"})
            link = root / "request-link"
            try:
                link.symlink_to(root, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            result = run_helper(project, link / request.name)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-request")

    def test_relative_request_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, request = make_project(root, profile_text("http://127.0.0.1:1/v1"), {"system": "", "user": "small"})
            result = subprocess.run(
                [sys.executable, str(HELPER), "--project-root", str(project), "--profile", "qwen38-32k", "--request-file", request.name],
                cwd=root, text=True, capture_output=True, timeout=15,
            )
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-request")

    def test_stdin_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, _ = make_project(root, profile_text("http://127.0.0.1:1/v1"), {"system": "", "user": "small"})
            result = subprocess.run(
                [sys.executable, str(HELPER), "--project-root", str(project), "--profile", "qwen38-32k", "--request-file", "-"],
                input='{"system":"","user":"small"}', text=True, capture_output=True, timeout=15,
            )
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-request")

    def test_unknown_profile_fields_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            text = profile_text("http://127.0.0.1:1/v1") + 'invented = "bad"\n'
            project, request = make_project(root, text, {"system": "", "user": "small", "max_output_tokens": 64})
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-profile")


    def test_configured_proxy_is_ignored(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td),
                    profile_text(f"http://127.0.0.1:{server.server_port}/v1"),
                    {"system": "", "user": "small", "max_output_tokens": 64},
                )
                env = os.environ.copy()
                env.update({"HTTP_PROXY": "http://127.0.0.1:1", "HTTPS_PROXY": "http://127.0.0.1:1"})
                result = run_helper(project, request, env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            server.shutdown()
            server.server_close()

    def test_http_readiness_error_does_not_run_start_command(self) -> None:
        class Unauthorized(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None: return
            def do_GET(self) -> None:  # noqa: N802
                self.send_response(401); self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Unauthorized)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                marker = root / "should-not-start.txt"
                command = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('bad')"]
                project, request = make_project(
                    root,
                    profile_text(f"http://127.0.0.1:{server.server_port}/v1", start_command=command, stop_command=[sys.executable, "-c", "pass"]),
                    {"system": "", "user": "small", "max_output_tokens": 64},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 20)
                self.assertEqual(json.loads(result.stdout)["status"], "request-failed")
                self.assertFalse(marker.exists())
        finally:
            server.shutdown(); server.server_close()

    def test_redirect_is_not_followed(self) -> None:
        class Redirect(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None: return
            def do_GET(self) -> None:  # noqa: N802
                self.send_response(302); self.send_header("Location", "http://127.0.0.1:1/other"); self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                project, request = make_project(
                    Path(td), profile_text(f"http://127.0.0.1:{server.server_port}/v1"),
                    {"system": "", "user": "small", "max_output_tokens": 64},
                )
                result = run_helper(project, request)
                self.assertEqual(result.returncode, 20)
                self.assertEqual(json.loads(result.stdout)["status"], "request-failed")
        finally:
            server.shutdown(); server.server_close()

    def test_base_url_query_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project, request = make_project(
                Path(td), profile_text("http://127.0.0.1:1/v1?redirect=bad"),
                {"system": "", "user": "small", "max_output_tokens": 64},
            )
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-profile")

    def test_failed_command_output_is_not_relayed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            secret = "DO-NOT-RELAY-LOCAL-COMMAND-OUTPUT"
            command = [sys.executable, "-c", f"print({secret!r}); raise SystemExit(7)"]
            project, request = make_project(
                Path(td), profile_text("http://127.0.0.1:1/v1", start_command=command, stop_command=[sys.executable, "-c", "pass"]),
                {"system": "", "user": "small", "max_output_tokens": 64},
            )
            result = run_helper(project, request)
            self.assertEqual(result.returncode, 20)
            self.assertNotIn(secret, result.stdout + result.stderr)

    def test_missing_request_returns_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project, _ = make_project(
                root, profile_text("http://127.0.0.1:1/v1"),
                {"system": "", "user": "small", "max_output_tokens": 64},
            )
            result = run_helper(project, root / "missing.json")
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-request")

    @unittest.skipIf(os.name == "nt", "symlink fixture uses Unix semantics")
    def test_redirected_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(strict=True)
            profile_dir = root / ".codex/ams-local-llm/profiles"
            profile_dir.mkdir(parents=True)
            outside = root / "outside.toml"
            outside.write_text(profile_text("http://127.0.0.1:1/v1"), encoding="utf-8")
            (profile_dir / "qwen38-32k.toml").symlink_to(outside)
            request = root / "request.json"
            request.write_text(json.dumps({"system": "", "user": "small"}), encoding="utf-8")
            result = run_helper(root, request)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-profile")


    @unittest.skipIf(os.name == "nt", "symlink fixture uses Unix semantics")
    def test_redirected_profile_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve(strict=True)
            outside = root / "outside-profiles"
            outside.mkdir()
            (outside / "qwen38-32k.toml").write_text(profile_text("http://127.0.0.1:1/v1"), encoding="utf-8")
            (root / ".codex").mkdir()
            (root / ".codex/ams-local-llm").mkdir()
            (root / ".codex/ams-local-llm/profiles").symlink_to(outside, target_is_directory=True)
            request = root / "request.json"
            request.write_text(json.dumps({"system": "", "user": "small"}), encoding="utf-8")
            result = run_helper(root, request)
            self.assertEqual(result.returncode, 20)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid-profile")


if __name__ == "__main__":
    unittest.main()
