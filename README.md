# DPXS — Claude Code 版

知乎盐选短篇小说辅助系统，面向 Claude Code。

## 这是什么

一套 LLM 协作写作框架，把创作过程拆成阶段式推进：

- 你负责方向、审美、取舍
- Claude Code 负责裂变、诊断、整理、验证、扩写
- 每一步都留痕，避免一路快跑后才发现基础是歪的

特别强调：**保留知乎盐选式的快节奏、强钩子和情绪回收，同时减少提纲 prose、便利型转折、工具人角色和空情绪爽点。**

## 快速开始

1. 初始化新项目：

```bash
bash scripts/init_project.sh my-story "真假千金反杀"
```

2. 查看项目状态：

```bash
python3 scripts/guard.py status my-story
```

3. 回退到上一步：

```bash
python3 scripts/guard.py rewind my-story previous
```

4. 捕获知识到项目知识库：

```bash
python3 scripts/guard.py capture my-story lesson "前提校验太晚" \
  --summary "前提因果校验应该前移到裂变之前。" \
  --source stage_logs/00_intake/02_premise-pressure-test-failed.md \
  --tag workflow
```

5. 审核候选知识：

```bash
python3 scripts/guard.py review-create my-story
# 编辑 knowledge/reviews/*.md，标记 保留/丢弃/合并/稍后
python3 scripts/guard.py review-apply my-story knowledge/reviews/001_candidate-review.md
```

6. 开始和 Claude Code 对话：

```text
我准备开始 output/my-story 这个项目。
脑洞是：……
先帮我做 intake 和脑洞裂变。
```

## 仓库结构

```text
.
├── .claude/
│   └── settings.json
├── CLAUDE.md               # Claude Code 协作入口
├── README.md
├── AI_WRITING_SOP.md        # 流程：阶段如何推进
├── PROJECT_RULES.md         # 规则：什么能做、什么必须停
├── CONTENT_FRAMEWORK.md     # 写法：内容怎么写、节奏怎么控
├── scripts/
│   ├── guard.py             # 状态管理
│   └── init_project.sh      # 项目初始化
├── templates/
│   └── project/             # 新项目模板
└── output/                  # 项目产物
    └── <project>/
        ├── PROJECT_INFO.md
        ├── project_state.json
        ├── 00_Brainstorm.md
        ├── 00_Creative_Chat_Log.md
        ├── 01_Evaluation_Log.md
        ├── 02_Structure.md
        ├── 03_Outline.md
        ├── 04_Prototype.md
        ├── chapters/
        ├── knowledge/
        │   ├── candidates/
        │   ├── reviews/
        │   └── entries/
        └── stage_logs/
```

## 核心文档

| 文件 | 职责 |
|------|------|
| `AI_WRITING_SOP.md` | 从脑洞到成文，阶段如何推进 |
| `PROJECT_RULES.md` | 确认门槛、停止条件、留痕规则、文件纪律 |
| `CONTENT_FRAMEWORK.md` | 内容写法、节奏控制、阅读体验要求 |
| `CLAUDE.md` | Claude Code 进入仓库后的默认工作方式 |

## 写作流程

```text
原始脑洞 → 输入收集 → 前提因果校验 → 脑洞裂变 → 方向评估
→ 结构方案 → 详细大纲 → Prototype → 场景化扩写 → 结构与读感复核
```

每个阶段都有确认门槛，用户不确认就不往下走。

## 知识库

每个项目自带三层知识库：

1. `knowledge/candidates/` — 候选条目，允许粗糙
2. `knowledge/reviews/` — 审核文档，中文标记去留
3. `knowledge/entries/` — 正式知识，只保留确认过的高价值内容

回退时有价值的旧思路、失败样本、可复用片段都可以沉淀到这里。

## 两种模式

### 写作模式
目标是把项目往前推进，关注故事成立、结构成立和扩写读感。

### 框架调试模式
目标是用实际脑洞压测流程本身，暴露流程缺陷优先于写出好故事。
