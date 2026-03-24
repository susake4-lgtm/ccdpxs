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

3. 确认当前阶段入口：

```bash
python3 scripts/guard.py context intake
```

4. 按当前阶段入口开始协作：

```text
我准备开始 output/my-story 这个项目。
脑洞是：……
先按 AGENTS.md 和当前阶段入口带我开始。
```

5. 常用状态命令：

```bash
python3 scripts/guard.py set-killer-test my-story pass
python3 scripts/guard.py rewind my-story previous
```

## 仓库结构

```text
.
├── .claude/
│   └── settings.json
├── AGENTS.md               # 当前阶段入口与协作契约
├── CLAUDE.md               # 兼容入口（转到 AGENTS.md）
├── README.md
├── AI_WRITING_SOP.md        # 流程：阶段如何推进
├── PROJECT_RULES.md         # 规则：什么能做、什么必须停
├── CONTENT_FRAMEWORK.md     # 写法：核心写法目标（始终加载）
├── CONTENT_FRAMEWORK_structure.md  # 写法：人物与冲突（Structure 起加载）
├── CONTENT_FRAMEWORK_writing.md    # 写法：开篇、节奏、扩写（Prototype 起加载）
├── scripts/
│   ├── guard.py             # 状态管理
│   ├── check_defs.py        # 压力测试检查定义
│   ├── check_engine.py      # 压力测试执行引擎
│   └── init_project.sh      # 项目初始化
├── templates/
│   └── project/             # 新项目模板
└── output/                  # 项目产物
    └── <project>/
        ├── PROJECT_INFO.md
        ├── project_state.json
        ├── 00_Brainstorm.md
        ├── 00_Killer_Test.md
        ├── 00_Creative_Chat_Log.md
        ├── 01_Evaluation_Log.md
        ├── 02_Structure.md
        ├── 03_Outline.md
        ├── 04_Prototype.md
        ├── chapters/
        └── stage_logs/
```

## 核心文档

| 文件 | 职责 |
|------|------|
| `AI_WRITING_SOP.md` | 从脑洞到成文，阶段如何推进 |
| `PROJECT_RULES.md` | 确认门槛、停止条件、留痕规则、文件纪律 |
| `CONTENT_FRAMEWORK.md` | 核心写法目标（始终加载） |
| `CONTENT_FRAMEWORK_structure.md` | 人物与冲突推进（Structure 起加载） |
| `CONTENT_FRAMEWORK_writing.md` | 开篇硬指标、节奏密度、扩写标准（Prototype 起加载） |
| `AGENTS.md` | 当前阶段入口与默认工作方式 |
| `CLAUDE.md` | 兼容入口，旧路径请转到 `AGENTS.md` |

## 写作流程

```text
原始脑洞 → 输入收集 → Killer Test → 前提因果校验 → 脑洞裂变 → 方向评估
→ 结构方案（含情绪曲线）→ 详细大纲 → Scene Pressure Test → Prototype
→ 场景化扩写 → 结构与读感复核
```

每个阶段都有确认门槛，用户不确认就不往下走。

## 两种模式

### 写作模式
目标是把项目往前推进，关注故事成立、结构成立和扩写读感。

### 框架调试模式
目标是用实际脑洞压测流程本身，暴露流程缺陷优先于写出好故事。
