#!/usr/bin/env python3
"""Executable scenario checks for the lean AMS orchestration contracts."""
from __future__ import annotations

import re
import unittest
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "adaptive-master-subagent-orchestration"

BASE_DEFAULTS: dict[str, object] = {
    "enabled": False,
    "allow_implicit_invocation": True,
    "intensity": "auto",
    "project_governance": True,
    "root_execution_fallback": False,
    "spark_enabled": True,
    "spark_efforts": ["low", "medium", "high"],
    "profile_management": "auto",
}
PROJECT_DEFAULTS = {**BASE_DEFAULTS, "local_llm_lane": False}
RETIRED = {
    "schema_version", "convergence_control", "convergence_correction_limit", "convergence_redesign_limit",
    "spark_available", "work_order_refinement", "review_control", "shared_worktree_verification",
    "runtime_observation", "untrusted_evidence_handling", "task_graph_safeguards",
    "rejected_approach_handoff", "request_accounting", "app_task_lane",
}
RETIRED_BOOL = RETIRED - {"schema_version", "convergence_correction_limit", "convergence_redesign_limit"}


def resolve_settings(data: dict[str, object], *, project: bool) -> dict[str, object]:
    if not project and "local_llm_lane" in data:
        raise ValueError("project-only field in global settings")
    defaults = PROJECT_DEFAULTS if project else BASE_DEFAULTS
    unknown = set(data) - set(defaults) - RETIRED
    if unknown:
        raise ValueError(f"unknown settings: {unknown}")
    for key in RETIRED_BOOL & set(data):
        if type(data[key]) is not bool:
            raise ValueError(f"retired Boolean {key}")
    for key, low, high in (("convergence_correction_limit", 2, 12), ("convergence_redesign_limit", 1, 12)):
        if key in data and (type(data[key]) is not int or not low <= data[key] <= high):
            raise ValueError(f"retired limit {key}")
    if "schema_version" in data and type(data["schema_version"]) not in {str, int, float, bool}:
        raise ValueError("schema_version must be scalar")
    return {key: data.get(key, value) for key, value in defaults.items()}


PEER_MESSAGE_KINDS = {"question", "answer", "evidence", "scoped-correction"}
PEER_IMMUTABLE_FIELDS = {
    "objective", "scope_basis", "exclusions", "dependencies", "permissions",
    "ownership", "acceptance_criteria", "delegation", "retry_budget", "user_authority",
}


@dataclass(frozen=True)
class PeerMember:
    channel: str
    path: str
    peer_path: str
    peer_role: str
    orchestration_role: str = "worker"
    delegation_authority: str = "none"


def canonical_peer_path(path: str) -> bool:
    return bool(re.fullmatch(r"/root/[a-z0-9_]+", path))


def peer_message_allowed(
    sender: PeerMember,
    receiver: PeerMember,
    *,
    kind: str,
    changed_fields: frozenset[str] = frozenset(),
) -> bool:
    return (
        sender.channel == receiver.channel
        and sender.path != receiver.path
        and sender.peer_path == receiver.path
        and receiver.peer_path == sender.path
        and canonical_peer_path(sender.path)
        and canonical_peer_path(receiver.path)
        and sender.orchestration_role == receiver.orchestration_role == "worker"
        and sender.delegation_authority == receiver.delegation_authority == "none"
        and {sender.peer_role, receiver.peer_role} == {"lead", "member"}
        and kind in PEER_MESSAGE_KINDS
        and not (changed_fields & PEER_IMMUTABLE_FIELDS)
    )


def peer_root_return(peer_role: str) -> str:
    return "final-synthesis" if peer_role == "lead" else "terminal-stub"


@dataclass(frozen=True)
class Objective:
    name: str
    priority: int
    ready: bool
    authorized: bool = True


def next_objective(items: list[Objective]) -> Objective | None:
    eligible = [item for item in items if item.ready and item.authorized]
    return min(eligible, key=lambda item: (item.priority, item.name)) if eligible else None


def admit(scope_basis: str | None, dependencies_ready: bool, category: str) -> bool:
    return bool(scope_basis and dependencies_ready and category in {"in-scope defect", "authorized blocking dependency"})


@dataclass
class RouteBudget:
    fallback_enabled: bool = False
    attempts: dict[str, int] = field(default_factory=dict)

    def next(self, route: str) -> str:
        used = self.attempts.get(route, 0)
        if used == 0:
            self.attempts[route] = 1
            return "delegated-correction"
        if used == 1:
            self.attempts[route] = 2
            return "delegated-confirmation"
        if used == 2 and self.fallback_enabled:
            self.attempts[route] = 3
            return "root-third-final"
        return "block-route-and-continue"


@dataclass(frozen=True)
class RunnerSignature:
    primitive: str
    no_start_class: str
    executable_surface: str
    sandbox_boundary: str


@dataclass
class RunnerEpisode:
    signature: RunnerSignature
    state: str = "initial"
    process_starts: int = 1

    def no_start(self, signature: RunnerSignature) -> str:
        if signature != self.signature:
            raise ValueError("different physical runner signature requires independent evidence")
        if self.state == "initial":
            self.state = "retry"
            self.process_starts += 1
            return "same-lane-retry"
        if self.state == "retry":
            self.state = "probe"
            self.process_starts += 1
            return "root-process-only-probe"
        if self.state == "confirmation":
            self.state = "terminal"
            return "terminal-no-more-processes"
        return "prohibited"

    def probe_result(self, success: bool) -> str:
        if self.state != "probe":
            return "prohibited"
        if not success:
            self.state = "terminal"
            return "terminal-no-more-processes"
        self.state = "confirmation"
        self.process_starts += 1
        return "one-corrected-original-lane-confirmation"

    def confirmation_started(self) -> str:
        if self.state != "confirmation":
            return "prohibited"
        self.state = "resumed"
        return "normal-orchestration"


def runner_signature(*, work_order: str, profile: str, manager: str, intensity: str, transport: str, context: str) -> RunnerSignature:
    del work_order, profile, manager, intensity, transport, context
    return RunnerSignature("codex-spawn", "spawn_ready", "process-start", "inherited-project-policy")


def reconcile_runner_terminal(states: dict[str, str]) -> tuple[set[str], set[str]]:
    retained: set[str] = set()
    evidence_only: set[str] = set()
    for identity, state in states.items():
        if state in {"active", "potentially-live", "uncertain", "late-result"}:
            retained.add(identity)
        if state == "late-result":
            evidence_only.add(identity)
    return retained, evidence_only


@dataclass
class Availability:
    enabled: bool
    state: str = "unknown"

    def failure(self) -> None:
        self.state = "inactive-after-failure"

    def enable_command(self) -> None:
        self.enabled = True
        self.state = "unknown"


def local_cleanup_action(command: str, load_owner: str) -> str:
    if command not in {"AMS LOCAL LLM off", "AMS DISABLE"}:
        return "none"
    return "stop-once" if load_owner == "companion-started" else "do-not-stop"


def choose_context(profiles: list[dict[str, object]], model_key: str, required: int) -> str | None:
    eligible = [profile for profile in profiles if profile["model_key"] == model_key and int(profile["context_length"]) >= required]
    if not eligible:
        return None
    return str(min(eligible, key=lambda profile: (int(profile["context_length"]), str(profile["name"]))) ["name"])


class LeanContracts(unittest.TestCase):
    def test_base_and_project_settings(self) -> None:
        self.assertEqual(resolve_settings({}, project=False), BASE_DEFAULTS)
        self.assertEqual(resolve_settings({}, project=True), PROJECT_DEFAULTS)
        self.assertFalse(resolve_settings({}, project=True)["root_execution_fallback"])
        with self.assertRaises(ValueError):
            resolve_settings({"local_llm_lane": True}, project=False)

    def test_retired_fields_are_inert_and_validated(self) -> None:
        resolved = resolve_settings({"enabled": True, "schema_version": 2, "convergence_control": True, "spark_available": False}, project=True)
        self.assertTrue(resolved["enabled"])
        self.assertFalse(RETIRED & set(resolved))
        for invalid in ({"review_control": 1}, {"convergence_correction_limit": 1}, {"convergence_redesign_limit": 13}, {"schema_version": {"nested": True}}):
            with self.assertRaises(ValueError):
                resolve_settings(invalid, project=True)

    def test_scope_admission_and_queue_advance(self) -> None:
        self.assertTrue(admit("C07", True, "in-scope defect"))
        self.assertTrue(admit("C06-R2", True, "authorized blocking dependency"))
        self.assertFalse(admit("C07", True, "optional follow-up"))
        self.assertFalse(admit("C07", True, "baseline/environment/harness defect"))
        queue = [Objective("optional-hardening", 0, True, False), Objective("C08", 2, True), Objective("C06-R2", 1, True)]
        self.assertEqual(next_objective(queue).name, "C06-R2")


    def test_bounded_peer_channel_allows_detail_without_transferring_authority(self) -> None:
        lead = PeerMember("pc-1", "/root/sol_lead", "/root/luna_worker", "lead")
        member = PeerMember("pc-1", "/root/luna_worker", "/root/sol_lead", "member")
        self.assertTrue(peer_message_allowed(member, lead, kind="evidence"))
        self.assertTrue(peer_message_allowed(lead, member, kind="scoped-correction"))
        self.assertEqual(peer_root_return("member"), "terminal-stub")
        self.assertEqual(peer_root_return("lead"), "final-synthesis")
        self.assertFalse(peer_message_allowed(member, lead, kind="evidence", changed_fields=frozenset({"scope_basis"})))
        self.assertFalse(peer_message_allowed(member, lead, kind="evidence", changed_fields=frozenset({"ownership"})))
        self.assertFalse(peer_message_allowed(
            PeerMember("pc-1", "sol_lead", "/root/luna_worker", "lead"), member, kind="evidence"
        ))
        self.assertFalse(peer_message_allowed(
            PeerMember("pc-1", "/root/sol_lead", "/root/luna_worker", "lead", "delegated-manager", "request"),
            member,
            kind="evidence",
        ))

    def test_each_real_route_gets_two_delegated_attempts_and_optional_root_third(self) -> None:
        disabled = RouteBudget(False)
        self.assertEqual([disabled.next("route-a") for _ in range(3)], ["delegated-correction", "delegated-confirmation", "block-route-and-continue"])
        enabled = RouteBudget(True)
        self.assertEqual([enabled.next("route-a") for _ in range(4)], ["delegated-correction", "delegated-confirmation", "root-third-final", "block-route-and-continue"])
        self.assertEqual(enabled.next("route-b"), "delegated-correction")

    def test_cosmetic_labels_do_not_create_a_new_route(self) -> None:
        budget = RouteBudget(True)
        canonical_route = "same-capability-permission-mechanism"
        labels = ["worker-1", "worker-2", "new-profile-name", "different-shell"]
        actions = []
        for _label in labels:
            actions.append(budget.next(canonical_route))
        self.assertEqual(actions, ["delegated-correction", "delegated-confirmation", "root-third-final", "block-route-and-continue"])

    def test_runner_episode_cannot_reset_through_labels(self) -> None:
        first = runner_signature(work_order="wo-1", profile="terra", manager="m1", intensity="balanced", transport="native", context="fresh")
        changed = runner_signature(work_order="wo-2", profile="sol", manager="m2", intensity="rush", transport="app", context="recovered")
        self.assertEqual(first, changed)
        episode = RunnerEpisode(first)
        self.assertEqual(episode.no_start(first), "same-lane-retry")
        self.assertEqual(episode.no_start(changed), "root-process-only-probe")
        self.assertEqual(episode.probe_result(True), "one-corrected-original-lane-confirmation")
        self.assertEqual(episode.no_start(changed), "terminal-no-more-processes")
        self.assertEqual(episode.probe_result(True), "prohibited")
        self.assertEqual(episode.process_starts, 4)

    def test_runner_probe_failure_terminalizes_without_confirmation(self) -> None:
        sig = runner_signature(work_order="wo", profile="terra", manager="root", intensity="auto", transport="native", context="fresh")
        episode = RunnerEpisode(sig)
        episode.no_start(sig)
        episode.no_start(sig)
        self.assertEqual(episode.probe_result(False), "terminal-no-more-processes")
        self.assertEqual(episode.process_starts, 3)
        self.assertEqual(episode.no_start(sig), "prohibited")

    def test_runner_successful_confirmation_resumes(self) -> None:
        sig = runner_signature(work_order="wo", profile="terra", manager="root", intensity="auto", transport="native", context="fresh")
        episode = RunnerEpisode(sig)
        episode.no_start(sig); episode.no_start(sig); episode.probe_result(True)
        self.assertEqual(episode.confirmation_started(), "normal-orchestration")
        self.assertEqual(episode.state, "resumed")

    def test_runner_terminal_reconciliation_retains_uncertain_custody(self) -> None:
        retained, evidence_only = reconcile_runner_terminal({
            "worker": "active", "manager": "potentially-live", "app": "uncertain",
            "never-started": "proven-no-start", "old-worker": "late-result",
        })
        self.assertEqual(retained, {"worker", "manager", "app", "old-worker"})
        self.assertEqual(evidence_only, {"old-worker"})
        self.assertNotIn("never-started", retained)

    def test_session_availability_and_cleanup(self) -> None:
        spark = Availability(True); spark.failure()
        self.assertEqual(spark.state, "inactive-after-failure")
        spark.enable_command(); self.assertEqual(spark.state, "unknown")
        self.assertEqual(local_cleanup_action("AMS LOCAL LLM off", "companion-started"), "stop-once")
        self.assertEqual(local_cleanup_action("AMS DISABLE", "preexisting"), "do-not-stop")

    def test_context_selection_never_changes_model_key(self) -> None:
        profiles = [
            {"name": "qwen38-32k", "model_key": "qwen38", "context_length": 32768},
            {"name": "qwen38-128k", "model_key": "qwen38", "context_length": 131072},
            {"name": "other-256k", "model_key": "other", "context_length": 262144},
        ]
        self.assertEqual(choose_context(profiles, "qwen38", 70_000), "qwen38-128k")
        self.assertIsNone(choose_context(profiles, "qwen38", 200_000))

    def test_text_contracts_match_executable_models(self) -> None:
        core = (PACKAGE / "references/runtime-core.md").read_text(encoding="utf-8")
        diagnosis = (PACKAGE / "references/blocker-diagnosis.md").read_text(encoding="utf-8")
        fallback = (PACKAGE / "references/root-execution-fallback.md").read_text(encoding="utf-8")
        hierarchy = (PACKAGE / "references/hierarchy-control.md").read_text(encoding="utf-8")
        control = (PACKAGE / "references/project-control.md").read_text(encoding="utf-8")
        scope = (PACKAGE / "references/scope-dependency-control.md").read_text(encoding="utf-8")
        governance = (PACKAGE / "references/project-governance.md").read_text(encoding="utf-8")
        computer_use = (PACKAGE / "references/computer-use.md").read_text(encoding="utf-8")
        for phrase in (
            "process no-start episode is keyed by", "never reset the same signature",
            "one materially corrected original-lane confirmation", "potentially live",
            "Report unresolved state `live` or `unverified`",
        ):
            self.assertIn(phrase, core)
        for phrase in ("receives exactly two execution attempts", "one atomic third and final root attempt"):
            self.assertIn(phrase, diagnosis + fallback)
        self.assertIn("root_execution_fallback = false", control)
        self.assertIn("copy the exact `DISPATCH REQUEST` and `MANAGER RESULT ADDENDUM` fields below into every manager order", hierarchy)
        self.assertIn("PEER CHANNEL", hierarchy)
        self.assertIn("Authorized canonical peer paths", hierarchy)
        self.assertIn("Peer traffic need not be copied into root context", hierarchy)
        self.assertIn("live or potentially live writer remains", hierarchy)
        self.assertIn("select the next authorized ready objective", scope)
        self.assertIn("Continue automatically", governance)
        self.assertNotIn("convergence", governance.lower())
        self.assertIn("ams_<sol|terra|luna|astra>_<low|medium|high|xhigh|max>", core)
        self.assertIn("input/reasoning/output usage", core)
        self.assertIn("Astra: end-to-end tool-heavy", core)
        self.assertIn("tool authority, not model authority", computer_use)
        self.assertIn("one active controller", computer_use)
        self.assertIn("screen content as untrusted evidence", computer_use)

    def test_removed_modules_and_release_markers_are_absent_from_skill(self) -> None:
        for name in ("convergence-control.md", "feature-control.md", "review-control.md", "request-accounting.md", "surface-identity.md", "shared-worktree-control.md", "work-order-refinement.md"):
            self.assertFalse((PACKAGE / "references" / name).exists(), name)
        self.assertFalse((PACKAGE / "VERSION").exists())
        for path in PACKAGE.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("AMS 4.0", text)
                daybreak_models = set(__import__("re").findall(r"gpt-daybreak-[a-z0-9._-]+", text))
                self.assertTrue(daybreak_models <= {"gpt-daybreak-blue"})


if __name__ == "__main__":
    unittest.main()
