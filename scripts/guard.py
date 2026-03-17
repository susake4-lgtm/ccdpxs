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
KNOWLEDGE_KINDS = {"idea", "lesson", "risk", "rejection", "rule", "fragment"}
REVIEW_ACTIONS = {"保留", "丢弃", "稍后"}
DEFAULT_STATE_VERSION = 5

# Stages at or before which the global knowledge base may be consulted.
# After KNOWLEDGE_READ_CUTOFF_STAGE, knowledge is write-only (output only, no reading).
KNOWLEDGE_READ_CUTOFF_STAGE = "structure"


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


# ---------------------------------------------------------------------------
# Global knowledge base (repo-level, shared across all projects)
# ---------------------------------------------------------------------------

def knowledge_root() -> Path:
    return repo_root() / "knowledge"


def candidates_dir() -> Path:
    return knowledge_root() / "candidates"


def candidates_index_path() -> Path:
    return candidates_dir() / "index.json"


def entries_dir() -> Path:
    return knowledge_root() / "entries"


def entries_index_path() -> Path:
    return entries_dir() / "index.json"


def reviews_dir() -> Path:
    return knowledge_root() / "reviews"


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


def ensure_knowledge_base() -> None:
    """Ensure the global (repo-level) knowledge base directories and index files exist."""
    root = knowledge_root()
    candidate_root = candidates_dir()
    entry_root = entries_dir()
    review_root = reviews_dir()

    root.mkdir(parents=True, exist_ok=True)
    candidate_root.mkdir(parents=True, exist_ok=True)
    entry_root.mkdir(parents=True, exist_ok=True)
    review_root.mkdir(parents=True, exist_ok=True)

    candidate_index = candidates_index_path()
    if not candidate_index.exists():
        write_json_file(candidate_index, [])

    entry_index = entries_index_path()
    if not entry_index.exists():
        write_json_file(entry_index, [])

    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# 全局知识库\n\n"
            "跨项目积累的创作规律、失败经验和可复用片段。\n\n"
            "## 三层结构\n\n"
            "1. `candidates/`：LLM 汇总输出的候选条目，允许粗糙。\n"
            "2. `reviews/`：筛选文档，用中文标记保留、丢弃、合并、稍后。\n"
            "3. `entries/`：正式知识库，只放用户确认过的高价值内容。\n\n"
            "## 调用规则\n\n"
            "- **02 Structure 及之前**：可读取 `entries/` 辅助方向判断。\n"
            "- **03 Outline 及之后**：只写入（capture），不读取，避免污染当前故事的内部一致性。\n\n"
            "## 来源\n\n"
            "知识来自各项目的 `00_Creative_Chat_Log.md`，由用户主动触发汇总后进入候选层。\n",
            encoding="utf-8",
        )


def load_index(index_path: Path, label: str) -> list[dict[str, Any]]:
    raw = read_json_file(index_path, [])
    if not isinstance(raw, list):
        raise SystemExit(f"Error: invalid {label} index type: {index_path}")
    return raw


def read_candidates() -> list[dict[str, Any]]:
    ensure_knowledge_base()
    return load_index(candidates_index_path(), "candidate")


def write_candidates(payload: list[dict[str, Any]]) -> None:
    write_json_file(candidates_index_path(), payload)


def read_entries() -> list[dict[str, Any]]:
    ensure_knowledge_base()
    return load_index(entries_index_path(), "entry")


def write_entries(payload: list[dict[str, Any]]) -> None:
    write_json_file(entries_index_path(), payload)


def validate_source_paths(project_root: Path, project_slug: str, sources: list[str]) -> list[str]:
    """Validate source paths (relative to project root) and return repo-relative forms."""
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
        # Store as repo-relative path for provenance clarity
        normalized_sources.append(f"output/{project_slug}/{source_path}")
    return normalized_sources


def format_candidate_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        f"# {candidate['title']}",
        "",
        f"- 候选ID: {candidate['id']}",
        f"- 类型: {candidate['kind']}",
        f"- 阶段: {candidate['stage']}",
        f"- 来源项目: {candidate.get('project_slug', '—')}",
        f"- 创建时间: {candidate['created_at']}",
        f"- 当前状态: {candidate['status']}",
    ]
    if candidate.get("tags"):
        lines.append(f"- 标签: {', '.join(candidate['tags'])}")
    if candidate.get("sources"):
        lines.append(f"- 来源文件: {', '.join(f'`{item}`' for item in candidate['sources'])}")
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
        f"- 来源项目: {entry.get('project_slug', '—')}",
        f"- 收录时间: {entry['created_at']}",
    ]
    if entry.get("tags"):
        lines.append(f"- 标签: {', '.join(entry['tags'])}")
    if entry.get("sources"):
        lines.append(f"- 来源文件: {', '.join(f'`{item}`' for item in entry['sources'])}")
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



def print_knowledge_hint(stage: str) -> None:
    cutoff_index = STAGE_INDEX[KNOWLEDGE_READ_CUTOFF_STAGE]
    stage_index = STAGE_INDEX[stage]
    if stage_index <= cutoff_index:
        print(f"[Knowledge] 当前阶段可读取全局知识库 knowledge/entries/")
    else:
        print(f"[Knowledge] 当前阶段只写入知识库，不读取（避免污染故事内部一致性）")


def command_init_state(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    ensure_knowledge_base()
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
    ensure_knowledge_base()
    state = read_state(args.project)
    missing = validate_project_files(project_root)
    candidates = read_candidates()
    entries = read_entries()

    current_stage = state["current_stage"]
    print(f"Project: {args.project}")
    print(f"Mode: {state['mode']}")
    print(f"Current stage: {current_stage} (step {STAGE_INDEX[current_stage]})")
    print(f"Killer test passed: {'yes' if state.get('killer_test_passed') else 'no'}"
          f" (attempts: {state.get('killer_test_attempts', 0)}/2)")
    print(f"Premise test passed: {'yes' if state.get('premise_test_passed') else 'no'}")
    print(f"Global knowledge candidates: {len(candidates)}")
    print(f"Global knowledge entries: {len(entries)}")
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


    print_knowledge_hint(current_stage)
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
    ensure_knowledge_base()
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

    print_knowledge_hint(target_stage)
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

    print_knowledge_hint(target_stage)
    return 0


def command_capture(args: argparse.Namespace) -> int:
    project_root = ensure_project_exists(args.project)
    ensure_knowledge_base()
    state = read_state(args.project)
    stage = require_valid_stage(args.stage or state["current_stage"])
    kind = args.kind.lower()
    if kind not in KNOWLEDGE_KINDS:
        raise SystemExit(f"Error: unknown knowledge kind: {kind}")

    sources = validate_source_paths(project_root, args.project, args.source or [])
    candidates = read_candidates()
    candidate_id = next_numeric_id(candidates)
    filename = f"{candidate_id:03d}_{kind}_{slugify(args.title)}.md"
    relative_path = Path("knowledge") / "candidates" / filename
    absolute_path = repo_root() / relative_path

    tags = [tag.strip() for tag in (args.tag or []) if tag.strip()]
    summary = args.summary.strip()
    note = args.note.strip() if args.note else ""
    created_at = utc_now()

    candidate = {
        "id": candidate_id,
        "title": args.title,
        "kind": kind,
        "stage": stage,
        "project_slug": args.project,
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
    write_candidates(candidates)

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
    ensure_knowledge_base()
    candidates = read_candidates()

    # Filter by project if specified
    pool = candidates
    if args.project:
        pool = [c for c in candidates if c.get("project_slug") == args.project]

    selected: list[dict[str, Any]] = []
    if args.id:
        requested_ids = {int(value) for value in args.id}
        for candidate_id in requested_ids:
            selected.append(ensure_candidate_by_id(pool, candidate_id))
    else:
        for candidate in pool:
            if candidate.get("status") in {"待审", "稍后"}:
                selected.append(candidate)

    selected = sorted(selected, key=lambda item: int(item["id"]))
    if not selected:
        raise SystemExit("Error: no candidate entries available for review")

    existing_reviews = sorted(reviews_dir().glob("*.md"))
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
    absolute_path = repo_root() / relative_path

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
                f"- 来源项目: {candidate.get('project_slug', '—')}",
                f"- 当前状态: {candidate['status']}",
            ]
        )
        if candidate.get("tags"):
            lines.append(f"- 标签: {', '.join(candidate['tags'])}")
        if candidate.get("sources"):
            lines.append(f"- 来源文件: {', '.join(candidate['sources'])}")
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

    if args.project:
        state = read_state(args.project)
        append_history(state, "review_create", state["current_stage"], f"Created review doc: {relative_path}")
        write_state(args.project, state)

    print(f"Created review doc: {relative_path}")
    return 0


def command_review_apply(args: argparse.Namespace) -> int:
    ensure_knowledge_base()

    review_path = repo_root() / args.review_path
    if not review_path.is_file():
        raise SystemExit(f"Error: missing review file: {review_path}")

    decisions, _ = parse_review_file(review_path)
    candidates = read_candidates()
    entries = read_entries()

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
                    "project_slug": candidate.get("project_slug", ""),
                    "summary": candidate["summary"],
                    "note": note or candidate.get("note", ""),
                    "tags": candidate.get("tags", []),
                    "sources": candidate.get("sources", []),
                    "path": str(relative_path),
                    "created_at": utc_now(),
                }
                (repo_root() / relative_path).write_text(format_entry_markdown(entry), encoding="utf-8")
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

    write_candidates(candidates)
    write_entries(entries)

    if args.project:
        state = read_state(args.project)
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
    ensure_knowledge_base()

    layer = args.layer
    project_filter = args.project or None
    label = f"project={project_filter}" if project_filter else "all projects"
    print(f"Global knowledge ({label})")

    if layer in {"候选", "全部"}:
        candidates = sorted(read_candidates(), key=lambda item: int(item["id"]), reverse=True)
        if project_filter:
            candidates = [c for c in candidates if c.get("project_slug") == project_filter]
        if args.limit:
            candidates = candidates[: args.limit]
        print(f"候选条目: {len(candidates)}")
        for item in candidates:
            proj = item.get("project_slug", "—")
            print(
                f"  - #{item['id']} | {item['status']} | {item['kind']} | {item['stage']} | [{proj}] {item['title']}"
            )

    if layer in {"正式", "全部"}:
        entries = sorted(read_entries(), key=lambda item: int(item["id"]), reverse=True)
        if project_filter:
            entries = [e for e in entries if e.get("project_slug") == project_filter]
        if args.limit:
            entries = entries[: args.limit]
        print(f"正式条目: {len(entries)}")
        for item in entries:
            proj = item.get("project_slug", "—")
            print(
                f"  - #{item['id']} | {item['kind']} | {item['stage']} | [{proj}] {item['title']}"
            )

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

    capture = subparsers.add_parser("capture", help="Capture a reusable idea or lesson into global candidate knowledge")
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
    review_create.add_argument("--project", help="Filter candidates by project slug (optional)")
    review_create.add_argument("--id", action="append", help="Candidate ID to include; repeatable")
    review_create.set_defaults(func=command_review_create)

    review_apply = subparsers.add_parser("review-apply", help="Apply decisions from a review doc")
    review_apply.add_argument("review_path", help="Path relative to the repo root (e.g. knowledge/reviews/001_candidate-review.md)")
    review_apply.add_argument("--project", help="Project to record history in (optional)")
    review_apply.set_defaults(func=command_review_apply)

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

    kb_list = subparsers.add_parser("kb-list", help="List global candidates and/or formal entries")
    kb_list.add_argument("--project", help="Filter by project slug (optional)")
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
