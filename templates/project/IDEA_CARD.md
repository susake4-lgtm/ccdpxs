# IDEA_CARD

> 这是本项目的单一正式锚点。下游写作与审核都围绕同一张卡展开，不再直接把原始脑洞当正式输入。
>
> 统一流程可见为：
> `raw_idea -> classified -> ready / review_required / hold -> writing / review -> pass / rework / reject / hold`
>
> 约束：
> - `target_platform` 由下游输入指定，不在这里自动判定
> - `card_id`、`target_platform`、`primary_motif`、`must_have`、`must_avoid` 视为不可擅改锚点
> - 本卡只承接上游归类结果与下游执行/审核钩子，不代替结构大纲或正文写作

## 卡片元信息

- card_id:
- version: v1.1
- status: raw_idea / classified / ready / review_required / hold / writing / review / pass / rework / reject
- target_platform:
- lane:
- confidence_level: high / medium / low
- idea_status: recommended / tentative / manual_review
- rule_refs:
- source_idea_raw:
- admission_note:

## raw_idea / classified 摘要

- raw_idea_summary:
- classified_summary:
- primary_motif_id:
- secondary_motif_id:
- primary_motif:
- secondary_motif:
- core_conflict:

## 平台与母题锚点

- target_platform:
- primary_motif:
- secondary_motif:
- lane:
- background:
- mechanism_variant:
- emotion_variant:
- title_direction:
- opening_direction:
- style_direction:
- structure_direction:

## premise / must_have / must_avoid

- one_line_hook:
- premise:
- relationship_frame:
- plot_mechanism:
- emotion_promise:
- must_have:
- must_avoid:
- review_focus:

## 角色与冲突最小集

- roles:
- conflict_minset:
- key_opponent:
- key_relationship:
- key_resource_or_order:
- first_breakpoint:

## ready / review_required / hold

- ready_check:
- review_required_reason:
- hold_reason:
- risk_flags:
- fallback_action:
- gating_note:

## writing / review result hooks

- writing_brief:
- review_focus:
- pass_criteria:
- rework_focus:
- reject_reason:
- hold_reason:

## rework package / downgrade notes

- rework_round:
- draft_id:
- blocking_issues:
- must_fix:
- must_keep:
- stop_condition:
- downgrade_notes:
- revision_instructions:

## 不可擅改锚点说明

- `card_id` 只用于唯一识别这张卡，不能在返工或降级时替换。
- `target_platform` 必须保持为下游/用户指定值，不能在卡内自动改写。
- `primary_motif` 是主发动机，不能被标题、背景或机制变体覆盖。
- `must_have` 和 `must_avoid` 是执行边界，写作和审核都必须沿用。
- 若卡片需要改变主母题、平台或核心边界，应回到上游重新判定，不在本卡内硬修。

