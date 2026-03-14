# CLAUDE.md

本仓库是一个面向 Claude Code 的**知乎盐选短篇小说辅助系统**。

它不追求一口气自动写完整本，而是把创作拆成可停顿、可确认、可修正、可回退、可留痕的阶段，让用户保留主导权，Claude Code 负责协助推进、诊断、整理和扩写。

## 进入项目后的默认顺序

1. 先读 `README.md`，确认仓库定位与目录约定。
2. 再读 `AI_WRITING_SOP.md`，理解阶段推进方式。
3. 再读 `PROJECT_RULES.md`，确认硬规则、停止条件与确认门槛。
4. 最后读 `CONTENT_FRAMEWORK.md`，对齐内容写法、节奏与阅读体验要求。

## 权威来源

- **流程推进**：`AI_WRITING_SOP.md`
- **硬规则与停止条件**：`PROJECT_RULES.md`
- **内容写法与阅读体验**：`CONTENT_FRAMEWORK.md`
- **仓库定位与命令**：`README.md`

如果文档之间出现口径差异，按上面的职责边界解释，不自行混写或扩大范围。

## 工作方式

1. 默认从仓库根目录启动会话，不把 `output/` 当成规则仓库根目录。
2. 新建项目：`bash scripts/init_project.sh <slug> [title]`。
3. 继续旧项目：先读该项目的阶段总文件和最近的 `stage_logs/`，判断当前阶段。
4. 不允许跳过阶段直接长篇扩写。
5. 每次只解决一个层级的问题：方向、评估、结构、大纲、prototype、扩写、复核。
6. 信息不足只补问最少必要问题；足够推进则直接推进当前阶段。

## 确认门槛

以下节点必须等用户明确确认后才能继续：

1. 脑洞裂变后
2. 方向评估后
3. 结构方案后
4. 详细大纲后
5. Prototype 后
6. 每次扩写后

可接受信号：`继续`、`下一步`、`按这个来`、`可以`，或明确修正后附带继续指令。

## guard.py 集成

状态管理优先通过 `scripts/guard.py`：

```bash
# 查看项目状态
python3 scripts/guard.py status <project>

# 推进到下一阶段
python3 scripts/guard.py advance <project>

# 确认当前阶段
python3 scripts/guard.py confirm <project>

# 回退到指定阶段
python3 scripts/guard.py rewind <project> <target>

# 捕获知识到项目知识库
python3 scripts/guard.py capture <project> <kind> <title> --summary "..." --source <file> --tag <tag>

# 生成候选知识审核文档
python3 scripts/guard.py review-create <project>

# 应用审核结果
python3 scripts/guard.py review-apply <project> <review-file>
```

当文档描述与 `project_state.json` 冲突时，先修状态或说明冲突，不口头假装已推进。

## 文件纪律

- 项目产物放在 `output/<project>/`。
- 阶段总文件 + `stage_logs/` 单轮归档并存。
- `01_Evaluation_Log.md` 必须追加，不覆盖。
- 单轮归档默认新增文件，不覆盖旧记录。
- 回退是非破坏性的；有价值的旧内容进 `knowledge/`。
- 知识库采用三层：`candidates/` → `reviews/` → `entries/`。
- 正式正文放 `chapters/`。
- 受控试写必须明确标注，归档到发起阶段对应目录。

## 框架调试模式

如果用户说"优化流程"而不是"写故事"，切换到框架调试模式：

- 脑洞只是测试样本，不是必须救活的作品。
- 首要目标是暴露流程缺陷，不是替不通的前提继续包装。
- 前提因果链不通就停，明确记录哪一步问得太晚。
- 优先修框架文档和检查点，再决定是否继续样本。

## 停止条件

出现以下情况必须停止继续推进：

1. 方向未定 / 结构未稳
2. 前提因果链答不通（"为什么非要这么做""为什么不能更简单"）
3. 关键转折依赖巧合或空降信息
4. 人物明显工具化
5. Prototype 有明显提纲腔
6. 扩写出现 outline 翻译腔、对话同质化、场景没立住
7. 用户要求回到上一层修改

## 输出风格

1. 默认阶段式推进，不一次性自动跑完。
2. 少量、清晰、可继续接管，不超量生成。
3. 用户未确认前，任何产出都视为可修改版本。
4. 基础层有问题就回修，不假装能靠后文补回来。
