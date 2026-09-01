# TypeScript → Python 迁移台账

本文件记录复现范围、顺序和验证依据。状态只使用：`待分析`、`进行中`、`已实现`、
`已验证`、`暂不移植`。其中“已实现”表示代码存在，“已验证”才表示已有足够行为证据。

## 原则

- 以上游公开行为、架构文档、测试和 fixture 为基准，不以文件数量衡量完成度。
- 先迁移底层协议与最小 Provider，再迁移 Consumer 和完整应用组装。
- Python API 可以采用 async context manager、Protocol、dataclass 等惯用表达，但差异必须明确。
- 新插件遵循 [`plugin-development.md`](plugin-development.md)；一个插件是独立生命周期单元，
  不等同于上游的每一个源码文件。
- 每次迁移更新本表，并在“证据”列链接本仓库测试或记录上游来源。
- 每个已验证里程碑都要能通过 VS Code 的长期入口 `Harness: 当前阶段` 按 F5 调试；重要
  调用链同时在 [`debugging.md`](debugging.md) 保留阶段专属配置、断点路线和观察项。

## 路线图

完整的最小主干提案见
[`2026-08-28-minimal-harness-spine.md`](../.agents/notes/proposed/architecture/2026-08-28-minimal-harness-spine.md)。

| 里程碑 | 上游范围 | Python 落点 | 可运行结果 | 状态 |
|---|---|---|---|---|
| M0 Cordis 基线 | vendored Cordis + loader | `dsh/cordis/` | 生命周期、事件、Effect 与 Loader 契约测试 | 已验证 |
| M1 日志与模型协议 | `core/session`, `llm/llm` | `dsh/session`, `dsh/llm`, `dsh/llm_scripted` | scripted 文本的 raw chunk/final message 写入并投影 | 已验证 |
| M2 无工具轮次 | `system-prompt`, `agent`, `agent-loop` | `dsh.system_prompt`, `dsh.agent`, `dsh.agent_loop` | 用户输入到流式最终回复 | 已验证 |
| M3 工具续跑 | `core/tools`, tool-call loop | `dsh/tools`, `dsh/agent_loop` | scripted tool call → echo → 最终回复 | 待分析 |
| M4 可执行主干 | agent-spine demo、headless boot | `dsh/harness`, `dsh/app` | keyless CLI + transcript fixture | 待分析 |
| M4 真实模型叶子 | DeepSeek LLM provider | `dsh/llm/deepseek` | 可选真实 API 端到端任务 | 待分析 |
| M5+ 插件迭代 | persistence/fs/shell/approval/skill 等 | 对应能力模块 | 每项形成完整 capability seam | 待分析 |
| 后期入口 | API、SDK、Web Client | 待定 | 核心 headless 稳定后评估 | 暂不移植 |

### MVP 边界

MVP 包含内存 Session、抽象流式 LLM、scripted Provider、system prompt、工具注册与执行、
单 Agent、Agent Loop、主干组合和 headless 入口。MVP 不包含数据库、fork、并行工具执行、
文件系统/Shell、审批、skills、compaction、jobs、subagent、API 或 Web UI。

MVP 的验收场景固定为一次包含工具调用的 keyless transcript。这个场景打通之前，不提前
建立 M5+ 能力的空目录或公共接口。

### M0 验证记录

- 服务依赖：Provider 出现、移除与替换驱动 Consumer 激活和卸载。
- Fiber 所有权：父插件卸载递归处理子插件，父激活失败回滚子 Fiber 与 Effect。
- Effect：失败 setup 回滚、逆序清理、重复 close 与取消 waiter 后继续清理。
- Events：waterfall 嵌套顺序、显式 `next_` 委托和监听器随 Fiber 撤销。
- Loader：entry children、禁用子树、原子叶配置更新、无效配置保留旧激活。
- 配置：安全 YAML、环境变量、include cycle 与嵌套 overlay deep merge。

验证命令：`uv run pytest dsh/cordis/tests -q`（17 passed）、`uv run ruff check .`、
`uv run mypy dsh`。

### M1 验证记录

- LLM 词汇：不可变 message/source/content block、raw stream chunk、finish reason 与 token usage。
- LLM Runtime：adapter 路由原子注册、Fiber 撤销、未知路由、缺失 finish 补全和 Provider
  failure 终止块。
- BlockAssembler：text/reasoning 顺序、raw tool arguments，以及 max-token 时丢弃不完整工具调用。
- Scripted Provider：配置验证、按序响应和卸载后路由撤销。
- Session：连续 `seq`、事件 payload/消息角色验证，以及只从三类 surface event 投影历史。
- 组装竖切：用户消息 → scripted stream → raw chunk + assistant message → 下一请求完全由日志投影。

验证命令：`uv run pytest -q`（32 passed）、`uv run ruff check .`、`uv run mypy dsh`。

### M2 验证记录

- 上游来源：`packages/core/system-prompt/src/index.ts`、`packages/core/agent/`、
  `packages/core/agent-loop/src/agent.ts` 及 `tests/loop.spec.ts`、`request-error.spec.ts`、
  `cancel.spec.ts`；生命周期顺序对照 `docs/agent-lifecycle.md`。
- System Prompt（Consumer/registry）：具名 section 注册、确定性 `(order, name)` 排序、persona
  配置、组装 waterfall 与贡献随 Fiber 撤销。
- Agent（Definition/registry）：稳定 identity/options、next-turn inbox、状态、取消、可等待 idle，
  Agent 注册随创建它的 Agent Loop Fiber 撤销。
- Agent Loop（Consumer）：`turn/start → step/start → user/message → assistant/chunk* →
  assistant/message → step/end → turn/end`；下一请求消息完全来自 Session 投影。
- 失败与取消：Provider in-band failure 关闭 step/turn 且不写成功 assistant message；取消产生
  `aborted` 收尾；卸载插件会取消并等待活动 driver task 静止。
- 有意延期：M2 每个 turn 只有一个 step；tools、steering、请求重试、完整 prompt scope/context、
  request header 持久化分别由 M3 及后续阶段实现。
- 组装竖切：[`tests/test_m2_tool_free_turn.py`](../tests/test_m2_tool_free_turn.py)，可由
  `Harness: 当前阶段` 与 `阶段 M2: 无工具轮次` 按 F5 调试。

验证命令：`uv run pytest -q`（44 passed）、`uv run ruff check dsh tests`、`uv run mypy dsh`。

## 已知差异

- Python 最低版本为 3.12，使用 `asyncio` 表达异步生命周期。
- Python 包采用 `dsh.*` 命名空间，不复制上游 npm workspace 包名。
- 上游本地路径只用于开发对照；Python 构建和测试不得依赖该目录存在。
- 项目处于预发布阶段，当前不承诺读取上游持久化格式。

## 单项迁移记录模板

迁移模块时在相应表项下补充：

```markdown
### <能力名称>

- 上游来源：`packages/...`
- 可观察行为：...
- Python API：...
- 插件角色：Definition | Provider | Consumer | composition
- 有意差异：...
- 验证：`tests/...`
- 未决问题：...
```
