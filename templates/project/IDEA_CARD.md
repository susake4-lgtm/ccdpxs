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
- primary_motif:
- secondary_motif:

## raw_idea / classified 摘要

> 这里只保留足够让下游识别任务的最小摘要，不展开额外分析字段。

- core_conflict:
- relationship_frame:

## premise / must_have / must_avoid

> 这里只保留当前流程会实际消费的核心承诺。

- plot_mechanism:
- emotion_promise:
- must_have:
- must_avoid:

## admission / risk

> 这里只记录准入判断，不扩成更大的数据模型。

- review_required_reason:
- hold_reason:
- risk_flags:
- fallback_action:

## writing / review hooks

> 只保留一个 `review_focus` 入口和一个结果备注位。

- review_focus:
- result_note:

## rework / downgrade

> 只保留当前能用的最小返工入口。

- blocking_issues:
- must_fix:
- must_keep:
- stop_condition:

## 不可擅改锚点说明

- `card_id` 只用于唯一识别这张卡，不能在返工或降级时替换。
- `target_platform` 必须保持为下游/用户指定值，不能在卡内自动改写。
- `primary_motif` 是主发动机，不能被标题、背景或机制变体覆盖。
- `must_have` 和 `must_avoid` 是执行边界，写作和审核都必须沿用。
- `status` 只表示卡片准入层状态，不承载写作/审核结果。
- 写作/审核的通过、返工、拒绝、暂停，只能记在结果备注区。
- 若卡片需要改变主母题、平台或核心边界，应回到上游重新判定，不在本卡内硬修。
