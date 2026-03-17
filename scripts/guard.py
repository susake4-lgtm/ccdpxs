#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure scripts/ directory is on sys.path for cross-imports (check_defs, check_engine)
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


STAGES = [
    "intake",
    "killer_test",
    "premise_test",
    "idea_fission",
    "evaluation",
    "structure",
    "outline",
    "scene_pressure_test",
    "prototype",
    "expansion",
    "review",
]

STAGE_INDEX = {stage: index + 1 for index, stage in enumerate(STAGES)}
ALLOWED_MODES = {"writing", "debug"}
DEFAULT_STATE_VERSION = 5


REQUIRED_PROJECT_PATHS = [
    "PROJECT_INFO.md",
    "00_Brainstorm.md",
    "00_Killer_Test.md",
    "00_Creative_Chat_Log.md",
    "01_Evaluation_Log.md",
    "02_Structure.md",
    "03_Outline.md",
    "04_Prototype.md",
    "chapters",
    "stage_logs",
]

STAGE_LOG_DIRS = {
    "intake": "stage_logs/00_intake",
    "killer_test": "stage_logs/00_killer-test",
    "premise_test": "stage_logs/00_intake",
    "idea_fission": "stage_logs/01_idea-fission",
    "evaluation": "stage_logs/02_evaluation",
    "structure": "stage_logs/03_structure",
    "outline": "stage_logs/04_outline",
    "scene_pressure_test": "stage_logs/04_scene-pressure-test",
    "prototype": "stage_logs/05_prototype",
    "expansion": "stage_logs/06_expansion",
    "review": "stage_logs/07_review",
}

TOTAL_STAGE_FILES = {
    "intake": ["00_Brainstorm.md", "00_Creative_Chat_Log.md"],
    "killer_test": ["00_Killer_Test.md", "00_Creative_Chat_Log.md"],
    "premise_test": ["00_Brainstorm.md", "00_Creative_Chat_Log.md"],
    "idea_fission": ["00_Brainstorm.md", "00_Creative_Chat_Log.md"],
    "evaluation": ["01_Evaluation_Log.md", "00_Creative_Chat_Log.md"],
    "structure": ["02_Structure.md", "00_Creative_Chat_Log.md"],
    "outline": ["03_Outline.md", "00_Creative_Chat_Log.md"],
    "scene_pressure_test": ["03_Outline.md", "00_Creative_Chat_Log.md"],
    "prototype": ["04_Prototype.md", "00_Creative_Chat_Log.md"],
    "expansion": ["00_Creative_Chat_Log.md", "chapters"],
    "review": ["00_Creative_Chat_Log.md"],
}

GATE_CONFIRMATION_STAGES = {
    "idea_fission",
    "evaluation",
    "structure",
    "outline",
    "scene_pressure_test",
    "prototype",
    "expansion",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")



def default_state(project_slug: str, project_title: str | None = None) -> dict[str, Any]:
    return {
        "version": DEFAULT_STATE_VERSION,
        "project_slug": project_slug,
        "project_title": project_title or project_slug,
        "mode": "writing",
        "current_stage": "intake",
        "killer_test_passed": False,
        "killer_test_attempts": 0,
        "premise_test_passed": False,
        "confirmations": {stage: False for stage in GATE_CONFIRMATION_STAGES},
        "stage_history": [
            {
                "timestamp": utc_now(),
                "action": "init",
                "stage": "intake",
                "note": "Project initialized",
            }
        ],
    }


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def project_dir(project_slug: str) -> Path:
    return repo_root() / "output" / project_slug


def state_path(project_slug: str) -> Path:
    return project_dir(project_slug) / "project_state.json"



def ensure_project_exists(project_slug: str) -> Path:
    candidate = project_dir(project_slug)
    if not candidate.is_dir():
        raise SystemExit(f"Error: missing project directory: {candidate}")
    return candidate


def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error: invalid JSON file: {path}: {exc}") from exc


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    state["version"] = DEFAULT_STATE_VERSION
    state.setdefault("project_slug", "")
    state.setdefault("project_title", state["project_slug"])
    state.setdefault("mode", "writing")
    state.setdefault("current_stage", "intake")
    state.setdefault("killer_test_passed", False)
    state.setdefault("killer_test_attempts", 0)
    state.setdefault("premise_test_passed", False)
    confirmations = state.setdefault("confirmations", {})
    for stage in GATE_CONFIRMATION_STAGES:
        confirmations.setdefault(stage, False)
    state.setdefault("stage_history", [])
    state.setdefault("checks", {})
    return state


def read_state(project_slug: str) -> dict[str, Any]:
    path = state_path(project_slug)
    if not path.is_file():
        raise SystemExit(f"Error: missing state file: {path}")
    raw = read_json_file(path, {})
    if not isinstance(raw, dict):
        raise SystemExit(f"Error: invalid state payload type in {path}")
    return normalize_state(raw)


def write_state(project_slug: str, state: dict[str, Any]) -> None:
    write_json_file(state_path(project_slug), normalize_state(state))


def require_valid_stage(stage: str) -> str:
    if stage not in STAGE_INDEX:
        raise SystemExit(f"Error: unknown stage: {stage}")
    return stage


def resolve_stage_token(token: str, current_stage: str) -> str:
    normalized = token.strip().lower()
    if normalized in {"prev", "previous"}:
        current_index = STAGE_INDEX[current_stage]
        if current_index == 1:
            raise SystemExit("Error: already at the first stage")
        return STAGES[current_index - 2]

    if normalized.isdigit():
        numeric = int(normalized)
        if not 1 <= numeric <= len(STAGES):
            raise SystemExit(f"Error: step must be between 1 and {len(STAGES)}")
        return STAGES[numeric - 1]

    return require_valid_stage(normalized)


def append_history(state: dict[str, Any], action: str, stage: str, note: str | None) -> None:
    state.setdefault("stage_history", []).append(
        {
            "timestamp": utc_now(),
            "action": action,
            "stage": stage,
            "note": note or "",
        }
    )


def file_exists(project_root: Path, relative_path: str) -> bool:
    return (project_root / relative_path).exists()


def stage_has_log(project_root: Path, stage: str) -> bool:
    log_dir = project_root / STAGE_LOG_DIRS[stage]
    if not log_dir.is_dir():
        return False
    for candidate in sorted(log_dir.iterdir()):
        if candidate.name == ".gitkeep":
            continue
        if candidate.is_file():
            return True
    return False


def chat_log_has_content(project_root: Path) -> bool:
    """Return True if 00_Creative_Chat_Log.md has at least one recorded decision."""
    log_path = project_root / "00_Creative_Chat_Log.md"
    if not log_path.exists():
        return False
    content = log_path.read_text(encoding="utf-8")
    # Require at least one non-empty 关键决策 line
    return bool(re.search(r"^- 关键决策[：:]\s*\S", content, re.MULTILINE))


def validate_project_files(project_root: Path) -> list[str]:
    missing: list[str] = []
    for relative_path in REQUIRED_PROJECT_PATHS:
        if not file_exists(project_root, relative_path):
            missing.append(relative_path)
    return missing


def blockers_for_target(
    project_root: Path,
    state: dict[str, Any],
    target_stage: str,
    skip_log_check: bool = False,
) -> list[str]:
    blockers: list[str] = []
    current_stage = require_valid_stage(state["current_stage"])
    current_index = STAGE_INDEX[current_stage]
    target_index = STAGE_INDEX[target_stage]

    if target_index > current_index + 1:
        blockers.append(
            f"Cannot jump forward from {current_stage} to {target_stage}; only the next stage is allowed."
        )
        return blockers

    if target_index < current_index:
        return blockers

    # Killer test gate: must pass before entering premise_test or later
    if target_stage in {
        "premise_test", "idea_fission", "evaluation", "structure",
        "outline", "scene_pressure_test", "prototype", "expansion", "review",
    }:
        if not state.get("killer_test_passed", False):
            blockers.append("Premise killer test has not passed yet.")

    # Premise test gate: must pass before entering idea_fission or later
    if target_stage in {
        "idea_fission", "evaluation", "structure", "outline",
        "scene_pressure_test", "prototype", "expansion", "review",
    }:
        if not state.get("premise_test_passed", False):
            blockers.append("Premise pressure test has not passed yet.")

    if target_index > current_index and current_stage in GATE_CONFIRMATION_STAGES:
        if not state.get("confirmations", {}).get(current_stage, False):
            blockers.append(f"Missing user confirmation for stage: {current_stage}.")

    stage_to_validate = current_stage
    required_files = TOTAL_STAGE_FILES.get(stage_to_validate, [])
    for relative_path in required_files:
        if not file_exists(project_root, relative_path):
            blockers.append(f"Missing required file or directory for {stage_to_validate}: {relative_path}")

    if not skip_log_check:
        required_log_stage = "intake" if stage_to_validate == "premise_test" else stage_to_validate
        if not stage_has_log(project_root, required_log_stage):
            blockers.append(f"Missing non-placeholder stage log in {STAGE_LOG_DIRS[required_log_stage]}")

    # Chat log content check: 00_Creative_Chat_Log.md must have at least one recorded decision
    if not chat_log_has_content(project_root):
        blockers.append(
            "00_Creative_Chat_Log.md has no recorded decisions yet. "
            "Add at least one '- 关键决策: <content>' entry before advancing."
        )

    # 检查压力测试是否完成（仅当检查会话已启动时）
    from check_engine import check_blockers_for_advance
    check_blocks = check_blockers_for_advance(state, current_stage)
    blockers.extend(check_blocks)

    return blockers




def command_init_state(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    path = state_path(args.project)
    if path.exists() and not args.force:
        raise SystemExit(f"Error: state file already exists: {path}")

    state = default_state(args.project, args.title)
    if args.mode:
        if args.mode not in ALLOWED_MODES:
            raise SystemExit(f"Error: invalid mode: {args.mode}")
        state["mode"] = args.mode
    write_state(args.project, state)
    print(f"Initialized state: {path}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    state = read_state(args.project)
    missing = validate_project_files(project_root)

    current_stage = state["current_stage"]
    print(f"Project: {args.project}")
    print(f"Mode: {state['mode']}")
    print(f"Current stage: {current_stage} (step {STAGE_INDEX[current_stage]})")
    print(f"Killer test passed: {'yes' if state.get('killer_test_passed') else 'no'}"
          f" (attempts: {state.get('killer_test_attempts', 0)}/2)")
    print(f"Premise test passed: {'yes' if state.get('premise_test_passed') else 'no'}")
    print("Confirmations:")
    for stage in STAGES:
        if stage in GATE_CONFIRMATION_STAGES:
            value = state.get("confirmations", {}).get(stage, False)
            print(f"  - {stage}: {'yes' if value else 'no'}")
    if missing:
        print("Missing project paths:")
        for relative_path in missing:
            print(f"  - {relative_path}")
    else:
        print("Missing project paths: none")

    history = state.get("stage_history", [])
    if history:
        print("Recent history:")
        for event in history[-5:]:
            note = event.get("note", "")
            suffix = f" | {note}" if note else ""
            print(f"  - {event['timestamp']} | {event['action']} | {event['stage']}{suffix}")

    return 0


def command_check(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    state = read_state(args.project)
    target_stage = require_valid_stage(args.target or state["current_stage"])

    missing = validate_project_files(project_root)
    blockers = []
    if missing:
        blockers.extend(f"Missing project path: {relative_path}" for relative_path in missing)
    blockers.extend(blockers_for_target(project_root, state, target_stage))

    print(f"Project: {args.project}")
    print(f"Current stage: {state['current_stage']}")
    print(f"Target stage: {target_stage}")
    if blockers:
        print("Blocked:")
        for item in blockers:
            print(f"  - {item}")
        return 1

    print("OK: target stage is currently allowed.")
    return 0


def command_set_mode(args: argparse.Namespace) -> int:
    state = read_state(args.project)
    if args.mode not in ALLOWED_MODES:
        raise SystemExit(f"Error: invalid mode: {args.mode}")
    state["mode"] = args.mode
    append_history(state, "set_mode", state["current_stage"], args.note or f"Mode set to {args.mode}")
    write_state(args.project, state)
    print(f"Mode updated to {args.mode}")
    return 0


def command_set_killer_test(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    state = read_state(args.project)
    passed = args.result == "pass"

    attempts = state.get("killer_test_attempts", 0) + 1
    state["killer_test_attempts"] = attempts
    state["killer_test_passed"] = passed

    if passed and STAGE_INDEX[state["current_stage"]] < STAGE_INDEX["killer_test"]:
        state["current_stage"] = "killer_test"

    note = args.note
    if not note:
        if passed:
            note = f"Killer test passed (attempt {attempts})"
        elif attempts >= 2:
            note = f"Killer test failed (attempt {attempts}) — recommend freeze"
        else:
            note = f"Killer test failed (attempt {attempts}) — rewrite allowed"

    append_history(state, "killer_test", "killer_test", note)
    write_state(args.project, state)

    print(f"Killer test: {'passed' if passed else 'failed'} (attempt {attempts}/2)")
    if not passed and attempts >= 2:
        print("Warning: max attempts reached. Consider freezing this brainstorm.")
    return 0


def command_set_premise(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    state = read_state(args.project)
    passed = args.result == "pass"
    state["premise_test_passed"] = passed
    if passed and STAGE_INDEX[state["current_stage"]] < STAGE_INDEX["premise_test"]:
        state["current_stage"] = "premise_test"
    if not passed:
        state["mode"] = "debug"
    append_history(
        state,
        "premise_test",
        "premise_test",
        args.note or ("Premise test passed" if passed else "Premise test failed"),
    )
    write_state(args.project, state)
    print(f"Premise test marked as {'passed' if passed else 'failed'}")
    return 0


def command_confirm(args: argparse.Namespace) -> int:
    stage = require_valid_stage(args.stage)
    if stage not in GATE_CONFIRMATION_STAGES:
        raise SystemExit(f"Error: stage does not use a confirmation gate: {stage}")
    state = read_state(args.project)
    state.setdefault("confirmations", {})[stage] = True
    append_history(state, "confirm", stage, args.note or f"Confirmed stage {stage}")
    write_state(args.project, state)
    print(f"Confirmation recorded for {stage}")
    return 0


def command_clear_confirmation(args: argparse.Namespace) -> int:
    stage = require_valid_stage(args.stage)
    if stage not in GATE_CONFIRMATION_STAGES:
        raise SystemExit(f"Error: stage does not use a confirmation gate: {stage}")
    state = read_state(args.project)
    state.setdefault("confirmations", {})[stage] = False
    append_history(state, "clear_confirmation", stage, args.note or f"Cleared confirmation for {stage}")
    write_state(args.project, state)
    print(f"Confirmation cleared for {stage}")
    return 0


def clear_future_confirmations(state: dict[str, Any], current_stage: str) -> None:
    current_index = STAGE_INDEX[current_stage]
    for stage in GATE_CONFIRMATION_STAGES:
        if STAGE_INDEX[stage] >= current_index:
            state.setdefault("confirmations", {})[stage] = False


def command_advance(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    state = read_state(args.project)
    target_stage = require_valid_stage(args.stage)
    current_stage = require_valid_stage(state["current_stage"])
    current_index = STAGE_INDEX[current_stage]
    target_index = STAGE_INDEX[target_stage]

    if target_index <= current_index:
        raise SystemExit(
            f"Error: advance only accepts the next stage; use rewind for backwards movement. Current: {current_stage}"
        )

    blockers = blockers_for_target(project_root, state, target_stage, skip_log_check=args.skip_log_check)
    if blockers:
        print("Blocked:")
        for item in blockers:
            print(f"  - {item}")
        return 1

    previous_stage = state["current_stage"]
    state["current_stage"] = target_stage
    clear_future_confirmations(state, target_stage)
    append_history(state, "advance", target_stage, args.note or f"Advanced from {previous_stage} to {target_stage}")
    write_state(args.project, state)
    print(f"Advanced to {target_stage}")
    return 0


def command_rewind(args: argparse.Namespace) -> int:
    ensure_project_exists(args.project)
    state = read_state(args.project)
    current_stage = require_valid_stage(state["current_stage"])
    target_stage = resolve_stage_token(args.target, current_stage)
    if target_stage == current_stage:
        raise SystemExit(f"Error: project is already at stage: {current_stage}")
    if STAGE_INDEX[target_stage] > STAGE_INDEX[current_stage]:
        raise SystemExit(f"Error: rewind target must not be ahead of current stage: {target_stage}")

    previous_stage = current_stage
    state["current_stage"] = target_stage
    clear_future_confirmations(state, target_stage)
    if STAGE_INDEX[target_stage] < STAGE_INDEX["killer_test"]:
        state["killer_test_passed"] = False
        state["killer_test_attempts"] = 0
    if STAGE_INDEX[target_stage] < STAGE_INDEX["premise_test"]:
        state["premise_test_passed"] = False
    append_history(
        state,
        "rewind",
        target_stage,
        args.note or f"Rewound from {previous_stage} to {target_stage}",
    )
    write_state(args.project, state)
    print(f"Rewound to {target_stage} (step {STAGE_INDEX[target_stage]})")
    print("Note: rewind is non-destructive; previous files and logs are preserved.")
    return 0



# ---------------------------------------------------------------------------
# Pressure test commands
# ---------------------------------------------------------------------------

def command_run_checks(args: argparse.Namespace) -> int:
    ensure_project_exists(args.project)
    state = read_state(args.project)
    stage = require_valid_stage(args.stage)
    from check_engine import init_check_session, generate_check_template
    init_check_session(state, stage)
    write_state(args.project, state)
    print(generate_check_template(stage))
    return 0


def command_submit_check(args: argparse.Namespace) -> int:
    ensure_project_exists(args.project)
    state = read_state(args.project)
    stage = require_valid_stage(args.stage)
    from check_engine import submit_check_result
    msg = submit_check_result(
        state, stage, args.check_id, args.result,
        score=args.score, note=args.note or "",
    )
    write_state(args.project, state)
    print(msg)
    return 0 if msg.startswith("OK") else 1


def command_submit_checks(args: argparse.Namespace) -> int:
    ensure_project_exists(args.project)
    state = read_state(args.project)
    stage = require_valid_stage(args.stage)
    import sys as _sys
    raw = _sys.stdin.read()
    items = json.loads(raw)
    from check_engine import submit_checks_batch
    messages = submit_checks_batch(state, stage, items)
    write_state(args.project, state)
    for msg in messages:
        print(msg)
    return 0


def command_check_status(args: argparse.Namespace) -> int:
    ensure_project_exists(args.project)
    state = read_state(args.project)
    stage = require_valid_stage(args.stage)
    from check_engine import get_check_status, compute_aggregate_score
    status = get_check_status(state, stage)
    print(f"Stage: {stage}")
    print(f"完成度: {status['done']}/{status['total']}")
    print(f"通过: {status['passed']} | 未通过: {status['failed']} | 跳过: {status['skipped']} | 待填: {status['pending']}")
    if status["pending_ids"]:
        print("待填项:")
        for cid in status["pending_ids"]:
            print(f"  - {cid}")
    agg = compute_aggregate_score(state, stage)
    if agg:
        print(f"聚合评分: {agg['total_score']}/{agg['max_score']} (判定: {agg['level'] or '—'})")
    return 0


def command_check_report(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    state = read_state(args.project)
    stage = require_valid_stage(args.stage)
    from check_engine import generate_check_report
    report = generate_check_report(state, stage, project_root)
    print(report)
    return 0


def command_check_chapter(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    state = read_state(args.project)
    chapter_num = str(args.chapter_num)
    from check_engine import (
        init_chapter_check_session, generate_check_template,
        get_check_status, generate_check_report,
    )
    if args.report:
        report = generate_check_report(state, "expansion", project_root, chapter_num=chapter_num)
        print(report)
    else:
        init_chapter_check_session(state, chapter_num)
        write_state(args.project, state)
        print(generate_check_template("expansion"))
        print(f"\n提交时使用: guard.py submit-check {args.project} expansion <check_id> <result> (章号通过内部状态追踪)")
    return 0


def command_skip_check(args: argparse.Namespace) -> int:
    ensure_project_exists(args.project)
    state = read_state(args.project)
    stage = require_valid_stage(args.stage)
    from check_engine import skip_check
    msg = skip_check(state, stage, args.check_id, args.reason)
    write_state(args.project, state)
    print(msg)
    return 0 if msg.startswith("OK") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Guard project state transitions and enforce stage gates."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_state = subparsers.add_parser("init-state", help="Create a state file for a project")
    init_state.add_argument("project")
    init_state.add_argument("--title")
    init_state.add_argument("--mode", choices=sorted(ALLOWED_MODES))
    init_state.add_argument("--force", action="store_true")
    init_state.set_defaults(func=command_init_state)

    status = subparsers.add_parser("status", help="Show project state")
    status.add_argument("project")
    status.set_defaults(func=command_status)

    check = subparsers.add_parser("check", help="Validate whether a target stage is allowed")
    check.add_argument("project")
    check.add_argument("--target", choices=STAGES)
    check.set_defaults(func=command_check)

    set_mode = subparsers.add_parser("set-mode", help="Switch writing/debug mode")
    set_mode.add_argument("project")
    set_mode.add_argument("mode", choices=sorted(ALLOWED_MODES))
    set_mode.add_argument("--note")
    set_mode.set_defaults(func=command_set_mode)

    set_killer_test = subparsers.add_parser("set-killer-test", help="Record killer test result")
    set_killer_test.add_argument("project")
    set_killer_test.add_argument("result", choices=["pass", "fail"])
    set_killer_test.add_argument("--note")
    set_killer_test.set_defaults(func=command_set_killer_test)

    set_premise = subparsers.add_parser("set-premise", help="Record premise test result")
    set_premise.add_argument("project")
    set_premise.add_argument("result", choices=["pass", "fail"])
    set_premise.add_argument("--note")
    set_premise.set_defaults(func=command_set_premise)

    confirm = subparsers.add_parser("confirm", help="Record user confirmation for a stage")
    confirm.add_argument("project")
    confirm.add_argument("stage", choices=sorted(GATE_CONFIRMATION_STAGES))
    confirm.add_argument("--note")
    confirm.set_defaults(func=command_confirm)

    clear_confirmation = subparsers.add_parser(
        "clear-confirmation", help="Clear an existing user confirmation"
    )
    clear_confirmation.add_argument("project")
    clear_confirmation.add_argument("stage", choices=sorted(GATE_CONFIRMATION_STAGES))
    clear_confirmation.add_argument("--note")
    clear_confirmation.set_defaults(func=command_clear_confirmation)

    advance = subparsers.add_parser("advance", help="Advance to the next allowed stage")
    advance.add_argument("project")
    advance.add_argument("stage", choices=STAGES)
    advance.add_argument("--note")
    advance.add_argument("--skip-log-check", action="store_true", help="Skip stage_logs file check")
    advance.set_defaults(func=command_advance)

    rewind = subparsers.add_parser("rewind", help="Rewind to previous stage, a named stage, or a step number")
    rewind.add_argument("project")
    rewind.add_argument("target", help="previous | <stage-name> | <step-number>")
    rewind.add_argument("--note")
    rewind.set_defaults(func=command_rewind)

    # -- Pressure test commands --
    run_checks = subparsers.add_parser("run-checks", help="Initialize check session and output template")
    run_checks.add_argument("project")
    run_checks.add_argument("stage", choices=STAGES)
    run_checks.set_defaults(func=command_run_checks)

    submit_check_cmd = subparsers.add_parser("submit-check", help="Submit a single check result")
    submit_check_cmd.add_argument("project")
    submit_check_cmd.add_argument("stage", choices=STAGES)
    submit_check_cmd.add_argument("check_id")
    submit_check_cmd.add_argument("result", choices=["pass", "fail", "skip"])
    submit_check_cmd.add_argument("--score", type=int)
    submit_check_cmd.add_argument("--note", default="")
    submit_check_cmd.set_defaults(func=command_submit_check)

    submit_checks_cmd = subparsers.add_parser("submit-checks", help="Batch submit check results from stdin JSON")
    submit_checks_cmd.add_argument("project")
    submit_checks_cmd.add_argument("stage", choices=STAGES)
    submit_checks_cmd.set_defaults(func=command_submit_checks)

    check_status_cmd = subparsers.add_parser("check-status", help="Show check completion status for a stage")
    check_status_cmd.add_argument("project")
    check_status_cmd.add_argument("stage", choices=STAGES)
    check_status_cmd.set_defaults(func=command_check_status)

    check_report_cmd = subparsers.add_parser("check-report", help="Generate check report (stdout + md file)")
    check_report_cmd.add_argument("project")
    check_report_cmd.add_argument("stage", choices=STAGES)
    check_report_cmd.set_defaults(func=command_check_report)

    check_chapter_cmd = subparsers.add_parser("check-chapter", help="Single chapter pressure test (expansion)")
    check_chapter_cmd.add_argument("project")
    check_chapter_cmd.add_argument("chapter_num", type=int)
    check_chapter_cmd.add_argument("--report", action="store_true", help="Generate report instead of template")
    check_chapter_cmd.set_defaults(func=command_check_chapter)

    skip_check_cmd = subparsers.add_parser("skip-check", help="Skip a check with reason")
    skip_check_cmd.add_argument("project")
    skip_check_cmd.add_argument("stage", choices=STAGES)
    skip_check_cmd.add_argument("check_id")
    skip_check_cmd.add_argument("--reason", required=True)
    skip_check_cmd.set_defaults(func=command_skip_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
