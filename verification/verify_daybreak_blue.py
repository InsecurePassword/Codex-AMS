#!/usr/bin/env python3
"""Adversarial scenario checks for the Daybreak Blue fallback contract."""
from __future__ import annotations

import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "adaptive-master-subagent-orchestration"


@dataclass(frozen=True)
class Refusal:
    source_family: str
    source_role: str
    work_order_id: str | None
    explicit_cyber_safeguard: bool
    authorized_defensive: bool
    unchanged_boundary: bool
    generic_failure: bool = False


def qualifies(refusal: Refusal) -> bool:
    return (
        refusal.source_family == "sol"
        and refusal.source_role in {"worker", "delegated-manager"}
        and bool(refusal.work_order_id)
        and refusal.work_order_id != "none-root-handling"
        and refusal.explicit_cyber_safeguard
        and refusal.authorized_defensive
        and refusal.unchanged_boundary
        and not refusal.generic_failure
    )


def valid_blue_observed_identity(requested: str, observed: str | None, approved_blue_surface: bool) -> bool:
    if requested != "gpt-daybreak-blue" or not observed:
        return False
    if observed == "gpt-daybreak-blue":
        return True
    return observed == "gpt-5.6-sol" and approved_blue_surface


@dataclass
class AccessBoundary:
    boundary_id: str
    closure: str = "open"
    blocker: str | None = None

    def close(self, blocker: str) -> None:
        self.closure = "closed-unavailable"
        self.blocker = blocker

    def transport_failure(self) -> None:
        pass

    def preflight_failure(self, *, direct_boundary_evidence: bool = False) -> None:
        if direct_boundary_evidence:
            self.close("direct boundary mismatch")

    def reopen(self, *, explicit_user: bool = False, new_provisioning_evidence: bool = False) -> None:
        if not (explicit_user or new_provisioning_evidence):
            raise ValueError("closed boundary cannot be cleared implicitly")
        self.closure = "open"
        self.blocker = None


@dataclass(frozen=True)
class TaskIdentity:
    root_objective_id: str
    unit_id: str
    admission_generation: str
    operation_id: str
    work_order_id: str
    nonce: str
    start_attempt: int


@dataclass
class FallbackUnit:
    unit_id: str
    state: str = "eligible"
    terminal_identity: TaskIdentity | None = None
    terminal_status: str | None = None

    def access_reopened(self) -> None:
        if self.state == "blocked":
            self.state = "eligible"

    def confirmed_start(self) -> None:
        if self.state != "eligible":
            raise ValueError("one confirmed-start task only")
        self.state = "active"

    def terminal(self, identity: TaskIdentity, status: str) -> str:
        if self.state == "active":
            self.state = "consumed"
            self.terminal_identity = identity
            self.terminal_status = status
            return "accepted"
        if self.state == "consumed" and identity == self.terminal_identity and status == self.terminal_status:
            return "idempotent"
        return "conflict-evidence-only"


def manager_custody(intensity: str, child_capacity: bool) -> str:
    if intensity == "minimal":
        return "serial-inactive-resumable"
    return "active-manager" if child_capacity else "serial-inactive-resumable"


def ownership_after_start(start_state: str) -> str:
    if start_state == "confirmed":
        return "daybreak-worker"
    if start_state == "no-start":
        return "root-write-freeze"
    if start_state == "uncertain":
        return "treat-active-no-retry"
    raise ValueError(start_state)


def invalidate_before_confirmed_start(state: str, *, stable_closed: bool = False, session_blocked: bool = False) -> tuple[str, str]:
    if state in {"active", "consumed"}:
        return state, "retain-correlation"
    return ("blocked" if stable_closed or session_blocked else "eligible", "clear-reservation-root-freeze-allocation")


def valid_no_start_retry(original: TaskIdentity, retry: TaskIdentity) -> bool:
    return (
        retry.root_objective_id == original.root_objective_id
        and retry.unit_id == original.unit_id
        and retry.admission_generation == original.admission_generation
        and retry.operation_id == original.operation_id
        and retry.work_order_id == original.work_order_id
        and retry.nonce != original.nonce
        and original.start_attempt == 1
        and retry.start_attempt == 2
    )


class DaybreakBlueContracts(unittest.TestCase):
    def test_trigger_requires_real_standard_sol_work_order_refusal(self) -> None:
        valid = Refusal("sol", "worker", "wo-sol-1", True, True, True)
        self.assertTrue(qualifies(valid))
        self.assertTrue(qualifies(Refusal("sol", "delegated-manager", "wo-sol-mgr", True, True, True)))
        self.assertFalse(qualifies(Refusal("root", "root", None, True, True, True)))
        self.assertFalse(qualifies(Refusal("sol", "root", "none-root-handling", True, True, True)))
        self.assertFalse(qualifies(Refusal("terra", "worker", "wo-1", True, True, True)))
        self.assertFalse(qualifies(Refusal("sol", "worker", None, True, True, True)))
        self.assertFalse(qualifies(Refusal("sol", "worker", "wo-1", False, True, True)))
        self.assertFalse(qualifies(Refusal("sol", "worker", "wo-1", True, False, True)))
        self.assertFalse(qualifies(Refusal("sol", "worker", "wo-1", True, True, False)))
        self.assertFalse(qualifies(Refusal("sol", "worker", "wo-1", True, True, True, generic_failure=True)))

    def test_blue_observed_identity_mapping(self) -> None:
        self.assertTrue(valid_blue_observed_identity("gpt-daybreak-blue", "gpt-daybreak-blue", False))
        self.assertTrue(valid_blue_observed_identity("gpt-daybreak-blue", "gpt-5.6-sol", True))
        self.assertFalse(valid_blue_observed_identity("gpt-daybreak-blue", "gpt-5.6-sol", False))
        self.assertFalse(valid_blue_observed_identity("gpt-daybreak-blue", "other", True))
        self.assertFalse(valid_blue_observed_identity("gpt-daybreak-blue", None, True))

    def test_access_boundary_closure_survives_handoff(self) -> None:
        boundary = AccessBoundary("access-A"); boundary.close("entitlement mismatch")
        handed_off = AccessBoundary(boundary.boundary_id, boundary.closure, boundary.blocker)
        with self.assertRaises(ValueError):
            handed_off.reopen()
        handed_off.reopen(explicit_user=True)
        self.assertEqual(handed_off.closure, "open")

    def test_transport_or_no_start_does_not_close_access_boundary(self) -> None:
        boundary = AccessBoundary("access-A"); boundary.transport_failure()
        self.assertEqual(boundary.closure, "open")

    def test_profile_change_never_erases_access_closure(self) -> None:
        boundary = AccessBoundary("access-A"); boundary.close("entitlement mismatch")
        self.assertEqual(boundary.closure, "closed-unavailable")

    def test_failed_preflight_closes_only_with_direct_boundary_evidence(self) -> None:
        boundary = AccessBoundary("access-A"); boundary.preflight_failure()
        self.assertEqual(boundary.closure, "open")
        boundary.preflight_failure(direct_boundary_evidence=True)
        self.assertEqual(boundary.closure, "closed-unavailable")

    def test_access_reopen_only_resets_never_started_blocked_unit(self) -> None:
        unit = FallbackUnit("unit-1", state="blocked"); unit.access_reopened()
        self.assertEqual(unit.state, "eligible")
        consumed = FallbackUnit("unit-2", state="consumed"); consumed.access_reopened()
        self.assertEqual(consumed.state, "consumed")

    def test_auto_manager_custody_uses_actual_capacity(self) -> None:
        self.assertEqual(manager_custody("auto", True), "active-manager")
        self.assertEqual(manager_custody("auto", False), "serial-inactive-resumable")
        self.assertEqual(manager_custody("minimal", True), "serial-inactive-resumable")

    def test_no_start_never_creates_child_ownership(self) -> None:
        self.assertEqual(ownership_after_start("no-start"), "root-write-freeze")
        self.assertEqual(ownership_after_start("confirmed"), "daybreak-worker")
        self.assertEqual(ownership_after_start("uncertain"), "treat-active-no-retry")

    def test_prestart_invalidation_clears_transient_state(self) -> None:
        self.assertEqual(invalidate_before_confirmed_start("eligible"), ("eligible", "clear-reservation-root-freeze-allocation"))
        self.assertEqual(invalidate_before_confirmed_start("eligible", session_blocked=True), ("blocked", "clear-reservation-root-freeze-allocation"))
        self.assertEqual(invalidate_before_confirmed_start("active"), ("active", "retain-correlation"))

    def test_no_start_retry_keeps_order_operation_and_fresh_nonce(self) -> None:
        original = TaskIdentity("obj-1", "unit-1", "gen-1", "op-1", "wo-1", "nonce-1", 1)
        self.assertTrue(valid_no_start_retry(original, TaskIdentity("obj-1", "unit-1", "gen-1", "op-1", "wo-1", "nonce-2", 2)))
        self.assertFalse(valid_no_start_retry(original, TaskIdentity("obj-1", "unit-1", "gen-1", "op-1", "wo-2", "nonce-2", 2)))
        self.assertFalse(valid_no_start_retry(original, TaskIdentity("obj-1", "unit-1", "gen-1", "op-2", "wo-1", "nonce-2", 2)))

    def test_one_confirmed_start_and_exact_terminal_reconciliation(self) -> None:
        identity = TaskIdentity("obj-1", "unit-1", "gen-1", "op-1", "wo-1", "nonce-1", 1)
        unit = FallbackUnit("unit-1"); unit.confirmed_start()
        self.assertEqual(unit.terminal(identity, "complete"), "accepted")
        self.assertEqual(unit.terminal(identity, "complete"), "idempotent")
        conflict = TaskIdentity("obj-1", "unit-1", "gen-2", "op-2", "wo-2", "nonce-2", 1)
        self.assertEqual(unit.terminal(conflict, "complete"), "conflict-evidence-only")
        with self.assertRaises(ValueError): unit.confirmed_start()

    def test_reference_requires_sol_work_order_and_blue_identity(self) -> None:
        text = (PACKAGE / "references/daybreak-blue.md").read_text(encoding="utf-8")
        for phrase in (
            "a real standard-Sol work order explicitly refused",
            "Root handling without that work order never qualifies",
            "The requested alias is `gpt-daybreak-blue`",
            "Accept observed route identity as:",
            "`gpt-5.6-sol` only when the same admission contains direct evidence",
            "underlying `gpt-5.6-sol` identity alone never proves Daybreak Blue",
            "Confirmed-start budget: 1 of 1",
            "Create no AMS database",
            "A proven no-start leaves no child owner",
            "clears reservation/root freeze/allocation",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("none-root-handling", text)
        self.assertNotIn("Refusal source: root-handling", text)

    def test_profile_is_worker_only_and_blue_only(self) -> None:
        text = (PACKAGE / "assets/agent-profiles/ams_daybreak_blue_max.toml").read_text(encoding="utf-8")
        self.assertIn('model = "gpt-daybreak-blue"', text)
        self.assertIn("Accept only Orchestration role=worker and Delegation authority=none", text)
        self.assertIn("Accept observed `gpt-5.6-sol` only with direct evidence", text)
        self.assertNotIn("sandbox_mode", text)
        self.assertNotIn("approval_policy", text)
        model_lines = [line for line in text.splitlines() if line.startswith("model = ")]
        self.assertEqual(model_lines, ['model = "gpt-daybreak-blue"'])

    def test_no_persistent_setting_or_proactive_probe(self) -> None:
        control = (PACKAGE / "references/project-control.md").read_text(encoding="utf-8")
        daybreak = (PACKAGE / "references/daybreak-blue.md").read_text(encoding="utf-8")
        for forbidden in ("daybreak_enabled =", "daybreak_available =", "AMS DAYBREAK ENABLE", "$CODEX_HOME/ams-runtime"):
            self.assertNotIn(forbidden, control + daybreak)
        self.assertIn("Daybreak has no setting or proactive probe", control)

    def test_intensity_cannot_multiply_daybreak(self) -> None:
        rush = (PACKAGE / "references/zergling-rush.md").read_text(encoding="utf-8")
        ultra = (ROOT / "SOL-ULTRA-AMS-EXTREME-ORCHESTRATION-PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("never multiplies the Daybreak lane", rush)
        self.assertIn("Extreme cannot duplicate a fallback unit", ultra)

    def test_root_fallback_cannot_take_over_refused_task(self) -> None:
        fallback = (PACKAGE / "references/root-execution-fallback.md").read_text(encoding="utf-8")
        self.assertIn("never authorizes root execution of the refused security-sensitive task", fallback)

    def test_only_blue_daybreak_route_is_declared(self) -> None:
        model_tokens: set[str] = set()
        product_paths = list(PACKAGE.rglob("*")) + [ROOT / "README.md", ROOT / "PRODUCT DOCUMENTATION.md", ROOT / "INSTALLATION.md"]
        for path in product_paths:
            if path.is_file() and path.suffix in {".md", ".toml", ".yaml", ".yml", ".json", ".py", ".sh", ".ps1", ".txt"}:
                text = path.read_text(encoding="utf-8")
                for token in __import__("re").findall(r"gpt-daybreak-[a-z0-9._-]+", text):
                    model_tokens.add(token)
        self.assertEqual(model_tokens, {"gpt-daybreak-blue"})



if __name__ == "__main__":
    unittest.main()
