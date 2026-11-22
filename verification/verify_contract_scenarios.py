#!/usr/bin/env python3
"""Executable scenario checks for the lean AMS orchestration contracts."""
from __future__ import annotations

import re
import itertools
import tomllib
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
    "continuity_ledger": True,
    "project_map": False,
    "project_verification": False,
    "premise_check": False,
    "model_governance": True,
    "model_guidance": True,
    "automatic_model_switching": True,
    "root_execution_fallback": False,
    "profile_management": "auto",
}
PROJECT_DEFAULTS = {**BASE_DEFAULTS, "local_llm_lane": False}
RETIRED = {
    "schema_version", "convergence_control", "convergence_correction_limit", "convergence_redesign_limit",
    "spark_available", "spark_enabled", "spark_efforts", "work_order_refinement", "review_control", "shared_worktree_verification",
    "runtime_observation", "untrusted_evidence_handling", "task_graph_safeguards",
    "rejected_approach_handoff", "request_accounting", "app_task_lane",
}
RETIRED_BOOL = RETIRED - {"spark_efforts", "schema_version", "convergence_correction_limit", "convergence_redesign_limit"}


def resolve_settings(data: dict[str, object], *, project: bool) -> dict[str, object]:
    if not project and "local_llm_lane" in data:
        raise ValueError("project-only field in global settings")
    defaults = PROJECT_DEFAULTS if project else BASE_DEFAULTS
    unknown = set(data) - set(defaults) - RETIRED
    if unknown:
        raise ValueError(f"unknown settings: {unknown}")
    for key in {key for key, default in defaults.items() if type(default) is bool} & set(data):
        if type(data[key]) is not bool:
            raise ValueError(f"policy Boolean {key}")
    for key in RETIRED_BOOL & set(data):
        if type(data[key]) is not bool:
            raise ValueError(f"retired Boolean {key}")
    for key, low, high in (("convergence_correction_limit", 2, 12), ("convergence_redesign_limit", 1, 12)):
        if key in data and (type(data[key]) is not int or not low <= data[key] <= high):
            raise ValueError(f"retired limit {key}")
    if "spark_efforts" in data:
        efforts = data["spark_efforts"]
        if (not isinstance(efforts, list) or any(type(e) is not str or e not in {"low", "medium", "high"} for e in efforts)
                or len(efforts) != len(set(efforts))):
            raise ValueError("retired Spark efforts")
    if "schema_version" in data and type(data["schema_version"]) not in {str, int, float, bool}:
        raise ValueError("schema_version must be scalar")
    return {key: data.get(key, value) for key, value in defaults.items()}


CONTINUITY_PATHS = {"continuity_ledger": "continuity.md", "project_map": "PROJECT-MAP.md"}
FUNCTION_FIELDS = {"LEDGER": "continuity_ledger", "PROJECT-MAP": "project_map",
                   "VERIFICATION": "project_verification", "PREMISE-CHECK": "premise_check"}


def function_control(values: dict[str, object], command: str) -> dict[str, object]:
    match = re.fullmatch(r"AMS (ENABLE|DISABLE) ([A-Z-]+)", command.upper())
    if match is None or match[2] not in FUNCTION_FIELDS:
        raise ValueError("not a function control")
    field = FUNCTION_FIELDS[match[2]]
    return {**values, field: match[1] == "ENABLE"}


def continuity_target(
    settings: dict[str, object], feature: str, *, phase: str, authorized_write: bool,
    active_session: bool = False,
    native_candidates: tuple[str, ...] = (), target_safe: bool = True,
    material: bool = True, absence_proven: bool = True,
) -> str | None:
    manual_map = phase == "manual-map" and feature == "project_map"
    automatic = phase == "active-work" and active_session and settings[feature]
    if (not (manual_map or automatic) or not authorized_write or not material
            or not target_safe or len(native_candidates) > 1):
        return None
    if native_candidates:
        return native_candidates[0]
    return CONTINUITY_PATHS[feature] if absence_proven else None


def apply_transition(history: dict[str, str], transition: str, facts: str) -> str:
    if transition in history:
        return "replay-no-op" if history[transition] == facts else "reconcile-as-new-correction"
    history[transition] = facts
    return "recorded"


def recovered_retry(kind: str, corroborated_attempts: int | None, terminal: bool | None) -> str:
    if corroborated_attempts is None or terminal is None:
        return "defer-unverified"
    if terminal or (kind == "non-runner" and corroborated_attempts >= 2):
        return "preserve-stop"
    return "use-remaining-budget"


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
    profile: str = ""


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
        and "ams_luna_low" not in {sender.profile, receiver.profile}
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

    def test_control_entry_and_legacy_settings(self) -> None:
        skill = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
        maintenance = (PACKAGE / "references/configuration-maintenance.md").read_text(encoding="utf-8")
        self.assertLess(skill.index("Handle AMS control commands"), skill.index("Resolve settings:"))
        self.assertIn("`AMS STATUS` never writes", skill)
        self.assertIn("For control-only requests, return", skill)
        self.assertIn("Compatibility reads never write", maintenance)
        self.assertNotIn("never runs implicitly", maintenance)
        original = {"enabled": True, "model_guidance": False, "convergence_control": True}
        for project in (False, True):
            resolved = resolve_settings(original, project=project)
            self.assertTrue(resolved["enabled"])
            self.assertFalse(resolved["model_guidance"])
            self.assertTrue(resolved["model_governance"])
            self.assertEqual(resolve_settings(resolved, project=project), resolved)
        self.assertIn("convergence_control", original)

    def test_continuity_defaults_and_independent_strict_controls(self) -> None:
        # Validate actual shipped default data against the pre-feature compatibility contract.
        control = (PACKAGE / "references/project-control.md").read_text(encoding="utf-8")
        defaults = tomllib.loads(control.split("```toml\n")[1].split("```")[0])
        self.assertEqual(defaults, BASE_DEFAULTS)
        old = {"enabled": False, "project_governance": False, "model_guidance": False}
        current = resolve_settings(old, project=True)
        self.assertTrue(current["continuity_ledger"])
        self.assertFalse(current["project_map"])
        no_ledger = function_control(current, "AMS disable ledger")
        self.assertEqual(no_ledger, {**current, "continuity_ledger": False})
        self.assertEqual(function_control(no_ledger, "AMS ENABLE LEDGER"), current)
        upkeep = function_control(current, "AMS ENABLE PROJECT-MAP")
        self.assertEqual(upkeep, {**current, "project_map": True})
        self.assertEqual(function_control(upkeep, "AMS DISABLE PROJECT-MAP"), current)
        for name, field in FUNCTION_FIELDS.items():
            enabled = function_control(current, f"AMS ENABLE {name}")
            self.assertEqual(enabled, {**current, field: True})
            self.assertEqual(function_control(enabled, f"AMS DISABLE {name}"), {**current, field: False})
        self.assertFalse(current["project_verification"])
        self.assertFalse(current["premise_check"])
        self.assertNotIn("continuity_ledger", old)
        for invalid in ("false", 0, [], {"nested": True}):
            for field in FUNCTION_FIELDS.values():
                for project in (False, True):
                    with self.assertRaises(ValueError):
                        resolve_settings({field: invalid}, project=project)
        for invalid in ("AMS ENABLE OTHER", "AMS LEDGER off", "AMS ENABLE PROJECT MAP", "AMS ENABLE LEDGER GLOBAL"):
            with self.assertRaises(ValueError):
                function_control(current, invalid)
        self.assertIn("Status probes nothing", control)
        self.assertIn("known path/state only; do not discover them", control)
        self.assertIn("never activation", control)

    def test_continuity_uses_native_or_defers_instead_of_parallel_fallback(self) -> None:
        # A late-discovered canonical ledger must supersede planned fallback creation.
        settings = resolve_settings({"enabled": True, "project_governance": False, "project_map": True}, project=True)
        allow = {"phase": "active-work", "authorized_write": True, "active_session": True}
        for feature, path in CONTINUITY_PATHS.items():
            self.assertEqual(continuity_target(settings, feature, **allow), path)
            self.assertEqual(continuity_target(settings, feature, **allow, native_candidates=("doc/native.md",)), "doc/native.md")
            for reason in (
                {"native_candidates": ("doc/one.md", "doc/two.md")},
                {"absence_proven": False},
                {"native_candidates": ("doc/native.md",), "target_safe": False},
                {"phase": "read-only", "authorized_write": False},
                {"authorized_write": False},
                {"phase": "activation-only"},
                {"phase": "install-only"},
                {"phase": "settings-only"},
                {"phase": "status"},
                {"active_session": False},
                {"material": False},
            ):
                self.assertIsNone(continuity_target(settings, feature, **(allow | reason)), reason)
            self.assertIsNone(continuity_target({**settings, feature: False}, feature, **allow))

    def test_ledger_reconciles_post_dispatch_interrupt_and_replay(self) -> None:
        history: dict[str, str] = {}
        self.assertEqual(apply_transition(history, "T1/A1/plan", "admitted"), "recorded")
        self.assertEqual(apply_transition(history, "T1/A1/plan", "admitted"), "replay-no-op")
        self.assertEqual(apply_transition(history, "T1/A1/end", "interrupted; start unknown"), "recorded")
        self.assertEqual(apply_transition(history, "T1/A1/end", "start verified"), "reconcile-as-new-correction")
        self.assertEqual(history["T1/A1/end"], "interrupted; start unknown")
        self.assertEqual(apply_transition(history, "T1/A1/end-correction1", "start verified by host"), "recorded")
        self.assertEqual(apply_transition(history, "T1/A2/failed-no-run", "no start verified"), "recorded")
        self.assertEqual(len(history), 4)
        contract = (PACKAGE / "references/project-continuity.md").read_text(encoding="utf-8")
        for status in ("no-run", "blockage", "rejection", "interruption", "supersession", "acceptance", "handoff"):
            self.assertIn(status, contract)
        self.assertIn("Do not imply a planned action ran", contract)
        self.assertIn("verify", contract.lower())
        self.assertIn("treat uncertain ownership as potentially live", contract)

    def test_one_shot_map_is_not_activation_or_automatic_maintenance(self) -> None:
        control = (PACKAGE / "references/project-control.md").read_text(encoding="utf-8")
        settings = resolve_settings({}, project=True)
        original = dict(settings)
        manual = {"phase": "manual-map", "authorized_write": True}
        self.assertEqual(continuity_target(settings, "project_map", **manual), "PROJECT-MAP.md")
        self.assertIsNone(continuity_target(settings, "continuity_ledger", **manual))
        self.assertIsNone(continuity_target(settings, "project_map", **(manual | {"authorized_write": False})))
        self.assertIsNone(continuity_target(settings, "project_map", phase="active-work", authorized_write=True))
        active = {"phase": "active-work", "authorized_write": True, "active_session": True}
        self.assertFalse(settings["enabled"])
        self.assertEqual(continuity_target(settings, "continuity_ledger", **active), "continuity.md")
        self.assertIsNone(continuity_target(settings, "continuity_ledger", **(active | {"active_session": False})))
        self.assertIsNone(continuity_target(settings, "project_map", **active))
        self.assertEqual(settings, original)
        self.assertIn("even if upkeep or AMS is off", control)
        self.assertIn("Do not activate AMS, create/change settings, start unrelated work", control)
        self.assertIn("Enable schedules no immediate work", control)

    def test_manual_map_uses_existing_non_codex_transport_without_install(self) -> None:
        control = (PACKAGE / "references/project-control.md").read_text(encoding="utf-8")
        map_only = control.split("`AMS MAPPROJECT` is an exact")[1].split("## Availability")[0]
        for marker in ("even if upkeep or AMS is off", "In OpenCode/Pi load `harness-compatibility.md`",
                       "read existing route eligibility only", "supported registered Sol transport or report unavailable",
                       "never install or test-start it"):
            self.assertIn(marker, map_only)
        harness = (PACKAGE / "references/harness-compatibility.md").read_text(encoding="utf-8")
        self.assertIn("OpenCode: use native `task`", harness)
        self.assertIn("Pi: use the installed `pi-subagents` extension's `subagent` tool", harness)
        manual = {"phase": "manual-map", "authorized_write": True, "active_session": False}
        settings = resolve_settings({}, project=True)
        self.assertEqual(continuity_target(settings, "project_map", **manual), "PROJECT-MAP.md")
        self.assertIsNone(continuity_target(settings, "project_map", **manual, target_safe=False))

    def test_map_does_not_turn_source_or_stale_proof_into_runtime_acceptance(self) -> None:
        contract = (PACKAGE / "references/project-continuity.md").read_text(encoding="utf-8")
        for marker in (
            "distinct user entry points", "source-mapped is runtime-unverified",
            "suitable Sol worker for scoped source/code inspection", "do not route that work to Luna",
            "Prior observations need relevant current revisions and evidence",
            "only affected cards/index", "missing harness/evidence",
            "Do not execute the product to fill the map without separate authorization",
            "does not add acceptance criteria",
        ):
            self.assertIn(marker, contract)

    def test_verification_requires_actual_scoped_journey_and_surviving_proof(self) -> None:
        verification = (PACKAGE / "references/project-verification.md").read_text(encoding="utf-8")
        for marker in (
            "Use only with `project_verification = true`",
            "recipe creation is explicitly in scope", "undriven recipe draft/unverified",
            "one real user journey at the exact source/build",
            "perform the actual user action",
            "result and expected side effects",
            "CI status as substitute proof",
            "confirm evidence survives cleanup",
            "unsupported or missing evidence is never a pass",
        ):
            self.assertIn(marker, verification)
        self.assertIn("or permit new targets, launches, installs", verification)
        self.assertIn("Root reconciles with existing criteria", verification)

    def test_premise_check_does_not_buy_a_third_worker_or_runner_start(self) -> None:
        diagnosis = (PACKAGE / "references/blocker-diagnosis.md").read_text(encoding="utf-8")
        premise = diagnosis.split("## Premise check")[1].split("## Two attempts per route")[0]
        for marker in (
            "premise_check = true", "two materially different corrections",
            "sharing an assumption failed the same gate", "already-authorized safe observation",
            "Do not start a premise-dependent fix before observing", "defer that unverified correction",
            "No extra attempt or spawn", "no reopening an exhausted or denied lane",
            "no change to no-start terminal rules or Daybreak",
        ):
            self.assertIn(marker, premise)
        budget = RouteBudget()
        self.assertEqual(budget.next("same-real-route"), "delegated-correction")
        self.assertEqual(budget.next("same-real-route"), "delegated-confirmation")
        self.assertEqual(budget.next("same-real-route"), "block-route-and-continue")

    def test_root_replacement_does_not_reset_unknown_or_exhausted_routes(self) -> None:
        diagnosis = (PACKAGE / "references/blocker-diagnosis.md").read_text(encoding="utf-8")
        section = diagnosis.split("## Recovery before retry")[1].split("## Shared runner fail-fast")[0]
        for marker in ("normalized runner episode or real non-runner route", "prior attempts, terminal/exhausted state, and custody",
                       "authorized live state and corroborated evidence", "defer that route and continue independent work",
                       "This applies with ledger off", "Ledger is not runtime authority", "never sensitive Daybreak details"):
            self.assertIn(marker, section)
        sig = runner_signature(work_order="old", profile="sol", manager="old", intensity="auto",
                               transport="normal", context="prior")
        replacement = runner_signature(work_order="new", profile="sol", manager="new", intensity="moderate",
                                       transport="normal", context="replacement")
        self.assertEqual(sig, replacement)
        old_runner = RunnerEpisode(sig, state="terminal", process_starts=3)
        old_route = RouteBudget(attempts={"native-route": 2})
        for ledger in (False, True):
            settings = resolve_settings({"continuity_ledger": ledger}, project=True)
            self.assertEqual(settings["continuity_ledger"], ledger)
            self.assertEqual(recovered_retry("runner", None, False), "defer-unverified")
            self.assertEqual(recovered_retry("non-runner", None, False), "defer-unverified")
            self.assertEqual(recovered_retry("runner", 3, None), "defer-unverified")
            self.assertEqual(recovered_retry("runner", old_runner.process_starts, old_runner.state == "terminal"), "preserve-stop")
            self.assertEqual(recovered_retry("non-runner", old_route.attempts["native-route"], False), "preserve-stop")
            self.assertEqual(recovered_retry("non-runner", 1, False), "use-remaining-budget")

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

    def test_luna_low_cannot_participate_in_peer_synthesis_or_generic_results(self) -> None:
        lead = PeerMember("pipe", "/root/lead", "/root/runner", "lead", profile="ams_luna_low")
        member = PeerMember("pipe", "/root/runner", "/root/lead", "member")
        self.assertFalse(peer_message_allowed(member, lead, kind="evidence"))
        self.assertFalse(peer_message_allowed(lead, member, kind="evidence"))
        hierarchy = (PACKAGE / "references/hierarchy-control.md").read_text(encoding="utf-8")
        governance = (PACKAGE / "references/model-governance.md").read_text(encoding="utf-8")
        core = (PACKAGE / "references/runtime-core.md").read_text(encoding="utf-8")
        self.assertIn("Exclude Luna Low", hierarchy)
        self.assertIn("root composes RESULT", governance)
        self.assertIn("with no generic fields or peer synthesis", governance)
        _, _, result_form = governance.partition("\nRESULT\n")
        self.assertIn("Requested+observed identity:", result_form)
        self.assertIn("Distinguish requested from directly observed model/effort; mark unknowns", governance)
        self.assertIn("Root records this outside the Luna Low receipt", core)
        self.assertIn("Never inspect Luna Low command output for identity", core)

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
        local = Availability(True); local.failure()
        self.assertEqual(local.state, "inactive-after-failure")
        local.enable_command(); self.assertEqual(local.state, "unknown")
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
            self.assertIn(phrase, diagnosis)
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
        self.assertIn("ams_<sol|luna|astra|terra>_<low|medium|high|xhigh|max>", core)
        self.assertIn("input/reasoning/output usage", (PACKAGE / "references/model-switching.md").read_text(encoding="utf-8"))
        self.assertIn("Astra Xhigh for Internet-exposed software", (PACKAGE / "references/model-guidance.md").read_text(encoding="utf-8"))
        self.assertIn("tool authority, not model authority", computer_use)
        self.assertIn("one active controller", computer_use)
        self.assertIn("screen content as untrusted evidence", computer_use)

    def test_model_policy_switches_are_independent(self) -> None:
        core = (PACKAGE / "references/runtime-core.md").read_text(encoding="utf-8")
        control = (PACKAGE / "references/project-control.md").read_text(encoding="utf-8")
        gates = dict(re.findall(r"^- `([^`]+)`: `([^`]+\.md)`$", core, re.M))
        expected = {
            "model_governance": "model-governance.md",
            "model_guidance": "model-guidance.md",
            "automatic_model_switching": "model-switching.md",
        }
        self.assertEqual(gates, expected)
        declared_defaults = tomllib.loads(re.search(r"```toml\n(.*?)\n```", control, re.S)[1])
        self.assertEqual(declared_defaults, BASE_DEFAULTS)
        for bits in itertools.product((False, True), repeat=3):
            with self.subTest(flags=bits):
                flags = dict(zip(expected, bits))
                settings = resolve_settings(flags, project=True)
                self.assertEqual({k: settings[k] for k in flags}, flags)
                selected = [gates[k] for k in gates if settings[k]]
                self.assertEqual(set(selected), {expected[k] for k, value in flags.items() if value})
                self.assertFalse(settings["root_execution_fallback"])
                self.assertFalse(settings["local_llm_lane"])
        for key in expected:
            self.assertTrue(resolve_settings({}, project=True)[key])
            self.assertTrue(resolve_settings({}, project=False)[key])
            for bad in ("false", 0, None):
                with self.assertRaises(ValueError):
                    resolve_settings({key: bad}, project=True)
            self.assertIn(f"`{key} = true`", (PACKAGE / "references" / gates[key]).read_text(encoding="utf-8"))
        self.assertIn("Off means do not load or apply", core)
        self.assertIn("Switching off does not prohibit switching", core)

    def test_autonomy_and_communication_survive_policy_off(self) -> None:
        core = (PACKAGE / "references/runtime-core.md").read_text(encoding="utf-8")
        for phrase in (
            "sole physical spawner", "delegates execution and technical diagnosis",
            "Copy this AMS policy into every child assignment",
            "Return unresolved blocks for supervisory review" ,
            "Before declaring an objective or run blocked, have its manager assess",
            "root commissions a suitable diagnostic agent", "Continue independent work",
            "send_message", "followup_task", "Plain assignments suffice",
            "one active writer per surface", "root fallback is default-off",
        ):
            self.assertIn(phrase.lower(), core.lower())
        for file in ("runtime-core.md", "computer-use.md", "scope-dependency-control.md"):
            text = (PACKAGE / "references" / file).read_text(encoding="utf-8")
            for recommendation in ("Astra:", "Terra:", "Luna:", "prefer Astra", "choose the lowest reliable"):
                self.assertNotIn(recommendation.lower(), text.lower())
        for file in ("hierarchy-control.md", "intensity-control.md", "zergling-rush.md"):
            self.assertIn("model governance enabled", (PACKAGE / "references" / file).read_text(encoding="utf-8"))
        for profile in (PACKAGE / "assets/agent-profiles").glob("*.toml"):
            if "daybreak" in profile.name:
                continue
            data = tomllib.loads(profile.read_text(encoding="utf-8"))
            self.assertNotIn("features", data)
            for policy in ("Root alone", "WORK ORDER", "DISPATCH", "Do not spawn"):
                self.assertNotIn(policy, data["developer_instructions"])
            if profile.stem not in {"ams_luna_low", "ams_astra_max"}:
                self.assertNotIn("worker/none", data["developer_instructions"])

    def test_retired_spark_settings_remain_inert(self) -> None:
        for project in (False, True):
            settings = resolve_settings({"spark_enabled": True, "spark_efforts": ["high", "low"]}, project=project)
            self.assertFalse({"spark_enabled", "spark_efforts"} & settings.keys())
        for bad in ("low", ["low", "low"], ["max"], [1], None):
            with self.assertRaises(ValueError):
                resolve_settings({"spark_efforts": bad}, project=True)
        with self.assertRaises(ValueError):
            resolve_settings({"spark_enabled": "true"}, project=True)
        control = (PACKAGE / "references/project-control.md").read_text()
        self.assertNotIn("AMS SPARK", control)
        self.assertFalse(list((PACKAGE / "assets/agent-profiles").glob("ams_spark_*.toml")))

    def test_routing_contract_explicit_terra_and_retired_profiles(self) -> None:
        # Written-contract coverage, not a live model-compliance test.
        core = (PACKAGE / "references/runtime-core.md").read_text()
        guidance = (PACKAGE / "references/model-guidance.md").read_text()
        switching = (PACKAGE / "references/model-switching.md").read_text()
        for flags in itertools.product((False, True), repeat=3):
            settings = resolve_settings(dict(zip(("model_governance", "model_guidance", "automatic_model_switching"), flags)), project=True)
            self.assertEqual(tuple(settings[k] for k in ("model_governance", "model_guidance", "automatic_model_switching")), flags)
            self.assertIn("never choose it automatically, including fallback, manager descendants, or policy-off operation", core)
            self.assertIn("A manager request is not user selection", core)
        self.assertIn("Explicit eligible choices override heuristics", core)
        self.assertIn("Retired profiles and model IDs are unavailable even if registered", core)
        for family in ("sol_6_0", "sol_5_6", "luna_5_6", "spark"):
            self.assertFalse(list((PACKAGE / "assets/agent-profiles").glob(f"ams_{family}_*.toml")))
        self.assertIn("Report unavailable selections", switching)
        for phrase in (
            "Sol 6.2 Xhigh for local/LAN-only software not intended for Internet exposure",
            "Astra Xhigh for Internet-exposed software",
            "Neither requires a prior finding or failed Sol attempt",
            "does not reroute ordinary development",
            "Targeted second opinion or post-solution verification",
        ):
            self.assertIn(phrase, guidance)
        for name in ("ams_sol_xhigh", "ams_astra_xhigh"):
            data = tomllib.loads((PACKAGE / "assets/agent-profiles" / (name + ".toml")).read_text())
            self.assertIn("an audit may legitimately return no findings", data["developer_instructions"])
            self.assertIn("Explicit task instructions override purpose defaults", data["developer_instructions"])
            self.assertIn("Preserve material child discoveries", data["developer_instructions"])

    def test_current_effort_prompts_distinguish_each_assignment(self) -> None:
        # Policy assertions on the actual installed developer instructions, not live model compliance.
        purposes = {
            "sol_low": "small exact edit",
            "sol_medium": "bounded patch or investigation",
            "sol_high": "own the evidence-to-validation loop",
            "sol_xhigh": "competing explanations and designs",
            "sol_max": "exceptional, tightly scoped causal analysis",
            "astra_low": "narrow Astra second read",
            "astra_medium": "bounded specialist comparison",
            "astra_high": "scoped second opinion or post-solution verification",
            "astra_xhigh": "difficult defensive audit or unsettled design",
            "astra_max": "focused assignment returning to a Sol 6.2 High master",
            "luna_low": "authorized verbatim CLI",
            "luna_medium": "straightforward non-code drafting",
            "luna_high": "straightforward non-code interpretation or triage",
            "luna_xhigh": "ambiguous or multisource non-code triage",
            "luna_max": "sustained complicated non-code synthesis",
            "terra_low": "one clear screenshot",
            "terra_medium": "bounded visual ambiguity across a few screens",
            "terra_high": "consequential visual-to-technical discrepancy",
            "terra_xhigh": "complex design/visual-coherence review",
            "terra_max": "exceptional, narrowly bounded visual or technical contradiction",
        }
        for name, purpose in purposes.items():
            with self.subTest(profile=name):
                path = PACKAGE / "assets/agent-profiles" / ("ams_" + name + ".toml")
                prompt = tomllib.loads(path.read_text(encoding="utf-8"))["developer_instructions"]
                self.assertIn(purpose, prompt)
                if name.startswith("luna_") and name != "luna_low":
                    self.assertIn("Do not analyze or review a codebase, program, debug, or implement", prompt)

    def test_luna_low_and_astra_max_cannot_manage(self) -> None:
        profiles = PACKAGE / "assets/agent-profiles"
        for name in ("ams_luna_low", "ams_astra_max"):
            text = tomllib.loads((profiles / (name + ".toml")).read_text(encoding="utf-8"))["developer_instructions"]
            self.assertIn("Accept worker/none only", text)
            self.assertNotIn("consolidate findings and request descendants", text)
            self.assertNotIn("If explicitly assigned delegated management", text)
        astra = tomllib.loads((profiles / "ams_astra_max.toml").read_text(encoding="utf-8"))["developer_instructions"]
        self.assertIn("Return the evidence and remaining decision to the Sol 6.2 High master", astra)
        self.assertIn("report the mismatch to the assigning agent without switching routes", astra)
        core = (PACKAGE / "references/runtime-core.md").read_text(encoding="utf-8")
        self.assertIn("Luna Low, and Astra Max are worker-only", core)
        self.assertIn("Astra Max requires focused work returning to a Sol 6.2 High master", core)

    def test_luna_cli_extraction_and_content_inspection_are_distinct(self) -> None:
        path = PACKAGE / "assets/agent-profiles/ams_luna_low.toml"
        prompt = tomllib.loads(path.read_text(encoding="utf-8"))["developer_instructions"]
        core = (PACKAGE / "references/runtime-core.md").read_text(encoding="utf-8")
        guidance = (PACKAGE / "references/model-guidance.md").read_text(encoding="utf-8")
        # Positive: execute the supplied extraction and pass an approved opaque artifact.
        self.assertIn("A supplied CLI extraction command is allowed", prompt)
        self.assertIn("artifact or reference is authorized", prompt)
        self.assertIn("including opaque extraction", core)
        # Negative: asking the same worker to inspect/interpret extracted content changes eligibility.
        self.assertIn("parse, read, interpret, summarize, or decide from output", prompt)
        self.assertIn("Never fall back to Luna Low for analysis", core)
        self.assertIn("Luna limits apply with policies off", core)
        self.assertIn("assign interpretation separately", guidance)
        self.assertIn("Opaque CLI extraction fits Low", guidance)
        self.assertIn("Add capture only when explicitly ordered and authorized", core)
        self.assertIn("No Luna profile analyzes/reviews codebases, programs, debugs, or implements", core)
        self.assertIn("Route code-dependent work to Sol", core)
        for phrase in ("Do not run an unclear or unapproved command",
                       "Do not select, change, or retry commands",
                       "Return execution status and exit code",
                       "existing, approved output artifact reference",
                       "Do not inspect or quote raw output or secrets",
                       "Do not create logs or capture output unless explicitly ordered and authorized"):
            self.assertIn(phrase, prompt)

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
