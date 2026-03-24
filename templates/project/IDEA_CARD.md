# IDEA_CARD

> 这是本项目的单一正式锚点。下游写作与审核都围绕同一张卡展开，不再直接把原始脑洞当正式输入。
>
> 统一流程可见为：
> `raw_idea -> classified -> ready / review_required / hold`
>
> 写作和审核结果不并入卡片主状态，统一写入下方结果备注区。
>
> 约束：
> - `target_platform` 由下游输入指定，不在这里自动判定
> - `card_id`、`target_platform`、`primary_motif`、`must_have`、`must_avoid` 视为不可擅改锚点
> - 本卡只承接上游归类结果与下游执行/审核钩子，不代替结构大纲或正文写作

## 卡片元信息

- card_id:
- status: raw_idea / classified / ready / review_required / hold
- target_platform:
- lane:
- confidence_level: high / medium / low
- rule_refs:
- source_idea_raw:

## raw_idea / classified 摘要

- raw_idea_summary:
- classified_summary:
- primary_motif:
- secondary_motif:
- core_conflict:

## premise / must_have / must_avoid

- one_line_hook:
- relationship_frame:
- plot_mechanism:
- emotion_promise:
- must_have:
- must_avoid:

## 角色与冲突最小集

- roles:
- conflict_minset:

## 平台与母题锚点

- 继承上方锚点：`target_platform` / `lane` / `primary_motif` / `secondary_motif`
- background:
- mechanism_variant:
- emotion_variant:
- 标题方向:
- 开篇方向:
- 文风方向:
- 结构方向:

## ready / review_required / hold

- ready_check:
- review_required_reason:
- hold_reason:
- risk_flags:
- fallback_action:

## writing / review result hooks

- 写作摘要:
- 审核关注点:
- 通过备注:
- 返工备注:
- 拒绝备注:
- 暂停备注:

## rework / downgrade

- rework_round:
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
- `status` 只表示卡片准入层状态，不承载写作/审核结果。
- 写作/审核的通过、返工、拒绝、暂停，只能记在结果备注区。
- 若卡片需要改变主母题、平台或核心边界，应回到上游重新判定，不在本卡内硬修。
