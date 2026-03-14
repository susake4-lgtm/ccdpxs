#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGES = [
    "intake",
    "premise_test",
    "idea_fission",
    "evaluation",
    "structure",
    "outline",
    "prototype",
    "expansion",
    "review",
]

STAGE_INDEX = {stage: index + 1 for index, stage in enumerate(STAGES)}
ALLOWED_MODES = {"writing", "debug"}
KNOWLEDGE_KINDS = {"idea", "lesson", "risk", "rejection", "rule", "fragment"}
REVIEW_ACTIONS = {"保留", "丢弃", "稍后"}
DEFAULT_STATE_VERSION = 3

REQUIRED_PROJECT_PATHS = [
    "PROJECT_INFO.md",
    "00_Brainstorm.md",
    "00_Creative_Chat_Log.md",
    "01_Evaluation_Log.md",
    "02_Structure.md",
    "03_Outline.md",
    "04_Prototype.md",
    "chapters",
    "stage_logs",
    "knowledge",
    "knowledge/candidates",
    "knowledge/candidates/index.json",
    "knowledge/reviews",
    "knowledge/entries",
    "knowledge/entries/index.json",
]

STAGE_LOG_DIRS = {
    "intake": "stage_logs/00_intake",
    "premise_test": "stage_logs/00_intake",
    "idea_fission": "stage_logs/01_idea-fission",
    "evaluation": "stage_logs/02_evaluation",
    "structure": "stage_logs/03_structure",
    "outline": "stage_logs/04_outline",
    "prototype": "stage_logs/05_prototype",
    "expansion": "stage_logs/06_expansion",
    "review": "stage_logs/07_review",
}

TOTAL_STAGE_FILES = {
    "intake": ["00_Brainstorm.md", "00_Creative_Chat_Log.md"],
    "premise_test": ["00_Brainstorm.md", "00_Creative_Chat_Log.md"],
    "idea_fission": ["00_Brainstorm.md", "00_Creative_Chat_Log.md"],
    "evaluation": ["01_Evaluation_Log.md", "00_Creative_Chat_Log.md"],
    "structure": ["02_Structure.md", "00_Creative_Chat_Log.md"],
    "outline": ["03_Outline.md", "00_Creative_Chat_Log.md"],
    "prototype": ["04_Prototype.md", "00_Creative_Chat_Log.md"],
    "expansion": ["00_Creative_Chat_Log.md", "chapters"],
    "review": ["00_Creative_Chat_Log.md"],
}

GATE_CONFIRMATION_STAGES = {
    "idea_fission",
    "evaluation",
    "structure",
    "outline",
    "prototype",
    "expansion",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff._-]+", "-", value.strip().lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-._")
    return normalized or "entry"


def next_numeric_id(items: list[dict[str, Any]]) -> int:
    return max((int(item.get("id", 0)) for item in items), default=0) + 1


def default_state(project_slug: str, project_title: str | None = None) -> dict[str, Any]:
    return {
        "version": DEFAULT_STATE_VERSION,
        "project_slug": project_slug,
        "project_title": project_title or project_slug,
        "mode": "writing",
        "current_stage": "intake",
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


def knowledge_root(project_root: Path) -> Path:
    return project_root / "knowledge"


def candidates_dir(project_root: Path) -> Path:
    return knowledge_root(project_root) / "candidates"


def candidates_index_path(project_root: Path) -> Path:
    return candidates_dir(project_root) / "index.json"


def entries_dir(project_root: Path) -> Path:
    return knowledge_root(project_root) / "entries"


def entries_index_path(project_root: Path) -> Path:
    return entries_dir(project_root) / "index.json"


def reviews_dir(project_root: Path) -> Path:
    return knowledge_root(project_root) / "reviews"


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
    state.setdefault("premise_test_passed", False)
    confirmations = state.setdefault("confirmations", {})
    for stage in GATE_CONFIRMATION_STAGES:
        confirmations.setdefault(stage, False)
    state.setdefault("stage_history", [])
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

    if target_stage in {"idea_fission", "evaluation", "structure", "outline", "prototype", "expansion", "review"}:
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

    return blockers


def ensure_knowledge_base(project_root: Path) -> None:
    root = knowledge_root(project_root)
    candidate_root = candidates_dir(project_root)
    entry_root = entries_dir(project_root)
    review_root = reviews_dir(project_root)
    legacy_index = root / "index.json"

    root.mkdir(parents=True, exist_ok=True)
    candidate_root.mkdir(parents=True, exist_ok=True)
    entry_root.mkdir(parents=True, exist_ok=True)
    review_root.mkdir(parents=True, exist_ok=True)

    candidate_index = candidates_index_path(project_root)
    if not candidate_index.exists():
        write_json_file(candidate_index, [])

    entry_index = entries_index_path(project_root)
    if not entry_index.exists():
        if legacy_index.exists():
            legacy_payload = read_json_file(legacy_index, [])
            if isinstance(legacy_payload, list):
                write_json_file(entry_index, legacy_payload)
            else:
                write_json_file(entry_index, [])
        else:
            write_json_file(entry_index, [])

    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Knowledge\n\n"
            "这里按三层维护知识：候选、审核、正式知识。\n\n"
            "1. `candidates/`：候选条目，允许粗糙。\n"
            "2. `reviews/`：筛选文档，用中文标记保留、丢弃、合并、稍后。\n"
            "3. `entries/`：正式知识库，只放确认过的高价值内容。\n",
            encoding="utf-8",
        )


def load_index(index_path: Path, label: str) -> list[dict[str, Any]]:
    raw = read_json_file(index_path, [])
    if not isinstance(raw, list):
        raise SystemExit(f"Error: invalid {label} index type: {index_path}")
    return raw


def read_candidates(project_root: Path) -> list[dict[str, Any]]:
    ensure_knowledge_base(project_root)
    return load_index(candidates_index_path(project_root), "candidate")


def write_candidates(project_root: Path, payload: list[dict[str, Any]]) -> None:
    write_json_file(candidates_index_path(project_root), payload)


def read_entries(project_root: Path) -> list[dict[str, Any]]:
    ensure_knowledge_base(project_root)
    return load_index(entries_index_path(project_root), "entry")


def write_entries(project_root: Path, payload: list[dict[str, Any]]) -> None:
    write_json_file(entries_index_path(project_root), payload)


def validate_source_paths(project_root: Path, sources: list[str]) -> list[str]:
    normalized_sources: list[str] = []
    for raw_source in sources:
        source_path = Path(raw_source)
        if source_path.is_absolute():
            raise SystemExit("Error: source paths must be relative to the project root")
        resolved = (project_root / source_path).resolve()
        try:
            resolved.relative_to(project_root.resolve())
        except ValueError as exc:
            raise SystemExit(f"Error: source path escapes project root: {raw_source}") from exc
        if not resolved.exists():
            raise SystemExit(f"Error: missing source path: {raw_source}")
        normalized_sources.append(str(source_path))
    return normalized_sources


def format_candidate_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        f"# {candidate['title']}",
        "",
        f"- 候选ID: {candidate['id']}",
        f"- 类型: {candidate['kind']}",
        f"- 阶段: {candidate['stage']}",
        f"- 创建时间: {candidate['created_at']}",
        f"- 当前状态: {candidate['status']}",
    ]
    if candidate.get("tags"):
        lines.append(f"- 标签: {', '.join(candidate['tags'])}")
    if candidate.get("sources"):
        lines.append(f"- 来源: {', '.join(f'`{item}`' for item in candidate['sources'])}")
    lines.extend(["", "## 摘要", "", candidate["summary"]])
    if candidate.get("note"):
        lines.extend(["", "## 备注", "", candidate["note"]])
    return "\n".join(lines) + "\n"


def format_entry_markdown(entry: dict[str, Any]) -> str:
    lines = [
        f"# {entry['title']}",
        "",
        f"- 正式知识ID: {entry['id']}",
        f"- 来源候选ID: {entry['source_candidate_id']}",
        f"- 类型: {entry['kind']}",
        f"- 阶段: {entry['stage']}",
        f"- 收录时间: {entry['created_at']}",
    ]
    if entry.get("tags"):
        lines.append(f"- 标签: {', '.join(entry['tags'])}")
    if entry.get("sources"):
        lines.append(f"- 来源: {', '.join(f'`{item}`' for item in entry['sources'])}")
    lines.extend(["", "## 摘要", "", entry["summary"]])
    if entry.get("note"):
        lines.extend(["", "## 备注", "", entry["note"]])
    return "\n".join(lines) + "\n"


def ensure_candidate_by_id(candidates: list[dict[str, Any]], candidate_id: int) -> dict[str, Any]:
    for candidate in candidates:
        if int(candidate.get("id", 0)) == candidate_id:
            return candidate
    raise SystemExit(f"Error: missing candidate id: {candidate_id}")


def parse_review_action(raw_value: str) -> tuple[str, int | None]:
    cleaned = raw_value.strip()
    if cleaned in REVIEW_ACTIONS:
        return cleaned, None
    match = re.fullmatch(r"合并[:：]\s*(\d+)", cleaned)
    if match:
        return "合并", int(match.group(1))
    raise SystemExit(f"Error: invalid review action: {raw_value}")


def parse_review_file(review_path: Path) -> tuple[list[dict[str, Any]], str]:
    content = review_path.read_text(encoding="utf-8")
    marker = re.compile(r"^## 候选 (\d+)\s*$", re.MULTILINE)
    matches = list(marker.finditer(content))
    if not matches:
        raise SystemExit(f"Error: review file has no candidate sections: {review_path}")

    parsed: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        candidate_id = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[start:end]

        action_match = re.search(r"^- 处理[：:]\s*(.+)\s*$", block, re.MULTILINE)
        note_match = re.search(r"^- 备注[：:]\s*(.*)\s*$", block, re.MULTILINE)
        if not action_match:
            raise SystemExit(f"Error: missing action for candidate {candidate_id} in {review_path}")

        action, merge_target = parse_review_action(action_match.group(1))
        parsed.append(
            {
                "candidate_id": candidate_id,
                "action": action,
                "merge_target": merge_target,
                "note": note_match.group(1).strip() if note_match else "",
            }
        )

    return parsed, content


def command_init_state(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    ensure_knowledge_base(project_root)
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
    ensure_knowledge_base(project_root)
    state = read_state(args.project)
    missing = validate_project_files(project_root)
    candidates = read_candidates(project_root)
    entries = read_entries(project_root)

    print(f"Project: {args.project}")
    print(f"Mode: {state['mode']}")
    print(f"Current stage: {state['current_stage']} (step {STAGE_INDEX[state['current_stage']]})")
    print(f"Premise test passed: {'yes' if state.get('premise_test_passed') else 'no'}")
    print(f"Knowledge candidates: {len(candidates)}")
    print(f"Knowledge entries: {len(entries)}")
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
    ensure_knowledge_base(project_root)
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


def command_set_premise(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    ensure_knowledge_base(project_root)
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
    ensure_knowledge_base(project_root)
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


def command_capture(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    ensure_knowledge_base(project_root)
    state = read_state(args.project)
    stage = require_valid_stage(args.stage or state["current_stage"])
    kind = args.kind.lower()
    if kind not in KNOWLEDGE_KINDS:
        raise SystemExit(f"Error: unknown knowledge kind: {kind}")

    sources = validate_source_paths(project_root, args.source or [])
    candidates = read_candidates(project_root)
    candidate_id = next_numeric_id(candidates)
    filename = f"{candidate_id:03d}_{kind}_{slugify(args.title)}.md"
    relative_path = Path("knowledge") / "candidates" / filename
    absolute_path = project_root / relative_path

    tags = [tag.strip() for tag in (args.tag or []) if tag.strip()]
    summary = args.summary.strip()
    note = args.note.strip() if args.note else ""
    created_at = utc_now()

    candidate = {
        "id": candidate_id,
        "title": args.title,
        "kind": kind,
        "stage": stage,
        "summary": summary,
        "note": note,
        "tags": tags,
        "sources": sources,
        "path": str(relative_path),
        "created_at": created_at,
        "status": "待审",
        "review_history": [],
    }
    absolute_path.write_text(format_candidate_markdown(candidate), encoding="utf-8")
    candidates.append(candidate)
    write_candidates(project_root, candidates)

    append_history(
        state,
        "capture",
        stage,
        args.note or f"Captured candidate #{candidate_id}: {args.title}",
    )
    write_state(args.project, state)
    print(f"Captured candidate #{candidate_id}: {relative_path}")
    return 0


def command_review_create(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    ensure_knowledge_base(project_root)
    state = read_state(args.project)
    candidates = read_candidates(project_root)

    selected: list[dict[str, Any]] = []
    if args.id:
        requested_ids = {int(value) for value in args.id}
        for candidate_id in requested_ids:
            selected.append(ensure_candidate_by_id(candidates, candidate_id))
    else:
        for candidate in candidates:
            if candidate.get("status") in {"待审", "稍后"}:
                selected.append(candidate)

    selected = sorted(selected, key=lambda item: int(item["id"]))
    if not selected:
        raise SystemExit("Error: no candidate entries available for review")

    existing_reviews = sorted(reviews_dir(project_root).glob("*.md"))
    review_id = 1
    if existing_reviews:
        numeric_ids = []
        for path in existing_reviews:
            match = re.match(r"(\d+)_", path.name)
            if match:
                numeric_ids.append(int(match.group(1)))
        if numeric_ids:
            review_id = max(numeric_ids) + 1

    filename = f"{review_id:03d}_candidate-review.md"
    relative_path = Path("knowledge") / "reviews" / filename
    absolute_path = project_root / relative_path

    lines = [
        f"# 知识候选筛选 {review_id:03d}",
        "",
        "## 说明",
        "",
        "请把每条候选的 `处理` 改成以下中文动作之一：",
        "",
        "- `保留`",
        "- `丢弃`",
        "- `合并:<候选ID>`",
        "- `稍后`",
        "",
        "只改 `处理` 和 `备注` 这两行即可。",
        "",
    ]

    for candidate in selected:
        lines.extend(
            [
                f"## 候选 {candidate['id']}",
                "",
                f"- 标题: {candidate['title']}",
                f"- 类型: {candidate['kind']}",
                f"- 阶段: {candidate['stage']}",
                f"- 当前状态: {candidate['status']}",
            ]
        )
        if candidate.get("tags"):
            lines.append(f"- 标签: {', '.join(candidate['tags'])}")
        if candidate.get("sources"):
            lines.append(f"- 来源: {', '.join(candidate['sources'])}")
        lines.extend(
            [
                f"- 摘要: {candidate['summary']}",
                "",
                "### 审核",
                "- 处理: 稍后",
                "- 备注: ",
                "",
            ]
        )

    absolute_path.write_text("\n".join(lines), encoding="utf-8")
    append_history(state, "review_create", state["current_stage"], f"Created review doc: {relative_path}")
    write_state(args.project, state)
    print(f"Created review doc: {relative_path}")
    return 0


def command_review_apply(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    ensure_knowledge_base(project_root)
    state = read_state(args.project)

    review_path = project_root / args.review_path
    if not review_path.is_file():
        raise SystemExit(f"Error: missing review file: {review_path}")

    decisions, _ = parse_review_file(review_path)
    candidates = read_candidates(project_root)
    entries = read_entries(project_root)

    decision_map = {item["candidate_id"]: item for item in decisions}
    for item in decisions:
        if item["action"] == "合并":
            target_id = item["merge_target"]
            if target_id == item["candidate_id"]:
                raise SystemExit(f"Error: candidate {item['candidate_id']} cannot merge into itself")
            if target_id not in decision_map and not any(int(candidate["id"]) == target_id for candidate in candidates):
                raise SystemExit(f"Error: merge target candidate does not exist: {target_id}")

    promoted = 0
    for item in decisions:
        candidate = ensure_candidate_by_id(candidates, item["candidate_id"])
        action = item["action"]
        note = item["note"]
        history_entry = {
            "reviewed_at": utc_now(),
            "review_file": str(Path(args.review_path)),
            "action": action if action != "合并" else f"合并:{item['merge_target']}",
            "note": note,
        }
        candidate.setdefault("review_history", []).append(history_entry)

        if action == "保留":
            existing_entry = next(
                (entry for entry in entries if int(entry.get("source_candidate_id", 0)) == int(candidate["id"])),
                None,
            )
            if existing_entry is None:
                entry_id = next_numeric_id(entries)
                filename = f"{entry_id:03d}_{candidate['kind']}_{slugify(candidate['title'])}.md"
                relative_path = Path("knowledge") / "entries" / filename
                entry = {
                    "id": entry_id,
                    "source_candidate_id": candidate["id"],
                    "title": candidate["title"],
                    "kind": candidate["kind"],
                    "stage": candidate["stage"],
                    "summary": candidate["summary"],
                    "note": note or candidate.get("note", ""),
                    "tags": candidate.get("tags", []),
                    "sources": candidate.get("sources", []),
                    "path": str(relative_path),
                    "created_at": utc_now(),
                }
                (project_root / relative_path).write_text(format_entry_markdown(entry), encoding="utf-8")
                entries.append(entry)
                existing_entry = entry
                promoted += 1
            candidate["status"] = "已收录"
            candidate["entry_id"] = existing_entry["id"]
        elif action == "丢弃":
            candidate["status"] = "已丢弃"
        elif action == "稍后":
            candidate["status"] = "稍后"
        elif action == "合并":
            candidate["status"] = "已合并"
            candidate["merged_into"] = item["merge_target"]
        else:
            raise SystemExit(f"Error: unsupported action: {action}")

    write_candidates(project_root, candidates)
    write_entries(project_root, entries)
    append_history(
        state,
        "review_apply",
        state["current_stage"],
        f"Applied review doc: {args.review_path} | promoted={promoted}",
    )
    write_state(args.project, state)
    print(f"Applied review doc: {args.review_path}")
    print(f"Promoted to entries: {promoted}")
    return 0


def command_kb_list(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    ensure_knowledge_base(project_root)

    layer = args.layer
    print(f"Project: {args.project}")

    if layer in {"候选", "全部"}:
        candidates = sorted(read_candidates(project_root), key=lambda item: int(item["id"]), reverse=True)
        if args.limit:
            candidates = candidates[: args.limit]
        print(f"候选条目: {len(candidates)}")
        for item in candidates:
            print(
                f"  - #{item['id']} | {item['status']} | {item['kind']} | {item['stage']} | {item['title']} | {item['path']}"
            )

    if layer in {"正式", "全部"}:
        entries = sorted(read_entries(project_root), key=lambda item: int(item["id"]), reverse=True)
        if args.limit:
            entries = entries[: args.limit]
        print(f"正式条目: {len(entries)}")
        for item in entries:
            print(
                f"  - #{item['id']} | {item['kind']} | {item['stage']} | {item['title']} | {item['path']}"
            )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Guard project state transitions and preserve reusable knowledge."
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

    capture = subparsers.add_parser("capture", help="Capture a reusable idea or lesson into candidate knowledge")
    capture.add_argument("project")
    capture.add_argument("kind", choices=sorted(KNOWLEDGE_KINDS))
    capture.add_argument("title")
    capture.add_argument("--summary", required=True)
    capture.add_argument("--stage", choices=STAGES)
    capture.add_argument("--source", action="append")
    capture.add_argument("--tag", action="append")
    capture.add_argument("--note")
    capture.set_defaults(func=command_capture)

    review_create = subparsers.add_parser("review-create", help="Generate a Chinese review doc for candidates")
    review_create.add_argument("project")
    review_create.add_argument("--id", action="append", help="Candidate ID to include; repeatable")
    review_create.set_defaults(func=command_review_create)

    review_apply = subparsers.add_parser("review-apply", help="Apply decisions from a review doc")
    review_apply.add_argument("project")
    review_apply.add_argument("review_path", help="Path relative to the project root")
    review_apply.set_defaults(func=command_review_apply)

    kb_list = subparsers.add_parser("kb-list", help="List candidates and/or formal entries")
    kb_list.add_argument("project")
    kb_list.add_argument("--layer", choices=["候选", "正式", "全部"], default="全部")
    kb_list.add_argument("--limit", type=int)
    kb_list.set_defaults(func=command_kb_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
