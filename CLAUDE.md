# CLAUDE.md

本仓库是一个面向 Claude Code 的**知乎盐选短篇小说辅助系统**。

它不追求一口气自动写完整本，而是把创作拆成可停顿、可确认、可修正、可回退、可留痕的阶段，让用户保留主导权，Claude Code 负责协助推进、诊断、整理和扩写。

## 进入项目后的默认读取顺序

按阶段按需加载，不全量读取：

- **始终读**：`CLAUDE.md`（自动）+ `CONTENT_FRAMEWORK.md`（核心写法目标）
- **Structure 阶段起加读**：`PROJECT_RULES.md` + `CONTENT_FRAMEWORK_structure.md`
- **Prototype 阶段起加读**：`AI_WRITING_SOP.md`（如需阶段详情）+ `CONTENT_FRAMEWORK_writing.md`

需要确认仓库定位或目录约定时，查阅 `README.md`。

## 权威来源

- **流程推进**：`AI_WRITING_SOP.md`
- **硬规则与停止条件**：`PROJECT_RULES.md`
- **内容写法与阅读体验**：`CONTENT_FRAMEWORK.md` + `CONTENT_FRAMEWORK_structure.md` + `CONTENT_FRAMEWORK_writing.md`
- **仓库定位与命令**：`README.md`

如果文档之间出现口径差异，按上面的职责边界解释，不自行混写或扩大范围。

## 工作方式

1. 默认从仓库根目录启动会话，不把 `output/` 当成规则仓库根目录。
2. 新建项目：`bash scripts/init_project.sh <slug> [title]`。
3. 继续旧项目：先读该项目的阶段总文件和最近的 `stage_logs/`，判断当前阶段。
4. 不允许跳过阶段直接长篇扩写。
5. 每次只解决一个层级的问题：方向、评估、结构、大纲、prototype、扩写、复核。
6. 信息不足只补问最少必要问题；足够推进则直接推进当前阶段。
7. 进入扩写阶段前，从 `02_Structure.md` 和 `03_Outline.md` 继承数据到 `EXPANSION_CONTEXT.md` 参照表，扩写时只补前场景衔接、每场景更新实际状态。

## 确认门槛

详见 `PROJECT_RULES.md` §2。

可接受信号：`继续`、`下一步`、`按这个来`、`可以`，或明确修正后附带继续指令。

## guard.py 集成

状态管理优先通过 `scripts/guard.py`：

| 命令 | 用途 |
|------|------|
| `guard.py status <project>` | 查看项目状态 |
| `guard.py advance <project> <stage>` | 推进到指定阶段 |
| `guard.py confirm <project>` | 确认当前阶段 |
| `guard.py rewind <project> <target>` | 回退到指定阶段 |
| `guard.py set-killer-test <project> pass/fail` | 记录 Killer Test 结果 |
| `guard.py run-checks <project> <stage>` | 初始化压力测试检查 |

其余压力测试命令（submit-check, submit-checks, check-status, check-report, check-chapter, skip-check）用法见 `guard.py <command> --help`。

当文档描述与 `project_state.json` 冲突时，先修状态或说明冲突，不口头假装已推进。

## 文件纪律

详见 `PROJECT_RULES.md` §5。核心要点：

- 项目产物放 `output/<project>/`，正式正文放 `chapters/`。
- 阶段总文件 + `stage_logs/` 单轮归档并存。
- `01_Evaluation_Log.md` 必须追加，不覆盖。
- `00_Creative_Chat_Log.md` 强制追加，每轮必须有 `- 关键决策: <内容>`。
- 受控试写必须明确标注，归档到发起阶段对应目录。

## 停止条件

详见 `PROJECT_RULES.md` §3。

## 框架调试模式

如果用户说"优化流程"而不是"写故事"，切换到框架调试模式：

- 脑洞只是测试样本，不是必须救活的作品。
- 首要目标是暴露流程缺陷，不是替不通的前提继续包装。
- 前提因果链不通就停，明确记录哪一步问得太晚。
- 优先修框架文档和检查点，再决定是否继续样本。

## 发散模式

当用户说"我想聊聊这个脑洞"或处于 Intake / Idea Fission 阶段时，进入发散模式：

1. 不打断用户的自由表达，允许散漫地聊脑洞、人物、画面、句子、情绪
2. 每轮对话结束后，自动判断用户说的内容属于哪个模块（premise / 人物 / 冲突 / 场景画面 / 情绪 / 风险）
3. 在对话尾部用一行标注当前沉淀状态，例如："本轮沉淀：premise 核心更新 + 新增一个场景画面"
4. 当沉淀内容足够进入下一阶段时，主动提示"当前信息已经够跑 Killer Test 了，要不要试一下？"
5. 每个模块最多沉淀 3 条核心结论，防止信息膨胀但故事反而变远

发散模式不改变阶段推进规则，只是在 Intake 和 Idea Fission 阶段多了一个"边聊边收"的工作方式。


## 用户标注约定

用户在文稿中用 `##原文##意见##` 格式标注，例如：

```
这件大衣我想了三个星期##买了也像是在讨好自己##这里感觉不通顺##
```

格式说明：第一个 `##` 后是被标注的原文片段，第二个 `##` 后是意见或提问，第三个 `##` 结束。

凡是看到此格式，均视为用户对该位置的标注，可能是修改意见、也可能是提问。按标注内容判断用户意图并响应，不需要用户额外说明。

## 扩写修改流程

### 版本命名规范

```
scene-xx.md          ← 初稿
scene-xx-v1.md       ← 第 1 轮修改版
scene-xx-v2.md       ← 第 2 轮修改版（依此递增）
scene-xx-终稿.md     ← 用户确认"这稿过了"
```

### 修改标注格式

用户在当前版本上用 `##原文##意见##` 标注，AI 在下一版本中用 `##原文##用户意见##AI修改说明##` 留痕：

```
##他递过来一杯水##这里感觉太平了##改为递咖啡，加一句他记得她口味的细节##
```

### 流转规则

1. 用户在 `scene-xx.md`（或当前最新版本）上用 `##原文##意见##` 标注
2. AI 输出下一版本（v1/v2/v3...），只改有标注的地方，不重写全文
3. 每处修改用 `##原文##用户意见##AI修改说明##` 留痕在新版本对应位置的注释中
4. 用户说"这稿过了" → 保存为 `scene-xx-终稿.md`（去掉所有标注痕迹的干净版）
5. 全部终稿完成后 → 合并为 `chapters/《小说标题》.md`

### 硬规则

- 只改有标注的地方，不动未标注内容
- 版本号只递增，不覆盖旧版本
- 终稿是干净正文，不含任何 `##` 标注

## 操作边界

1. 只允许在当前 git 仓库内操作。
2. 不允许直接推送 `main` 分支。
3. 只允许推送当前工作分支。
4. 不允许 `force push`。
5. 不允许修改 git remote。
6. 不允许删除 `.git` 目录。
7. 不允许执行与当前仓库无关的破坏性系统操作。

## 默认不做事项

除非用户明确要求，否则不要：

1. 大面积重写已经能用的框架文档。
2. 引入与当前任务无关的新依赖或脚本。
3. 为了"更优雅"而重构已稳定的 guard.py 或模板体系。
4. 把一次小修扩展成整仓重写。
5. 主动新增 AI_WRITING_SOP / PROJECT_RULES / CONTENT_FRAMEWORK 之外的新框架文档。

## 阶段性保存规则

每完成一个明确的阶段性目标（框架文档修改、模板更新、guard.py 功能变更、项目阶段推进），必须执行一次完整保存流程：

1. 运行最小必要验证（guard.py 能正常执行、修改后的模板格式正确、相关脚本不报错）。
2. `git add` 本次相关文件。
3. 创建一次语义清晰的 commit。
4. 将当前工作分支推送到远程仓库。
5. 向用户汇报：
   - milestone 名称
   - commit SHA
   - push 结果
   - 剩余未完成项

## 本项目的最小必要验证

按"改哪里，验哪里"原则：

1. 修改 `scripts/guard.py` → 至少跑一次 `guard.py status <test-project>` 确认不报错。
2. 修改 `scripts/init_project.sh` → 至少跑一次初始化确认目录结构正确。
3. 修改 `templates/` 下模板 → 确认模板占位符、标题、格式无误。
4. 修改 `AI_WRITING_SOP.md` / `PROJECT_RULES.md` / `CONTENT_FRAMEWORK.md` → 确认与 CLAUDE.md 权威来源表述无矛盾。
5. 如果验证命令失败，必须先判断是代码问题、环境问题还是测试数据问题，再决定是否继续。

## 推荐 commit 粒度与命名

每次 commit 只表达一个明确目的，不混入多个不相关修改。

推荐使用：

- `fix:` 用于缺陷修复（guard.py bug、模板错误等）
- `refactor:` 用于小范围结构整理
- `docs:` 用于框架文档修改（SOP、规则、模板）
- `feat:` 仅用于用户明确要求的新功能
- `chore:` 用于配置、脚本维护

commit message 必须体现"为什么要改"，不要写空泛描述。

## 建议重点关注的高风险区域

修改以下区域时，需要更加保守，确认后再改：

1. `scripts/guard.py` — 状态管理核心，改错会导致阶段推进出问题。
2. `AI_WRITING_SOP.md` — 流程主文档，改动影响所有项目的推进方式。
3. `PROJECT_RULES.md` — 硬规则文档，改动影响停止条件与确认门槛。
4. `CONTENT_FRAMEWORK.md` — 内容写法标准，改动影响所有扩写质量判断。
5. `templates/project/` — 模板改动影响所有新项目初始化。

如果一次改动同时涉及以上多个文件，优先拆成多个 milestone。

## 必须暂停并汇报的情况

遇到以下任一情况，必须立刻暂停，不得自行继续：

1. GitHub 认证失败。
2. `git push` 被远程拒绝。
3. 出现 merge/rebase 冲突。
4. guard.py 报错且无法最小修复。
5. 需要改写 git 历史。
6. 需要删除大量文件或进行其他高破坏性操作。
7. 发现框架文档之间存在无法自行判断的口径冲突。
8. 用户项目的 `project_state.json` 状态与实际产物明显不一致，无法确定以谁为准。

## 默认并行执行规则

本项目以文档和创作为主，并行需求低于代码项目，但仍需约束：

1. 默认**最多同时占用 5 个并行位**。
2. **预留 2 个并行位给用户**。
3. 并行位包括：Agent 子代理、后台 Bash 长任务。
4. 未经用户明确允许，不得占满所有并行位。

### 适合并行的操作

- 同时读取多个框架文档进行对齐检查。
- 同时检查多个项目的 `project_state.json` 状态。
- guard.py 验证 + 模板格式检查。

### 不适合并行的操作

- 同时修改多个高风险框架文档。
- 同时推进多个项目的阶段（每个项目需要独立的用户确认）。

## 多项目并行规则

用户可能同时开多个 Claude Code 实例，各自推进不同项目。

### 隔离保障

- 每个项目的状态文件 `output/<project>/project_state.json` 完全独立，互不影响。
- `scripts/guard.py`、`check_defs.py`、`check_engine.py` 是只读代码，无并发冲突。

### 分支管理

1. **每个项目使用独立工作分支**，命名 `project/<slug>`（如 `project/xiao-hao-lao-gong`）。
2. **不允许多个实例同时操作同一分支**。
3. 阶段完成后，将工作分支 merge 到 main，**merge 后可安全删除工作分支**（内容已保存在 main 中）。
4. 未合并的分支**禁止删除**。
5. 定期清理已合并的旧分支，避免积累：`git branch --merged main | grep 'project/' | xargs git branch -d`。

### 启动时分支检查

1. 确认当前不在 `main`。
2. 确认当前分支对应本次要推进的项目。
3. 如果分支不存在，创建：`git checkout -b project/<slug>`。

## 代理环境下的 Git / GitHub 命令

如果当前网络环境访问 GitHub 不稳定，可在命令前临时加代理环境变量。不要修改全局 git config。

当前常用代理示例：

```bash
HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897" git push
```

首次推送工作分支示例：

```bash
HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897" git push -u origin <当前分支>
```

如果代理端口或地址变化，应优先使用用户当前提供的新值。

## 每次启动后的默认动作

开始工作前，默认执行以下顺序：

1. 先阅读本文件（CLAUDE.md，自动加载）。
2. `guard.py status <project>` 确认当前阶段。
3. `guard.py context <current-stage>` 确认本阶段需要读什么文档。
4. 只读需要的文档章节（不全量加载所有框架文档）。
5. 确认当前分支不是 `main`（如果在 `main`，先切到工作分支）。
6. 查看当前工作区是否已有未提交改动。
7. 根据用户任务，先定义本次要完成的 milestone。
8. 仅在 milestone 边界执行 commit、push。

如需查询阶段入口/出口条件：`guard.py stage-info <stage>`。
如需查询停止条件和确认门槛：`guard.py rules`。

## 输出风格

1. 默认阶段式推进，不一次性自动跑完。
2. 少量、清晰、可继续接管，不超量生成。
3. 用户未确认前，任何产出都视为可修改版本。
4. 基础层有问题就回修，不假装能靠后文补回来。

## 建议启动方式

如需最大化自动化，可使用：

```bash
claude --dangerously-skip-permissions
```

但即使在该模式下，也必须严格遵守本文件中的操作边界与阶段性保存规则。
