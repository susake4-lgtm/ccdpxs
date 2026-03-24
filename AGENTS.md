# AGENTS.md

本仓库是一个面向 Codex 的**阶段式短篇小说协作系统**。

它不追求一口气自动写完整本，而是把创作拆成可停顿、可确认、可修正、可回退、可留痕的阶段，让用户保留主导权，Agent 负责协助推进、诊断、整理和扩写。

本文件现在就是仓库的正式阶段入口。它负责三件事：

- 当前阶段入口与仓库权威链的关系
- `IDEA_CARD` 的正式锚点口径
- 上游替换后哪些内容只能停在 docs-only 参考层

具体分工如下：`AGENTS.md` 负责阶段入口与默认工作方式，`AI_WRITING_SOP.md` 负责流程推进，`PROJECT_RULES.md` 负责硬规则与文件纪律，`CONTENT_FRAMEWORK*.md` 负责内容标准。

## 当前入口关系

- `AGENTS.md` 现在是 `guard.py context` 所对应的正式阶段入口文件
- `CLAUDE.md` 只保留为兼容壳，避免旧入口直接失效
- 阶段实际读取顺序，以 `guard.py context` 输出为准

## 接口层补充契约

统一接口对象是 `IDEA_CARD`。正式写作与审核都围绕同一张卡展开，不再直接把原始脑洞当正式执行输入。

卡片 / 准入侧状态只包含：

```text
raw_idea -> classified -> ready / review_required / hold
```

阶段 / 草稿处理结果另行记录：

```text
writing / review -> pass / rework / reject / hold
```

补充约束如下：

- 进入 Structure 及其后续正式执行阶段前，`IDEA_CARD.status` 应为 `ready`，而不是仅仅“不是 hold”
- `review_required` 表示卡片仍待人工确认或补齐，不能当成已准入
- 不可擅改锚点至少包括：`card_id`、`target_platform`、`primary_motif`、`must_have`、`must_avoid`
- `target_platform` 由下游或用户输入指定，不自动判定
- `EXPANSION_CONTEXT.md` 只负责继承和场景实际状态记录，不重新定义平台规则、母题规则或结构规则
- `event-arc`、`reverse-outline`、`V2` 治理思路等都只作 docs-only 参考层，不上升为正式输入锚点或硬门禁

## 默认读取与启动顺序

当前仓库的实际启动顺序应以脚本输出为准：

1. `python3 scripts/guard.py status <project>` 确认当前阶段
2. `python3 scripts/guard.py context <current-stage>` 确认当前阶段需要读取的文档
3. 先按 `AGENTS.md` 和 `guard.py context` 的输出进入当前阶段
4. 若看到旧入口 `CLAUDE.md`，转到 `AGENTS.md` 继续，不再把 `CLAUDE.md` 当权威源
5. 继续旧项目时，再读该项目当前阶段总文件和最近的 `stage_logs/`

需要确认仓库定位或目录约定时，查阅 `README.md`。

## 权威来源

- **阶段入口与默认工作方式**：`AGENTS.md`
- **流程推进**：`AI_WRITING_SOP.md`
- **硬规则与停止条件**：`PROJECT_RULES.md`
- **内容写法与阅读体验**：`CONTENT_FRAMEWORK.md` + `CONTENT_FRAMEWORK_structure.md` + `CONTENT_FRAMEWORK_writing.md`
- **仓库定位与命令**：`README.md`

如果文档之间出现口径差异，按上面的职责边界解释，不自行混写或扩大范围。

模板层补充：

- `templates/project/IDEA_CARD.md` 是卡片模板，不是独立权威层
- `templates/project/EXPANSION_CONTEXT.md` 是扩写继承模板，不是独立权威层

## 工作补充

- 默认从仓库根目录启动，不把 `output/` 当成规则仓库根目录
- 每次只解决一个层级的问题，不跳过阶段直接长篇扩写
- 卡片一旦存在，后续阶段都以 `IDEA_CARD` 为正式输入，不回退到原始脑洞直推
- 进入扩写前，从 `02_Structure.md` 和 `03_Outline.md` 继承数据到 `EXPANSION_CONTEXT.md`
- 当文档描述与 `project_state.json` 冲突时，先修状态或说明冲突，不口头假装已推进

## 确认门槛

完整确认门槛和可接受信号以 `PROJECT_RULES.md` §2 及 `python3 scripts/guard.py rules` 为准。

## guard.py 集成

常用命令仍以 `scripts/guard.py` 为主：

- `guard.py status <project>`
- `guard.py context <stage>`
- `guard.py advance <project> <stage>`
- `guard.py confirm <project>`
- `guard.py rewind <project> <target>`
- `guard.py rules`
- `guard.py stage-info <stage>`

其余压力测试命令用法见 `guard.py <command> --help`。

## 文件纪律

文件纪律、日志规则、扩写版本管理和留痕规则以 `PROJECT_RULES.md` §4-§5 为准。

## 停止条件

停止条件与 `hold / rework / reject` 的边界，以 `PROJECT_RULES.md` §3 和 §6 为准。

## 框架调试模式

如果用户说“优化流程”而不是“写故事”，沿用本文件的框架调试模式，并补充一条仓库级约束：

- 研究型新增默认先 docs 化，不先改 `guard.py`、`check_defs.py`、`check_engine.py`

## 发散模式

如果用户说“我想聊聊这个脑洞”或处于 Intake / Idea Fission 阶段，沿用本文件与阶段文档的发散模式，不再回看 `CLAUDE.md`。

## 用户标注约定

用户在文稿中用 `##原文##意见##` 标注时，视为对该位置的直接修改意见或提问。具体解释与响应方式沿用仓库当前扩写规则。

## 扩写修改流程

扩写修改仍沿用现有版本流转：

- 初稿：`scene-xx.md`
- 修改版：`scene-xx-v1.md`、`scene-xx-v2.md` ...
- 终稿：`scene-xx-终稿.md`

只改有标注的地方，不覆盖旧版本；详细留痕格式和流转规则沿用 `PROJECT_RULES.md` 与当前扩写模板。

## 其余协作边界

操作边界、默认不做事项、必须暂停的情况和输出风格，沿用本文件与 `PROJECT_RULES.md` 的现有约定，不再回看 `CLAUDE.md`。
