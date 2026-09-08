#!/usr/bin/env python3
"""Verify the release-agnostic lean AMS repository and installed-core contract."""
from __future__ import annotations

import hashlib
import json
import re
import tomllib
from urllib.parse import unquote
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "adaptive-master-subagent-orchestration"
MANIFEST = ROOT / "install-manifest.txt"
BASELINE = ROOT / "verification/fixtures/baseline-install-manifest-working-current.txt"

PROFILE_EFFORTS = {
    "sol": ("low", "medium", "high", "xhigh", "max"),
    "terra": ("low", "medium", "high", "xhigh", "max"),
    "luna": ("low", "medium", "high", "xhigh", "max"),
    "astra": ("low", "medium", "high", "xhigh", "max"),
    "spark": ("low", "medium", "high"),
}
MODELS = {
    "sol": "gpt-5.6-sol",
    "terra": "gpt-5.6-terra",
    "luna": "gpt-5.6-luna",
    "astra": "gpt-6-astra",
    "spark": "gpt-5.3-codex-spark",
}
CORE_REFERENCES = {
    "blocker-diagnosis.md",
    "configuration-maintenance.md",
    "computer-use.md",
    "daybreak-blue.md",
    "harness-compatibility.md",
    "hierarchy-control.md",
    "intensity-control.md",
    "model-governance.md",
    "model-guidance.md",
    "model-switching.md",
    "package-maintenance.md",
    "profile-management.md",
    "project-control.md",
    "project-governance.md",
    "root-execution-fallback.md",
    "runtime-core.md",
    "scope-dependency-control.md",
    "zergling-rush.md",
}
REMOVED_REFERENCES = {
    "convergence-control.md",
    "evidence-handling.md",
    "feature-control.md",
    "handoff-control.md",
    "request-accounting.md",
    "review-control.md",
    "runtime-observation.md",
    "shared-worktree-control.md",
    "surface-identity.md",
    "task-graph-safeguards.md",
    "work-order-refinement.md",
}
RETIRED_FIELDS = {
    "schema_version",
    "convergence_control",
    "convergence_correction_limit",
    "convergence_redesign_limit",
    "spark_available",
    "work_order_refinement",
    "review_control",
    "shared_worktree_verification",
    "runtime_observation",
    "untrusted_evidence_handling",
    "task_graph_safeguards",
    "rejected_approach_handoff",
    "request_accounting",
    "app_task_lane",
}


PEER_CANDIDATE_PROFILE_HASHES = {
    "ams_luna_high.toml": "22cd43c99ba332d8e5902f1ee96a9f8c481a21bd9c3b108f2ee6ecdaaf50f986",
    "ams_luna_low.toml": "869cce6526326fe89cc9f698890ce50f99f6f2e7bec7b06460e55fe1ab8cfac1",
    "ams_luna_max.toml": "16a6e2472f3117e145b300cc2ee1ac30734f079240cc19a2f6d936e577cb4133",
    "ams_luna_medium.toml": "43222d1cd3b9a5991e7d02cf9648bc67d879b6fd8d96271f0ec01ddc025df290",
    "ams_luna_xhigh.toml": "5ad2eb60b6e8bec121bec6365c890cf0c7dfe357686061ebd8e490fda3a1466d",
    "ams_sol_high.toml": "00050f8f207231976c73d2f433d502bbd1d39493373a829bb6428f67d802ab3f",
    "ams_sol_low.toml": "0f45cc7f558a11d1b3bf87c5f2e845cb7e9e45f5cc6cc447b9e39f49d512a24d",
    "ams_sol_max.toml": "6a75ed8581a148d275c18e832e5c78d6b44c0ee12bbeb466b8aa229d356ea4f1",
    "ams_sol_medium.toml": "5c5032948c980f8735426d296d757d841d5be35dc513e6c0cadb2764adfa8180",
    "ams_sol_xhigh.toml": "875810a10c1ae9da5dd53ae1d667c4d2d4e98426b651cb6ebf21bae890489e86",
    "ams_spark_high.toml": "048808da9efabbc56766c5ade32384f40b9bf70cdca552951107543d2c8b8cf9",
    "ams_spark_low.toml": "e665b2dd2c0fb25321af2a87eb8aee7b3ef91366bf679f8bc57f74afa6be8635",
    "ams_spark_medium.toml": "6423fdc127044a8ac3963cf54ca385231aac9e322ed9eb422953b2a4d751c154",
    "ams_terra_high.toml": "8aea92a175187689b1fb16fba76a42b23bc1e3f60349bf642c629a2f3f76014d",
    "ams_terra_low.toml": "11980063c0bd805b5b89e119d2d108985b617d3251cc87ecadc28c65097d5190",
    "ams_terra_max.toml": "ab51eab6288db70ae5fa5a725eb92828b98cf95a9ccb8c595d5519e28734af75",
    "ams_terra_medium.toml": "461a0c2250f2ae535fda672fef5e5918742f3a49ea3677150f4711a059cbba33",
    "ams_terra_xhigh.toml": "2c8159222aaeef4d739b74f622b494eb77051c0b15584ad9e48f1f5a39dcdd7a",
}


LEAN_CANDIDATE_PROFILE_HASHES = {
    "ams_luna_high.toml": "f7a8bd41fb963aa79319bbe4ad9531204568d6a212013f1116029ddca9d805d6",
    "ams_luna_low.toml": "fb47eec631a3eb6ade50951939dcce9cefe894607d27654eb67a476a1f3918f8",
    "ams_luna_max.toml": "3b1fcb9e66d1a402212e3a8387bc63c557f8a7ed048a315bd53e1b91d487e441",
    "ams_luna_medium.toml": "5cf1e7778d634bc3521e952a8d3dbb0c78dadd7c0a4fb5c4e5d1e3b147154f00",
    "ams_luna_xhigh.toml": "799766e76b4c9f384ca451b0139bd2147b2dd654ac82ad11e71ce02c09a679bb",
    "ams_sol_high.toml": "8ad9d1e8d4794eb2d1c53ee52d5d08633f874d3d5bd6ab470b4be7a958c3435a",
    "ams_sol_low.toml": "dfc27a14798dee38474a5940c523a59b91d7ce9358a83d9f135ef97ace2bd84e",
    "ams_sol_max.toml": "25146436a686e49130355359ee177b1f9a562c1814570f1c93500a8ab83877a4",
    "ams_sol_medium.toml": "fe8d6a89ed465f091ace53adfaefa4b654f5db66175aa6d90b32e6853a29e4b3",
    "ams_sol_xhigh.toml": "d0c34e563b7fc9d4203ba939cba7e984cffd322ee896d912052108044e5a8212",
    "ams_spark_high.toml": "6fdc11666d81261b3b8c06ad6df4deb61d8f208754d437a8d8185d7fd8504c80",
    "ams_spark_low.toml": "e37d29aa369bdf32ef5bf5bec4f5fc03b771167a8b8d15d7c7c521c159d65a1c",
    "ams_spark_medium.toml": "22d7f5f1de7baa32e5bde234b70d8bc3e9b69c40165deaee625454261c2e69a9",
    "ams_terra_high.toml": "5a0cf2b3009bb9d5afa4f56b8d4d5ec1da3fa3de13ef0209040c3f88e8bc7f7c",
    "ams_terra_low.toml": "863a494b3867da89137a5f5f5134d47872730b561319daa6d7ee69bddfb6797c",
    "ams_terra_max.toml": "f6f872f0fa8499f43f9b98512122e43acc94c9e79d1184b1c4bb87a4136fc283",
    "ams_terra_medium.toml": "ccc90cb09ba17e170355621bfb354f15f2727965acbe112d423d2865e10b79d3",
    "ams_terra_xhigh.toml": "1928dd03259ca23e4aa80bd45f32cf1361826519a4e59468c6a4713633a80395"
}

ASTRA_CANDIDATE_PROFILE_HASHES = {
    'ams_astra_high.toml': '049bdaf498f30d3d0b12d974a300b1c4b2b2a7637f15faf8828305a0a5d3089f',
    'ams_astra_low.toml': '6a84b9ea942a89c13532b3778b15e784add31ac7bd6aaadce130bdf9726bbab4',
    'ams_astra_max.toml': '1a21720488f4bc3f2fc29d605cb4463c5db43c616a159595246d005446b54ed8',
    'ams_astra_medium.toml': '9ea29f923af3a2918c7bb528b092b636cdcf53b0718afdcbd3e380d854262f35',
    'ams_astra_xhigh.toml': 'cc32498d22312873f795effe9ca488e448c109a650a5c6ed7d971e72368d3ac3',
    'ams_luna_high.toml': '99a75b8f47ece6fae8ea4e13d81441cb857e0034ab87611788b6b1a2b152b0e8',
    'ams_luna_low.toml': 'c9f4b4fc800f4f3dfe8d3205bc0c6842d17d0b49fa4fbce83a203ceac57600a9',
    'ams_luna_max.toml': '29bafcd1ce190892e187651be15eacb9f75768f7e552770ff46620107bf7bd58',
    'ams_luna_medium.toml': 'c5e3cb8af09a764f82ad8433642eba28aa2fe626feb7776710874b9f5d6d754a',
    'ams_luna_xhigh.toml': 'c2dbc5e81baad3b329038658f71dccc1c8b8946b475e62f25a57abdbe74c3e54',
    'ams_sol_high.toml': '773b05567bd7517d80bb8a7ae268be675ee1ddd931edb1689afa8ded954df9b5',
    'ams_sol_low.toml': '34b055c1fbe1580ab3f724564b65d289956d5a1ed2bd62b5aa0cf6d4d01f78f6',
    'ams_sol_max.toml': '5b42a2dae627b2466d592a05d8e16a65476aac6d60423470c901a0c3fa242477',
    'ams_sol_medium.toml': 'dd1535eb93a892870ac987ecc3c59e6325726938a3e27d3bb93cfad44a468811',
    'ams_sol_xhigh.toml': 'a399d1d02e35028298ccf5e4a138b1a1778febe3dc090aed7da7aec3d97f48e9',
    'ams_spark_high.toml': 'cf8fc04c0bf2209c4ad3290b2bf57f6e3cfe2e7f0ce51ce84b0ad14d89955b78',
    'ams_spark_low.toml': 'bd80dbf9c30cbfb7302a25194632834e7a749267b9b7d841f7a4dee28e203a8d',
    'ams_spark_medium.toml': 'd74d42e0c2befb6c843732bf3738a5b719ad3681675e787886aac1ae850ee198',
    'ams_terra_high.toml': 'b0bd03cfef9d2783661425e70c4c271d846deffa49c4b04a2b192cd346b272ed',
    'ams_terra_low.toml': 'bab5d611ab62ba30d57eb798c9629606889bd350f9b2a33c3832cc16a9c1d45e',
    'ams_terra_max.toml': 'd97fb7d3e41e68228d5799e583cab3b990df6745afa7bc249ad7ddd20b8c8fdf',
    'ams_terra_medium.toml': 'dd078cb3e3849cd3b2f5d8f9994f122fbe48f60df148cafb2d1f1540754f434a',
    'ams_terra_xhigh.toml': 'd371e764a0c22e561a6cb441b04aa1c4f521e1ae3cf6d433f4d42ad7361dd477',
}



PUBLISHED_PROFILE_HASHES = {'ams_spark_low.toml': '000d9f512aa90a52caa2d1bdaf302e1abb8a81a40e380b51fd14b993befa9043', 'ams_sol_max.toml': '405f2215ea3d52444d8cee8e32fcd96fc0c3d4adf34423a3aa5994c8d24c28d6', 'ams_sol_xhigh.toml': 'f36b2a946c56a9d51b38f7158a9ce0be5efa87da55670a2e2718ea88bf07080f', 'ams_sol_low.toml': '0dafc7dd89929f2fb736b044e3b3d9e735061adf3c1846d7db3fed77e551173a', 'ams_terra_xhigh.toml': 'c5cfbf2fe7c25b49323decf62ca3acf0949ea006f94ebb77f161d7cef9513a02', 'ams_astra_low.toml': '5a0d513c3dd22a64a9f516de2492e457fae617a65b70d2e376d97bcba775bd86', 'ams_astra_high.toml': 'd4fb1917f82cb4c428d3606fdc4ccd0a274500327ad4a34fa0bf0846fa97fb77', 'ams_luna_max.toml': '3d50cdf5952caa16c2109d3ec4237c52f11fb26ffd5914889b25eaf6b390d424', 'ams_terra_medium.toml': '9d80c212c31d9515dd94e76bb6907f1ce59f7d2689d98fdfdd346fc876d57ac5', 'ams_astra_medium.toml': '50f3156c0c916fea14b772ad447f8249126e5be88129d7fac1e4fceb6b7513a7', 'ams_luna_medium.toml': '29d95fae263c531dba5a4c5ec0ab31f92b122e427773fc0c88a4e6b0325bf161', 'ams_spark_high.toml': 'be9abba98a4d0adef6eb8a44b3cb189df52ea6d31ec964ad2eb2d85064a17f0b', 'ams_luna_low.toml': '1a8d32c5bab48bec8a8389ebf3e5fa4d341ae148ad50c5cb43daebe6c953fc56', 'ams_astra_max.toml': '171fc462327ca4eb3f4633664d9410c8f30126f216368e46d603ed62f13cdeb3', 'ams_luna_high.toml': '6400ff519bf08e609d663274a03ab63103da0e3c263a75913434a47bb84f6963', 'ams_sol_high.toml': 'b68803ff09b267ee6b859c00d1fcac5e99f7c1b05dffc85a3f3876e1978e2130', 'ams_terra_high.toml': '2ee408e2ed7a1cb736a06aa7d50d7b82508c53a8f8c8b6fd29f7093620783b46', 'ams_sol_medium.toml': '52b6648fb3d32770a2ae25048f7017ce03c0af571d05770845a48f6255e3cd2c', 'ams_luna_xhigh.toml': 'f5681143cc0831adf65747d4dcd0be7877b72c5c314c63f4ef458008cf531fe8', 'ams_astra_xhigh.toml': 'b5023cf34a8bbd815193f09a0b9726f73e5985cf2d88d247075be9f13c481a68', 'ams_terra_low.toml': '361ff9a1cdc9576d81002eac9aa5dae266cf8d8143a3b003324ef92a586a8f8c', 'ams_terra_max.toml': 'a0b7553fbe6f2c0a8e0a719bb9469a9fd9be182d1fb0625be73cc63ac27fa623', 'ams_spark_medium.toml': 'b0cf2357f80ef4e3129f231dc9fe78b528fc4cf375d3dfa08a9d8b7004b6baae'}

def fail(message: str) -> None:
    raise AssertionError(message)


def read_text(path: Path, maximum: int = 2 * 1024 * 1024) -> str:
    if not path.is_file() or path.is_symlink():
        fail(f"missing or redirected file: {path.relative_to(ROOT)}")
    data = path.read_bytes()
    if not data or len(data) > maximum:
        fail(f"unsafe size: {path.relative_to(ROOT)}")
    if data.startswith(b"\xef\xbb\xbf") or b"\x00" in data or b"\r" in data:
        fail(f"unsafe text bytes: {path.relative_to(ROOT)}")
    if not data.endswith(b"\n"):
        fail(f"missing final LF: {path.relative_to(ROOT)}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        fail(f"invalid UTF-8: {path.relative_to(ROOT)}: {error}")
    raise AssertionError("unreachable")


def parse_manifest(path: Path, *, allow_legacy_version: bool) -> dict[str, tuple[str, int]]:
    lines = read_text(path).splitlines()
    if not lines or lines[0] != "ams-install-manifest-v1":
        fail(f"invalid manifest header: {path.relative_to(ROOT)}")
    start = 1
    if len(lines) > 1 and lines[1].startswith("version\t"):
        if not allow_legacy_version:
            fail("current install manifest must not carry an AMS release version")
        start = 2
    entries: dict[str, tuple[str, int]] = {}
    for line_number, line in enumerate(lines[start:], start + 1):
        parts = line.split("\t")
        if len(parts) != 3:
            fail(f"invalid manifest line {line_number}")
        digest, length_text, repo_path = parts
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"invalid manifest digest at line {line_number}")
        if not length_text.isdecimal() or int(length_text) <= 0:
            fail(f"invalid manifest size at line {line_number}")
        if repo_path in entries or not repo_path.startswith("adaptive-master-subagent-orchestration/"):
            fail(f"invalid/duplicate manifest path: {repo_path}")
        entries[repo_path] = (digest, int(length_text))
    if not entries:
        fail("manifest contains no package files")
    return entries


def require(text: str, phrase: str, label: str) -> None:
    if phrase not in text:
        fail(f"{label} missing: {phrase!r}")


def toml_block_after(text: str, marker: str) -> dict[str, object]:
    marker_index = text.find(marker)
    if marker_index < 0:
        fail(f"missing TOML marker: {marker}")
    fence = text.find("```toml\n", marker_index)
    if fence < 0:
        fail(f"missing TOML fence after: {marker}")
    start = fence + len("```toml\n")
    end = text.find("\n```", start)
    if end < 0:
        fail(f"unterminated TOML fence after: {marker}")
    return tomllib.loads(text[start:end])


def assert_markdown_reference_integrity() -> None:
    markdown_files = sorted(ROOT.rglob("*.md"))
    for path in markdown_files:
        if "__pycache__" in path.parts:
            continue
        text = read_text(path)
        # Validate explicit repository-relative Markdown links.
        for target in re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if re.match(r"^[a-z]+://", target, re.IGNORECASE) or target.startswith("mailto:"):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"Markdown link escapes repository: {path.relative_to(ROOT)} -> {target}")
            if not resolved.exists():
                fail(f"broken Markdown link: {path.relative_to(ROOT)} -> {target}")


def assert_release_agnostic_runtime() -> None:
    forbidden_files = [
        PACKAGE / "VERSION",
        ROOT / "extensions/ams-app-task-lane/COMPATIBILITY",
        ROOT / "extensions/ams-local-openai-lane/COMPATIBILITY",
        ROOT / "extensions/ams-runtime-observation/COMPATIBILITY",
    ]
    for path in forbidden_files:
        if path.exists():
            fail(f"release/compatibility identity file remains: {path.relative_to(ROOT)}")

    release_pattern = re.compile(r"\bAMS\s+[0-9]+(?:\.[0-9]+)+\b", re.IGNORECASE)
    for root in (PACKAGE, ROOT / "extensions"):
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix == ".pyc" or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in {".md", ".yaml", ".yml", ".toml", ".py", ".ps1", ""}:
                continue
            text = read_text(path)
            if release_pattern.search(text):
                fail(f"runtime/companion identifies an AMS release: {path.relative_to(ROOT)}")


def main() -> int:
    assert_release_agnostic_runtime()

    references = {path.name for path in (PACKAGE / "references").glob("*.md")}
    if references != CORE_REFERENCES:
        fail(
            "core reference inventory mismatch: "
            f"missing={sorted(CORE_REFERENCES - references)}, extra={sorted(references - CORE_REFERENCES)}"
        )
    for name in REMOVED_REFERENCES:
        if (PACKAGE / "references" / name).exists():
            fail(f"removed stateful/modular reference remains: {name}")

    entries = parse_manifest(MANIFEST, allow_legacy_version=False)
    actual_files = sorted(
        path for path in PACKAGE.rglob("*") if path.is_file() and not path.is_symlink()
    )
    actual_paths = {path.relative_to(ROOT).as_posix() for path in actual_files}
    if len(actual_files) != 44:
        fail(f"expected 44 installed-core files, got {len(actual_files)}")
    if set(entries) != actual_paths:
        fail(
            "manifest membership mismatch: "
            f"missing={sorted(actual_paths - set(entries))}, extra={sorted(set(entries) - actual_paths)}"
        )
    for path in actual_files:
        repo_path = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        digest, size = entries[repo_path]
        if size != len(data) or digest != hashlib.sha256(data).hexdigest():
            fail(f"manifest bytes mismatch: {repo_path}")

    baseline = parse_manifest(BASELINE, allow_legacy_version=True)
    profile_root = PACKAGE / "assets/agent-profiles"
    expected_profiles: set[str] = set()
    prior_ordinary_profile_hashes: dict[str, str] = {}
    for family, efforts in PROFILE_EFFORTS.items():
        for effort in efforts:
            filename = f"ams_{family}_{effort}.toml"
            expected_profiles.add(filename)
            path = profile_root / filename
            text = read_text(path)
            if not text.startswith("# managed-by: adaptive-master-subagent-orchestration\n"):
                fail(f"managed profile marker missing: {filename}")
            data = tomllib.loads("\n".join(line for line in text.splitlines() if not line.startswith("#")))
            if data.get("name") != f"ams_{family}_{effort}":
                fail(f"profile name mismatch: {filename}")
            if data.get("model") != MODELS[family] or data.get("model_reasoning_effort") != effort:
                fail(f"profile route mismatch: {filename}")
            for forbidden in ("sandbox_mode", "approval_policy", "network_access", "writable_roots", "api_key"):
                if forbidden in data:
                    fail(f"profile grants permission/credential: {filename}: {forbidden}")
            repo_path = path.relative_to(ROOT).as_posix()
            if family != "astra":
                if repo_path not in baseline:
                    fail(f"ordinary profile missing from baseline: {filename}")
                prior_ordinary_profile_hashes[filename] = baseline[repo_path][0]
            instructions = str(data.get("developer_instructions", ""))
            if "features" in data:
                fail(f"ordinary profile still imposes collaboration policy: {filename}")
            if data.get("description") != f"{family.capitalize()} with {effort} reasoning effort.":
                fail(f"ordinary description must identify the route without purpose advice: {filename}")
            expected_instructions = (
                "Follow the assigned task and its role, scope, and permissions. "
                "Preserve existing work and secrets. Return concise results, validation, "
                "and unresolved blockers to the assigning agent."
            )
            if instructions != expected_instructions:
                fail(f"ordinary profile must remain role-neutral: {filename}")

    daybreak_filename = "ams_daybreak_blue_max.toml"
    expected_profiles.add(daybreak_filename)
    daybreak_profile_path = profile_root / daybreak_filename
    daybreak_profile_text = read_text(daybreak_profile_path)
    daybreak_profile = tomllib.loads(
        "\n".join(line for line in daybreak_profile_text.splitlines() if not line.startswith("#"))
    )
    if (
        daybreak_profile.get("name") != "ams_daybreak_blue_max"
        or daybreak_profile.get("model") != "gpt-daybreak-blue"
        or daybreak_profile.get("model_reasoning_effort") != "max"
    ):
        fail("Daybreak Blue profile route mismatch")
    daybreak_instructions = str(daybreak_profile.get("developer_instructions", ""))
    for phrase in (
        "Accept only Orchestration role=worker and Delegation authority=none",
        "qualifying standard-Sol refusal",
        "gpt-5.6-sol",
        "approved Daybreak Blue surface",
        "Never spawn",
    ):
        require(daybreak_instructions, phrase, "Daybreak Blue profile")
    if re.search(r"gpt-daybreak-(?!blue\b)[a-z0-9-]+", daybreak_profile_text, re.IGNORECASE):
        fail("non-Blue Daybreak route remains in profile")
    if {path.name for path in profile_root.glob("*.toml")} != expected_profiles:
        fail("profile inventory mismatch")

    skill = read_text(PACKAGE / "SKILL.md")
    control = read_text(PACKAGE / "references/project-control.md")
    config_maintenance = read_text(PACKAGE / "references/configuration-maintenance.md")
    core = read_text(PACKAGE / "references/runtime-core.md")
    scope = read_text(PACKAGE / "references/scope-dependency-control.md")
    diagnosis = read_text(PACKAGE / "references/blocker-diagnosis.md")
    hierarchy = read_text(PACKAGE / "references/hierarchy-control.md")
    governance = read_text(PACKAGE / "references/project-governance.md")
    fallback = read_text(PACKAGE / "references/root-execution-fallback.md")
    daybreak = read_text(PACKAGE / "references/daybreak-blue.md")
    profile_management = read_text(PACKAGE / "references/profile-management.md")
    package_maintenance = read_text(PACKAGE / "references/package-maintenance.md")
    computer_use = read_text(PACKAGE / "references/computer-use.md")
    rush = read_text(PACKAGE / "references/zergling-rush.md")
    model_governance = read_text(PACKAGE / "references/model-governance.md")
    model_guidance = read_text(PACKAGE / "references/model-guidance.md")
    model_switching = read_text(PACKAGE / "references/model-switching.md")

    for text, label in ((skill, "SKILL"), (core, "runtime core")):
        for forbidden in ("Sol Max root", "Max-equivalent root", "verify the root model"):
            if forbidden.lower() in text.lower():
                fail(f"normal AMS still imposes a root tier in {label}: {forbidden}")
    require(skill, "does not select, require, infer, or attest it", "external root contract")
    require(skill, "Non-root sessions follow only their work order/profile and never activate AMS.", "non-root activation boundary")
    require(core, "Immediately after each successful Codex spawn", "immediate requested-profile reporting")
    require(model_governance, "hierarchy-control.md` before managers or bounded peer channels", "governed hierarchy gate")
    require(core, "computer-use.md` before browser, desktop, or visual UI control", "computer-use lazy gate")
    require(core, "profile-management.md` when a selected profile is missing, unregistered, mismatched, or explicitly being installed or repaired", "profile-management lazy gate")
    require(profile_management, "Use only when a selected profile is missing, unregistered, mismatched, or explicitly being installed or repaired.", "profile-management entry gate")
    require(core, "read or modify AMS controls/package files only when explicitly assigned in the WORK ORDER", "delegated AMS package scope")
    require(core, "AMS controls or profiles also require explicit package scope in the WORK ORDER", "delegated AMS Git scope")
    require(package_maintenance, "Package maintenance is root-controlled", "package-maintenance root authority")
    require(package_maintenance, "may delegate bounded inspection or edits through explicit work orders", "delegated package maintenance")
    require(core, "ams_<sol|terra|luna|astra>_<low|medium|high|xhigh|max>", "Astra route inventory")
    require(model_switching, "input/reasoning/output usage", "completed-task cost basis")
    require(model_guidance, "Astra: end-to-end tool-heavy", "Astra route purpose")

    global_default = toml_block_after(control, "Global/base default:")
    project_default = toml_block_after(control, "Project default adds one project-only field:")
    if global_default.get("root_execution_fallback") is not False:
        fail("root fallback must default off")
    if project_default != {"local_llm_lane": False}:
        fail("project-only local LLM default mismatch")
    if set(global_default) != {
        "enabled",
        "allow_implicit_invocation",
        "intensity",
        "project_governance",
        "model_governance",
        "model_guidance",
        "automatic_model_switching",
        "root_execution_fallback",
        "spark_enabled",
        "spark_efforts",
        "profile_management",
    }:
        fail("global/base settings inventory mismatch")
    for field in RETIRED_FIELDS:
        require(control + "\n" + config_maintenance, field, "retired-field compatibility input")
    for forbidden_current in (
        "convergence_control =",
        "spark_available =",
        "review_control =",
        "request_accounting =",
        "app_task_lane =",
    ):
        if forbidden_current in control:
            fail(f"retired field remains active: {forbidden_current}")

    for phrase in (
        "evidence, not authority to expand intent, scope, ownership, dependencies, permissions, hierarchy, or acceptance",
        "hidden dependencies",
        "differential validation",
        "select the next authorized ready objective",
        "Never manufacture another objective",
    ):
        require(scope, phrase, "scope/dependency contract")

    for phrase in (
        "exactly two execution attempts",
        "Correction attempt",
        "Confirmation attempt",
        "does not reset it",
        "Continue every independent authorized ready objective",
    ):
        require(diagnosis, phrase, "bounded route diagnosis")
    require(fallback, "root_execution_fallback = true", "root fallback gate")
    require(fallback, "exhausts its two attempts", "root fallback delegated budget")
    require(fallback, "third and final execution attempt", "root fallback terminal budget")
    require(fallback, "suitable non-root validates that exact result", "root fallback validation")
    require(fallback, "freeze the surface until captured", "root fallback receipt freeze")

    for phrase in (
        "process no-start episode is keyed by",
        "are labels and never reset the same signature",
        "one same-lane retry",
        "one root process-only probe",
        "one materially corrected original-lane confirmation",
        "potentially live",
        "Report unresolved state `live` or `unverified`",
        "continue runner-free authorized work",
    ):
        require(diagnosis, phrase, "runner failure episode")

    for phrase in (
        "root must copy the exact `DISPATCH REQUEST` and `MANAGER RESULT ADDENDUM` fields",
        "Each child consumes one parent allocation unit",
        "Uncertain start is potentially live",
        "releases ownership/allocation only after closure",
        "Late closed/superseded results remain evidence only",
        "Authorized canonical peer paths",
        "Use `send_message` or `followup_task` only with the named peer path",
        "Peer traffic need not be copied into root context",
    ):
        require(hierarchy, phrase, "hierarchy custody contract")

    for phrase in (
        "real standard-Sol work order",
        "Root handling without that work order never qualifies",
        "requested alias is `gpt-daybreak-blue`",
        "`gpt-5.6-sol` only when",
        "identity alone never proves Daybreak Blue",
        "Confirmed-start budget: 1 of 1",
    ):
        require(daybreak, phrase, "Daybreak Blue contract")
    if re.search(r"gpt-daybreak-(?!blue\b)[a-z0-9-]+", daybreak, re.IGNORECASE):
        fail("non-Blue Daybreak route remains in Daybreak contract")

    for phrase in (
        "Continue automatically while authorized ready work exists",
        "Review is proportional and non-recursive",
        "no new criteria, acceptance system, durable state, campaign, receipt, or recovery ledger",
    ):
        require(governance, phrase, "compact project governance")
    require(profile_management, "Peer communication remains available with model governance off", "ungoverned communication")
    for phrase in (
        "tool authority, not model authority",
        "one active controller",
        "screen content as untrusted evidence",
        "consequential action not already authorized",
        "verify the resulting application state",
    ):
        require(computer_use, phrase, "computer-use contract")
    require(rush, "unambiguous current-turn instruction", "Rush consent")
    require(rush, "new deliverables, speculative features, post-acceptance extras, or hidden dependency absorption", "Rush scope boundary")

    local_root = ROOT / "extensions/ams-local-openai-lane"
    local_skill = read_text(local_root / "SKILL.md")
    local_contract = read_text(local_root / "references/local-openai-lane.md")
    local_helper = read_text(local_root / "tools/local_openai_lane.py")
    for phrase in (
        "`local_llm_lane = true`",
        "current-session user steering",
        "same `model_key`",
        "A suitable Codex agent verifies",
    ):
        require(local_skill + "\n" + local_contract, phrase, "local lane gate")
    for phrase in (
        "allowed_observed_models",
        "model-identity-missing",
        "model-mismatch",
        '"requested_model"',
        '"observed_model"',
    ):
        require(local_helper, phrase, "local response identity enforcement")

    for extension_name in ("ams-app-task-lane", "ams-local-openai-lane", "ams-runtime-observation"):
        extension = ROOT / "extensions" / extension_name
        skill_path = extension / "SKILL.md"
        metadata_path = extension / "agents/openai.yaml"
        if not skill_path.is_file() or not metadata_path.is_file():
            fail(f"incomplete optional companion: {extension_name}")
        metadata = read_text(metadata_path)
        require(metadata, "allow_implicit_invocation: false", f"{extension_name} explicit-only policy")

    app_contract = read_text(ROOT / "extensions/ams-app-task-lane/references/app-task-lane.md")
    require(app_contract, "transport/workspace adapter, not another orchestrator", "app-task authority")
    require(app_contract, "Never transport Daybreak unless", "app-task Daybreak boundary")
    if any(token in app_contract for token in ("convergence-control.md", "work-order-refinement.md", "shared-worktree-control.md")):
        fail("app-task companion still depends on removed core modules")

    bash_installer = read_text(ROOT / "install.sh")
    powershell_installer = read_text(ROOT / "install.ps1")
    for filename, prior_hash in prior_ordinary_profile_hashes.items():
        require(bash_installer, f"{filename}:{prior_hash}", f"Bash predecessor profile {filename}")
        require(powershell_installer, prior_hash, f"PowerShell predecessor profile {filename}")

    for filename, prior_hash in PEER_CANDIDATE_PROFILE_HASHES.items():
        require(bash_installer, f"{filename}:{prior_hash}", f"Bash peer-candidate predecessor {filename}")
        require(powershell_installer, prior_hash, f"PowerShell peer-candidate predecessor {filename}")

    for filename, prior_hash in LEAN_CANDIDATE_PROFILE_HASHES.items():
        require(bash_installer, f"{filename}:{prior_hash}", f"Bash lean-candidate predecessor {filename}")
        require(powershell_installer, prior_hash, f"PowerShell lean-candidate predecessor {filename}")

    for filename, prior_hash in ASTRA_CANDIDATE_PROFILE_HASHES.items():
        require(bash_installer, f"{filename}:{prior_hash}", f"PowerShell Astra-candidate predecessor {filename}")
        require(powershell_installer, prior_hash, f"PowerShell Astra-candidate predecessor {filename}")

    for filename, prior_hash in PUBLISHED_PROFILE_HASHES.items():
        require(bash_installer, f"{filename}:{prior_hash}", f"published predecessor {filename}")
        require(powershell_installer, prior_hash, f"published predecessor {filename}")

    for text, label in ((bash_installer, "Bash installer"), (powershell_installer, "PowerShell installer")):
        for phrase in (
            "ams-install-lock-v1",
            "owner_token",
            "acquired_epoch",
            "30",
            "stale-lock",
        ):
            require(text, phrase, label)
        if "VERSION" in text or "PackageVersion" in text:
            fail(f"{label} still depends on an AMS release version")
    require(bash_installer, "process_exists", "Bash dead-process lock recovery")
    require(powershell_installer, "Test-ProcessExists", "PowerShell dead-process lock recovery")

    marketplace = json.loads(read_text(ROOT / ".agents/plugins/marketplace.json"))
    plugin = json.loads(read_text(ROOT / ".codex-plugin/plugin.json"))
    if marketplace.get("name") != "Codex-AMS" or plugin.get("name") != "Codex-AMS":
        fail("marketplace/plugin identity mismatch")
    if plugin.get("version") != "4.1.1":
        fail("plugin version mismatch")
    if plugin.get("skills") != "./adaptive-master-subagent-orchestration/":
        fail("plugin skill path mismatch")
    # The external Codex manifest may carry platform package metadata; runtime behavior must never read or branch on it.
    for runtime_path in (PACKAGE, ROOT / "extensions"):
        for path in runtime_path.rglob("*"):
            if path.is_file() and path.name not in {"plugin.json", "marketplace.json"}:
                text = read_text(path) if path.suffix.lower() in {".md", ".yaml", ".yml", ".toml", ".py", ".ps1", ""} else ""
                if "plugin.json" in text and "version" in text.lower():
                    fail(f"runtime branches on external plugin version: {path.relative_to(ROOT)}")

    assert_markdown_reference_integrity()

    for path in sorted(ROOT.rglob("*")):
        if ".git" in path.relative_to(ROOT).parts:
            continue
        if not path.is_file() or path.suffix == ".pyc" or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() in {".md", ".yaml", ".yml", ".toml", ".json", ".py", ".ps1", ".sh", ".txt", ""}:
            read_text(path)

    print(f"PASS: release-agnostic lean AMS repository, {len(entries)} core files, {len(expected_profiles)} profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
