# Agent Note: 以最小可运行主干启动 Python Harness

Status: proposed

## Problem

上游 DeepSeek Harness 已包含会话、LLM、工具、Agent Loop、持久化、审批、Shell、Web、
Subagent 和多种入口。按包逐个平移会长时间得到一组无法组合运行的模块，也会在尚无端到端
证据时过早固化大量接口。Python 复现需要先确定最小产品闭环，以及后续插件只能依赖的稳定
扩展点。

现有 `dsh.cordis` 提供插件生命周期，但尚未通过 Harness 场景证明服务替换、注册撤销和
异步清理足以承载 Agent Loop。项目需要一个可在无 API Key 环境确定性运行、又能自然接入
真实模型与工具的主干。

## Proposal

先实现一个无 UI、内存态、单 Agent 的最小 Harness 主干。主干只包含所有入口共同需要的
Service Definition、Consumer 和默认 Agent Loop；具体 LLM Provider 与未来执行环境作为
同级叶子插件注入。

最小闭环为：用户输入进入 Agent inbox，Agent Loop 打开 turn，将输入写入 Session，组装
system prompt 和工具 schema，通过抽象 LLM 服务读取流，记录 assistant 输出；若模型请求
工具，则经过 Tools 流水线执行、记录结果并发起下一 step，直到产生最终文本并关闭 turn。

首个可运行组合使用确定性的 scripted LLM Provider 和无副作用的 `echo` 工具，证明：

```text
user input
  -> turn/start -> step/start -> user/message
  -> scripted LLM -> assistant tool call
  -> tools pipeline -> echo -> tool/result
  -> next step -> scripted LLM -> assistant/message
  -> step/end -> turn/end
```

### 主干模块

只在开始实现对应能力时创建目录，不预建空包：

| Python 模块 | 角色 | MVP 范围 |
|---|---|---|
| `dsh.core.runtime.session` | Definition + 内存 Provider | 仅追加事件、读取、消息投影；暂不做磁盘持久化与 fork |
| `dsh.core.model.llm` | Service Definition | message/content/tool-call 词汇、流式请求协议、稳定 Provider 错误 |
| `dsh.plugins.providers.model.llm_scripted` | 测试 Provider | scripted 流与请求捕获，不进入生产默认组合 |
| `dsh.core.runtime.system_prompt` | Consumer/registry | 有序 prompt section 与工具 schema 组装 |
| `dsh.core.runtime.tools` | Definition + Consumer | 生命周期化注册、参数校验、pre/execute/post 流水线、最终结果 |
| `dsh.core.runtime.agent` | Definition + registry | 单 Agent、inbox、状态与 `agent/*` 事件 |
| `dsh.core.runtime.agent_loop` | Consumer | 串行 step、工具续跑、取消与错误收尾 |
| `dsh.core.application.bundle` | composition | 挂载共享主干，不选择具体 LLM 后端 |
| `dsh.core.application.boot` | entry adapter | 单次任务入口与确定性 transcript 输出 |

MVP 内的“单 Agent”是组装限制，不写死在服务协议中。事件和标识从第一版保留 `session_id`、
`agent_id`、`turn_id` 与 `step_id`，避免后续多会话或多 Agent 需要重写日志语义。

### 插件扩展规则

- 每项能力先定义 Service Definition，再实现至少一个 Provider 或 Consumer；主干不导入具体
  Provider。
- 服务、prompt section、工具和事件监听都通过 Cordis Effect 注册并随 Fiber 卸载。
- Tools 的 `pre-execute`、`execute`、`post-execute` 使用 waterfall 语义，策略插件可以拒绝、
  包装或改写结果。
- LLM 流的原始片段与完成消息分别记录，使终端输出、回放和最终模型历史可以独立投影。
- 送入后续模型请求的所有消息必须来自 Session 投影；Agent Loop 不维护第二份隐藏历史。
- composition 只决定共享插件集合和配置转发；应用入口选择 Provider、I/O 和生命周期。

### 分阶段交付

#### M0：Cordis Harness 基线

补齐服务出现/消失、Provider 替换、Effect 撤销、waterfall 短路、异步取消和 loader 组合测试。
这一阶段不新增 Harness 业务模块。

#### M1：日志与模型协议

实现 `dsh.core.runtime.session`、`dsh.core.model.llm` 和 scripted Provider。使用一次固定文本响应证明用户消息、流式
片段和最终 assistant 消息都进入日志，并能从日志投影出下一次 LLM 请求。

#### M2：一次无工具轮次

实现 system prompt、Agent inbox/registry 和最小 Agent Loop。完成
`input -> streamed response -> transcript`，覆盖正常完成、Provider 失败和调用方取消。

#### M3：工具续跑闭环

实现 Tools 注册表与流水线，加入测试 `echo` 插件。模型先调用工具、再消费工具结果并给出
最终文本；验证未知工具、参数错误、工具异常、策略拒绝和并行请求的串行 MVP 行为。

#### M4：主干组合与 headless

实现 `dsh.core.application.bundle` 和单次 headless 入口。提供一个 keyless 示例配置和 transcript fixture，
证明空工作区从配置加载到正常退出；再接入首个 DeepSeek Provider 插件，但真实 API 测试在
缺少凭据时明确跳过。

#### M5+：按完整 seam 迭代

每次只增加一个能形成完整闭环的插件能力，建议顺序为：持久化 Session、文件系统与只读
工具、Shell + 本地进程、审批策略、skills/context、compaction、jobs、subagent，最后才是
API/Web UI。每项都提供 Definition、Provider、Consumer、契约测试与 assembled transcript；
不能只添加接口或只添加工具 schema。

## Alternatives considered

**按上游 workspace 一次性建立所有 Python 包。** 这能让目录看起来接近上游，但会产生
大量没有运行证据的空接口，并把 TS 包边界误当成 Python 的最佳模块边界。

**先接真实 DeepSeek API，再补测试 Provider。** 这能更早看到真实输出，但测试受凭据、网络
和模型非确定性影响，无法作为 Agent Loop 与事件日志的回归基线。

**把 Session、Tools 与 LLM 调用直接写进一个 Harness 类。** 初期代码更少，但插件无法替换
Provider 或插入策略，后续拆分会改变全部调用方和日志语义。

**先实现完整持久化与 Web UI。** 这扩大了首个里程碑的状态格式与协议范围，却仍不能证明
最核心的模型—工具续跑行为正确。

## Acceptance criteria

- `uv run dsh ...` 或等价 headless 命令可用 scripted Provider 完成一次含工具调用的任务，
  无需网络和密钥。
- transcript 中存在配对的 turn/step、用户消息、assistant tool call、tool result 与最终回复。
- 下一 step 的模型请求完全由 Session 日志投影，测试中不存在旁路历史列表。
- 卸载工具或 Provider 插件会撤销注册；依赖它的 Fiber 停止或等待替代 Provider。
- Provider 失败、工具失败和取消均产生确定性收尾，且不会留下活动 Fiber/Effect。
- 单元、Provider 契约、组合集成和 keyless transcript 四层测试通过。
- 最小主干不依赖 DeepSeek SDK、文件系统执行、数据库、Web 框架或 UI。

## Risks

- 过度压缩 Session 事件可能导致后续持久化不兼容；MVP 仍需从上游事件投影测试提取最小
  稳定语义，而不是发明临时 transcript 格式。
- Python async generator 的取消与清理不同于 JavaScript stream；M1 必须先固定关闭协议。
- 提前暴露过多公共类会限制重构；预发布阶段仅导出跨模块协议和必要数据类型。
- scripted Provider 容易让错误时序过于理想化；M2/M3 必须包含分片中断、工具异常和取消。
- 串行工具执行是 MVP 限制。事件与结果顺序需要为未来有界并行保留明确扩展空间。
