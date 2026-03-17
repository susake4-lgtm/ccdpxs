# AI 协作写作标准作业程序（Claude Code 版）

本文件只定义工作流本身：从原始脑洞到正式扩写，阶段如何推进、每阶段产出什么、什么时候进入下一阶段。

硬规则见 `PROJECT_RULES.md`。
内容写法见 `CONTENT_FRAMEWORK.md`（核心）+ `CONTENT_FRAMEWORK_structure.md`（结构阶段起）+ `CONTENT_FRAMEWORK_writing.md`（Prototype 阶段起）。

## 总体流程

```text
原始脑洞
→ 输入收集
→ Killer Test（脑洞粗筛）
→ 前提因果校验
→ 脑洞裂变
→ 方向评估
→ 结构方案（含情绪曲线）
→ 详细大纲
→ Scene Pressure Test（场景压力测试）
→ Prototype
→ 场景化扩写
→ 结构与读感复核
```

默认采用阶段式对话推进，而不是一次性自动生成到底。

## 统一产物模型

每个项目默认放在 `output/<project>/`，采用"双层产物模型"：

1. 阶段总文件：保存当前阶段最新版本，便于直接阅读
2. 阶段单轮归档：保存每次推进的独立 md，便于回溯
3. 状态文件：保存当前阶段、确认状态、前提校验结果和回退历史

推荐目录：

```text
output/<project>/
├─ PROJECT_INFO.md
├─ project_state.json
├─ 00_Brainstorm.md
├─ 00_Creative_Chat_Log.md    ← 强制追加，版权留痕
├─ 01_Evaluation_Log.md
├─ 02_Structure.md
├─ 03_Outline.md
├─ 04_Prototype.md
├─ chapters/
├─ 00_Killer_Test.md
└─ stage_logs/
   ├─ 00_intake/
   ├─ 00_killer-test/
   ├─ 01_idea-fission/
   ├─ 02_evaluation/
   ├─ 03_structure/
   ├─ 04_outline/
   ├─ 04_scene-pressure-test/
   ├─ 05_prototype/
   ├─ 06_expansion/
   └─ 07_review/
```

## 阶段 0：输入收集（Intake）

目标：
先说清这次写作的边界，避免后续跑偏。

输入：
- 原始脑洞、场景、标题感、情绪目标中的任一项
- 如果有的话：平台、字数区间、题材偏好、禁区

产出：
- 一份简短任务定义
- 已知约束与待澄清问题
- `stage_logs/00_intake/` 单轮归档

退出条件：`guard.py stage-info intake`

## 阶段 0.3：Killer Test（脑洞粗筛）

用 4 个问题快速判断脑洞是否值得继续投入。详细检查项见 `check_defs.py`。

四个核心问题：故事还是点子？冲突天然还是硬造？展开是否能打？是否靠高级感伪装？

决策：0-3 分暂缓，4-5 分可保留需重写核心，6-8 分进入前提因果校验。每个脑洞最多重写 2 次。

产出：`00_Killer_Test.md` + `stage_logs/00_killer-test/` 单轮归档

退出条件：`guard.py stage-info killer_test`

## 阶段 0.5：前提因果校验（Premise Pressure Test）

目标：
在开始裂变、包装和优化之前，先确认前提因果链最低限度是顺的。

默认五问：

1. 谁想达成什么
2. 为什么非要这么做
3. 为什么不能用更简单的办法
4. 相关人为什么会配合
5. 主角为什么不能直接离开、报警或求助

产出：
- 一份简短前提校验结论
- 当前最大的逻辑断点
- 是否值得继续裂变
- 归档到 `stage_logs/00_intake/`

退出条件：`guard.py stage-info premise_test`

## 阶段 1：脑洞裂变（Idea Fission）

目标：
把一个原始想法裂变成多个可执行方向，测试上限与可写性。

动作：
- 至少裂变出 3 个方向，通常 3 到 5 个
- 每个方向都说明：
  - 核心卖点
  - 情绪价值
  - 执行风险
  - 平台适配
  - 逻辑发动机
  - 人物发动机
  - 最容易失真的点

产出：
- `00_Brainstorm.md`
- `stage_logs/01_idea-fission/` 单轮归档
- 推荐方向与推荐理由

退出条件：`guard.py stage-info idea_fission`

## 阶段 2：方向评估（Evaluation）

目标：
判断当前方向是否值得继续做结构与正文。

动作：
- 评估吸睛度、冲突张力、情绪价值、执行风险
- 判断是否容易写成便利型推进、工具人角色、提纲 prose
- 如果方向尚未稳定，继续收缩，不进入结构

产出：
- `01_Evaluation_Log.md`
- `stage_logs/02_evaluation/` 单轮归档
- 当前轮结论：继续、回改、暂停

退出条件：`guard.py stage-info evaluation`

## 阶段 3：结构方案（Structure）

目标：
先搭"故事骨架"，不急着写长文。

动作：
- 明确标题方向、核心冲突、开篇爆点、30% 卡点、中段升级、终局回收
- 检查大转折的触发点
- 检查是人物选择推动局势，还是作者安排推动局势
- 设计情绪曲线（Emotional Arc）：定义 5 个情绪节点（E1 初始→E2 扰动→E3 升级→E4 峰值→E5 余味）

产出：
- `02_Structure.md`（含情绪曲线、人物行为模式、核心 motif/设定清单）
- `stage_logs/03_structure/` 单轮归档

退出条件：`guard.py stage-info structure`

## 阶段 4：详细大纲（Outline）

目标：
把结构方案拆成可写的章节或场景推进单元。

动作：
- 梳理人物关系和关键动机
- 拆分章节或场景节拍
- 标明每段承担的功能：推进冲突、释放爽点、揭露信息、制造钩子
- 标出最容易写空、写成概述的地方

产出：
- `03_Outline.md`（含每场景时间线、情绪位置入/出、认知差追踪表）
- `stage_logs/04_outline/` 单轮归档

退出条件：`guard.py stage-info outline`

## 阶段 4.5：Scene Pressure Test（场景压力测试）

对大纲中关键场景做压力测试。优先测试开头、30% 卡点、高潮、结尾 4 个节点。详细维度和评分规则见 `check_defs.py`。

五个维度：冲突强度、代价感、信息变化、主角决策、结尾钩子。满分 10 分。

决策：0-3 分回修，4-6 分标风险后可尝试，7-10 分可直接扩写。

产出：`stage_logs/04_scene-pressure-test/` 单轮归档

退出条件：`guard.py stage-info scene_pressure_test`

## 阶段 5：Prototype

目标：
先写一个简版故事，验证节奏、情绪、人物和反转是否成立。

动作：
- 用较短篇幅跑通主线
- 重点检查是否像故事，而不是像剧情摘要
- 找出一进正文最容易写空的段落

产出：
- `04_Prototype.md`
- `stage_logs/05_prototype/` 单轮归档

退出条件：`guard.py stage-info prototype`

## 阶段 6：场景化扩写（Expansion）

目标：
把已经确认的内容扩成真正能读的场景化正文。

动作：
- **扩写前必须从 02_Structure.md 和 03_Outline.md 继承数据到 `EXPANSION_CONTEXT.md` 参照表**，扩写时只补前场景衔接，每场景更新实际状态
- 每次只扩写一个小单元
- 明确本轮目标是推进局势、抬高代价、落情绪，还是回收前文
- 每次扩写后更新参照表中的"扩写后实际状态"
- 每次扩写后停下，等待用户决定继续、修改或回退

产出：
- `stage_logs/06_expansion/` 单轮归档
- 按需要同步到 `chapters/` 下的章节总文件

退出条件：`guard.py stage-info expansion`

## 阶段 7：结构与读感复核（Review）

目标：
在已有一定正文体量后，检查结构、人物、语言和节奏是否开始失真。

动作：
- 检查是否存在便利型转折、角色工具化、情绪空转、文风漂移
- 判断问题属于扩写层、outline 层，还是结构层

产出：
- `stage_logs/07_review/` 单轮归档
- 明确是继续、补档、回修当前层，还是回退上一层

## 受控试写

如果用户只想验证语气、场景或角色反应，可以做受控试写，但必须满足：

1. 明确标注"受控试写"
2. 不等于正式进入扩写阶段
3. 归档到发起该试写的阶段目录
4. 不能跳过 Prototype

## 回退原则

回退默认只改变当前工作点，不删除旧文件和旧思路。
