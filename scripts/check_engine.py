"""
检查引擎 — 检查逻辑、报告生成、状态集成。

核心职责：
- 初始化/管理检查会话
- 提交检查结果（单条 & 批量）
- 生成检查报告（stdout + md 文件双写）
- 计算聚合评分
- 为 guard.py advance 提供阻塞判定
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from check_defs import (
    KILLER_TEST_THRESHOLDS,
    SCENE_PT_THRESHOLDS,
    get_check_by_id,
    get_checks_for_stage,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# 会话管理
# ---------------------------------------------------------------------------

def init_check_session(state: dict[str, Any], stage: str) -> dict[str, Any]:
    """创建检查会话（幂等）。返回该 stage 的检查会话 dict。"""
    checks = state.setdefault("checks", {})
    if stage in checks:
        return checks[stage]
    session = {
        "session_started": _utc_now(),
        "results": {},
    }
    checks[stage] = session
    return session


def init_chapter_check_session(state: dict[str, Any], chapter_num: str) -> dict[str, Any]:
    """为 Expansion 单章初始化检查会话（幂等）。"""
    checks = state.setdefault("checks", {})
    expansion = checks.setdefault("expansion", {
        "session_started": _utc_now(),
        "results": {},
    })
    chapters = expansion.setdefault("chapters", {})
    key = str(chapter_num)
    if key in chapters:
        return chapters[key]
    session = {
        "session_started": _utc_now(),
        "results": {},
    }
    chapters[key] = session
    return session


# ---------------------------------------------------------------------------
# 提交检查结果
# ---------------------------------------------------------------------------

def submit_check_result(
    state: dict[str, Any],
    stage: str,
    check_id: str,
    result: str,
    score: int | None = None,
    note: str = "",
    *,
    chapter_num: str | None = None,
) -> str:
    """提交单条检查结果。返回确认消息。"""
    check_def = get_check_by_id(check_id)
    if check_def is None:
        return f"Error: unknown check_id: {check_id}"
    if check_def["stage"] != stage and not (stage == "expansion" and check_def["stage"] == "expansion"):
        return f"Error: check {check_id} belongs to stage {check_def['stage']}, not {stage}"
    if result not in ("pass", "fail", "skip"):
        return f"Error: result must be pass/fail/skip, got: {result}"
    if check_def["result_type"] == "scored" and result != "skip":
        if score is None:
            return f"Error: scored check {check_id} requires --score"
        lo, hi = check_def["score_range"]
        if not (lo <= score <= hi):
            return f"Error: score must be {lo}-{hi}, got: {score}"

    # 获取对应的 results dict
    if chapter_num is not None:
        session = init_chapter_check_session(state, chapter_num)
    else:
        session = init_check_session(state, stage)

    session["results"][check_id] = {
        "result": result,
        "score": score,
        "note": note,
        "timestamp": _utc_now(),
        "skipped_reason": note if result == "skip" else None,
    }
    return f"OK: {check_id} = {result}" + (f" (score={score})" if score is not None else "")


def submit_checks_batch(
    state: dict[str, Any],
    stage: str,
    items: list[dict[str, Any]],
    *,
    chapter_num: str | None = None,
) -> list[str]:
    """批量提交检查结果。返回每条的确认消息。"""
    messages: list[str] = []
    for item in items:
        msg = submit_check_result(
            state,
            stage,
            item["check_id"],
            item["result"],
            item.get("score"),
            item.get("note", ""),
            chapter_num=chapter_num,
        )
        messages.append(msg)
    return messages


# ---------------------------------------------------------------------------
# 跳过检查
# ---------------------------------------------------------------------------

def skip_check(
    state: dict[str, Any],
    stage: str,
    check_id: str,
    reason: str,
    *,
    chapter_num: str | None = None,
) -> str:
    """用户确认跳过某条检查（带原因）。"""
    return submit_check_result(state, stage, check_id, "skip", note=reason, chapter_num=chapter_num)


# ---------------------------------------------------------------------------
# 查看状态
# ---------------------------------------------------------------------------

def get_check_status(state: dict[str, Any], stage: str, *, chapter_num: str | None = None) -> dict[str, Any]:
    """返回完成度摘要。"""
    checks_def = get_checks_for_stage(stage)
    total = len(checks_def)

    if chapter_num is not None:
        results = (
            state.get("checks", {})
            .get("expansion", {})
            .get("chapters", {})
            .get(str(chapter_num), {})
            .get("results", {})
        )
    else:
        results = state.get("checks", {}).get(stage, {}).get("results", {})

    done = 0
    passed = 0
    failed = 0
    skipped = 0
    pending_ids: list[str] = []

    for check_def in checks_def:
        cid = check_def["id"]
        if cid in results:
            done += 1
            r = results[cid]["result"]
            if r == "pass":
                passed += 1
            elif r == "fail":
                failed += 1
            elif r == "skip":
                skipped += 1
        else:
            pending_ids.append(cid)

    return {
        "stage": stage,
        "chapter_num": chapter_num,
        "total": total,
        "done": done,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pending": len(pending_ids),
        "pending_ids": pending_ids,
        "complete": done == total,
    }


def all_checks_complete(state: dict[str, Any], stage: str, *, chapter_num: str | None = None) -> bool:
    """所有必填项是否已填（pass/fail/skip 都算填了）。"""
    status = get_check_status(state, stage, chapter_num=chapter_num)
    return status["complete"]


# ---------------------------------------------------------------------------
# 生成检查模板（供 Claude 填写）
# ---------------------------------------------------------------------------

def generate_check_template(stage: str) -> str:
    """生成 Claude 填写的检查模板文本。"""
    checks = get_checks_for_stage(stage)
    if not checks:
        return f"No checks defined for stage: {stage}"

    lines = [
        f"# 压力测试检查 — {stage}",
        f"共 {len(checks)} 项检查",
        "",
    ]

    for i, c in enumerate(checks, 1):
        category_label = "原有" if c["category"] == "original" else "盐选适配"
        score_hint = ""
        if c["result_type"] == "scored":
            lo, hi = c["score_range"]
            score_hint = f" [评分 {lo}-{hi}]"
        lines.append(f"## {i}. [{c['id']}] {c['description']}")
        lines.append(f"- 类别: {category_label}")
        lines.append(f"- 来源: {c['source_ref']}")
        lines.append(f"- 不通过: {c['fail_action']}")
        lines.append(f"- 类型: {c['result_type']}{score_hint}")
        lines.append(f"- 结果: ___  (pass / fail / skip)")
        if c["result_type"] == "scored":
            lines.append(f"- 评分: ___")
        lines.append(f"- 备注: ")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 计算聚合评分
# ---------------------------------------------------------------------------

def compute_aggregate_score(state: dict[str, Any], stage: str) -> dict[str, Any] | None:
    """计算评分型阶段的聚合分数。仅对 killer_test 和 scene_pressure_test 有意义。"""
    results = state.get("checks", {}).get(stage, {}).get("results", {})
    checks = get_checks_for_stage(stage)
    scored_checks = [c for c in checks if c["result_type"] == "scored"]

    if not scored_checks:
        return None

    total_score = 0
    max_score = 0
    scored_items: list[dict[str, Any]] = []

    for c in scored_checks:
        lo, hi = c["score_range"]
        max_score += hi
        r = results.get(c["id"])
        if r and r.get("score") is not None:
            total_score += r["score"]
            scored_items.append({"id": c["id"], "score": r["score"]})
        else:
            scored_items.append({"id": c["id"], "score": None})

    # 选择阈值
    thresholds = None
    if stage == "killer_test":
        thresholds = KILLER_TEST_THRESHOLDS
    elif stage == "scene_pressure_test":
        thresholds = SCENE_PT_THRESHOLDS

    level = None
    if thresholds:
        for label, (lo, hi) in thresholds.items():
            if lo <= total_score <= hi:
                level = label
                break

    return {
        "total_score": total_score,
        "max_score": max_score,
        "level": level,
        "thresholds": thresholds,
        "items": scored_items,
    }


# ---------------------------------------------------------------------------
# 生成检查报告（双写 stdout + md）
# ---------------------------------------------------------------------------

def generate_check_report(
    state: dict[str, Any],
    stage: str,
    project_root: Path,
    *,
    chapter_num: str | None = None,
) -> str:
    """生成报告文本并写入 md 文件。返回报告文本。"""
    status = get_check_status(state, stage, chapter_num=chapter_num)
    checks = get_checks_for_stage(stage)

    if chapter_num is not None:
        results = (
            state.get("checks", {})
            .get("expansion", {})
            .get("chapters", {})
            .get(str(chapter_num), {})
            .get("results", {})
        )
    else:
        results = state.get("checks", {}).get(stage, {}).get("results", {})

    lines = []

    if chapter_num is not None:
        lines.append(f"# 压力测试报告 — expansion 第 {chapter_num} 章")
    else:
        lines.append(f"# 压力测试报告 — {stage}")

    lines.append(f"生成时间: {_utc_now()}")
    lines.append(f"完成度: {status['done']}/{status['total']}")
    lines.append(f"通过: {status['passed']} | 未通过: {status['failed']} | 跳过: {status['skipped']} | 待填: {status['pending']}")
    lines.append("")

    # 聚合评分
    if chapter_num is None:
        agg = compute_aggregate_score(state, stage)
        if agg:
            lines.append(f"## 聚合评分: {agg['total_score']}/{agg['max_score']}")
            if agg["level"]:
                lines.append(f"判定: {agg['level']}")
            lines.append("")

    # 逐条结果
    lines.append("## 逐条结果")
    lines.append("")

    for c in checks:
        cid = c["id"]
        r = results.get(cid)
        category_label = "原有" if c["category"] == "original" else "盐选适配"

        if r:
            result_str = r["result"]
            if r.get("score") is not None:
                result_str += f" (score={r['score']})"
            note = r.get("note", "")
            skip_reason = r.get("skipped_reason", "")
            status_mark = "PASS" if r["result"] == "pass" else ("SKIP" if r["result"] == "skip" else "FAIL")
        else:
            result_str = "—"
            note = ""
            skip_reason = ""
            status_mark = "PENDING"

        lines.append(f"### [{status_mark}] {cid}: {c['description']}")
        lines.append(f"- 类别: {category_label} | 来源: {c['source_ref']}")
        lines.append(f"- 结果: {result_str}")
        if note:
            lines.append(f"- 备注: {note}")
        if skip_reason:
            lines.append(f"- 跳过原因: {skip_reason}")
        if r and r["result"] == "fail":
            lines.append(f"- 修复方向: {c['fail_action']}")
        lines.append("")

    report_text = "\n".join(lines)

    # 写入 md 文件
    from guard import STAGE_LOG_DIRS
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    if chapter_num is not None:
        log_dir = project_root / STAGE_LOG_DIRS["expansion"]
        filename = f"check_report_chapter_{chapter_num}_{timestamp}.md"
    else:
        log_dir = project_root / STAGE_LOG_DIRS.get(stage, f"stage_logs/{stage}")
        filename = f"check_report_{stage}_{timestamp}.md"

    log_dir.mkdir(parents=True, exist_ok=True)
    report_path = log_dir / filename
    report_path.write_text(report_text, encoding="utf-8")

    return report_text


# ---------------------------------------------------------------------------
# Blocker 集成
# ---------------------------------------------------------------------------

def check_blockers_for_advance(state: dict[str, Any], current_stage: str) -> list[str]:
    """返回阻塞消息列表。仅当该阶段有检查定义且检查会话已启动时才阻塞。

    expansion 阶段特殊处理：不自动阻塞章内推进。
    只在 expansion → review 时检查：所有跑过检测的章节是否都通过了。
    """
    blockers: list[str] = []

    # expansion 阶段：不阻塞章内推进，只在进 review 时检查
    if current_stage == "expansion":
        return _check_expansion_blockers(state)

    checks_def = get_checks_for_stage(current_stage)
    if not checks_def:
        return blockers

    # 检查会话是否已启动
    session = state.get("checks", {}).get(current_stage)
    if session is None:
        # 旧项目（未启动检查会话的）不受影响
        return blockers

    status = get_check_status(state, current_stage)
    if not status["complete"]:
        pending = status["pending"]
        blockers.append(
            f"压力测试未完成: {current_stage} 还有 {pending} 项检查未填写 "
            f"({status['done']}/{status['total']} done)"
        )

    # 评分型阶段检查聚合分数
    agg = compute_aggregate_score(state, current_stage)
    if agg and agg["level"] == "fail":
        blockers.append(
            f"压力测试聚合评分不通过: {current_stage} "
            f"总分 {agg['total_score']}/{agg['max_score']} (判定: fail)"
        )

    return blockers


def _check_expansion_blockers(state: dict[str, Any]) -> list[str]:
    """expansion → review 时检查章节检测情况。

    规则：
    - 没有任何章节跑过检测 → 阻塞（至少得跑一章）
    - 跑过检测的章节中有 fail 且未 skip → 阻塞
    - 跑过检测的章节全部 pass/skip → 放行
    """
    blockers: list[str] = []
    chapters = state.get("checks", {}).get("expansion", {}).get("chapters", {})

    if not chapters:
        # 没跑过任何章节检测 — 但也可能是旧项目，不强制阻塞
        # 只在 expansion 检查会话已存在时才阻塞
        if "expansion" in state.get("checks", {}):
            blockers.append("扩写阶段未对任何章节运行压力测试。至少需要检测 1 章。")
        return blockers

    failed_chapters: list[str] = []
    incomplete_chapters: list[str] = []

    for ch_num, session in chapters.items():
        results = session.get("results", {})
        checks_def = get_checks_for_stage("expansion")

        done = 0
        has_fail = False
        for c in checks_def:
            r = results.get(c["id"])
            if r:
                done += 1
                if r["result"] == "fail":
                    has_fail = True

        if done < len(checks_def):
            incomplete_chapters.append(ch_num)
        elif has_fail:
            failed_chapters.append(ch_num)

    if incomplete_chapters:
        blockers.append(
            f"扩写章节检测未完成: 第 {', '.join(sorted(incomplete_chapters))} 章还有未填写的检查项"
        )
    if failed_chapters:
        blockers.append(
            f"扩写章节检测未通过: 第 {', '.join(sorted(failed_chapters))} 章存在 fail 项（需修复或 skip）"
        )

    return blockers
