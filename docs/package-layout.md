# DSH 包目录设计

本文定义 Python Harness 已实施的一级物理分区，以及后续能力采用的候选归类。当前 import
路径以源码为准，实施证据见 [`porting.md`](porting.md)，迁移决定见
[`三分区包目录`](../.agents/notes/implemented/architecture/2026-09-01-three-zone-package-layout.md)。

## 设计目标

`dsh` 下只保留三个一级产品分区：

```text
dsh/
├── cordis/   # Cordis 插件运行时，不包含 Harness 产品语义
├── core/     # 默认 Harness 套件；默认组合正常运行所必需
└── plugins/  # 默认套件以外、需要显式选择的插件
```

一级目录只回答“代码属于运行时、默认产品还是可选扩展”。领域和能力角色下沉到后续目录。
Python import 路径与物理路径一致，例如 `dsh.core.runtime.agent` 和
`dsh.plugins.integrations.gateway.transports.websocket.gateway_websocket`。

一个独立生命周期单元仍是一个插件包，并从自己的 `__init__.py` 导出唯一 `plugin` 入口。
目录嵌套不产生 Cordis Fiber 父子关系；真实父子关系只由 `ctx.plugin()` 或 Loader
`children` 建立。

## `core`：默认 Harness 套件

`core` 包含默认 profile 会装载的 Definition、默认 Provider、Consumer、策略和应用组合。
“技术上是插件”不构成移入 `plugins` 的理由；如果缺少它会使默认 Harness 不完整，它就属于
`core`。

```text
dsh/core/
├── runtime/                              # Agent 核心运行链
│   ├── agent/                            # Agent 实例、状态、取消与 inbox
│   ├── agent_loop/                       # turn、step、LLM 调用与工具续跑
│   ├── agent_default_model/              # 默认模型选择
│   ├── agent_tool_presentation/          # 工具及结果的模型展示
│   ├── scope/                            # Agent、Session 与插件作用域
│   ├── session/                          # 基础 Session 与事件日志
│   ├── system_prompt/                    # System Prompt 注册与组装
│   └── tools/                            # 工具注册与执行流水线
├── model/                                # 默认模型能力
│   ├── llm/                              # Provider-neutral LLM Definition
│   ├── llm_deepseek/                     # 默认 DeepSeek Provider
│   ├── llm_retry/                        # 模型请求重试策略
│   └── token_meter/                      # token 计量
├── session/                              # Session 持久化与派生数据
│   ├── log/                              # 日志格式
│   ├── persistence/                      # 持久化 Definition 与默认 Provider
│   ├── projection/                       # 日志投影与缓存
│   ├── query/                            # 查询 Definition 与默认实现
│   ├── title/                            # 会话标题生成
│   ├── telemetry/                        # 遥测 Definition 与默认 Provider
│   └── policy/                           # checkpoint 等会话策略
├── execution/                            # 默认本地执行能力
│   ├── subprocess/                       # 子进程 Definition 与本地 Provider
│   ├── sandbox/                          # 沙箱 Definition、Provider 与策略
│   ├── shell/                            # Shell Definition、默认 Provider 与工具
│   ├── filesystem/                       # FS Definition、默认 Provider 与工具
│   └── code_runtime/                     # 代码执行 Definition 与默认 Provider
├── context/                              # 默认模型上下文
│   ├── agent_instructions/               # 工作区 Agent 指令
│   ├── file_reference/                   # 文件引用
│   ├── session_reference/                # Session 引用
│   ├── time_context/                     # 时间与时区
│   └── tmux_context/                     # tmux 环境
├── collaboration/                        # 用户与 Agent 协作
│   ├── interaction/                      # 命令、审批、提问与权限预设
│   ├── feedback/                         # 消息和命令反馈
│   ├── goal/                             # Goal 状态、驱动器、命令与工具
│   ├── plan/                             # Plan 协作模式
│   ├── todo/                             # Todo 工具
│   └── jobs/                             # 后台任务 Definition、Provider 与工具
├── delegation/                           # Agent 委派与工作流
│   ├── subagent/                         # 进程内 Subagent 与控制工具
│   └── workflow/                         # Workflow Definition、引擎与工具
├── knowledge/                            # 默认知识与网络能力
│   ├── skill/                            # Skill 注册表、Provider 与工具
│   └── web/                              # Web Definition、默认 Provider 与工具
├── storage/                              # 默认非 Session 数据存储
│   ├── storage/                          # 通用存储与默认 Provider
│   ├── spill/                            # 大结果外置存储与策略
│   └── attachment/                       # 附件身份、验证与存储
├── configuration/                        # 设置、凭据、身份与 Workspace
│   ├── settings/
│   ├── credentials/
│   ├── identity/
│   └── workspace/
├── policy/                               # 默认横切策略
│   ├── compaction/                       # 上下文压缩
│   └── guard/                            # 超时与循环卫生
├── application/                          # 默认可启动应用
│   ├── boot/                             # 启动与命令行公共逻辑
│   ├── bundle/                           # base、headless、web 等默认组合
│   ├── api/                              # 内部 API gateway 与控制器
│   ├── host/                             # Web 服务端
│   └── client/                           # Web 客户端 UI
└── internal/                             # 不直接形成产品表面的内部设施
    ├── typert/
    ├── runtime_diagnostics/
    ├── util/
    └── test_support/
```

上面的 M3+ 深层目录是候选分类，不是要求预建的公共 ABI。当前已实施的产品树只包含
`model/llm` 与 `runtime/{agent,agent_loop,session,system_prompt}`；默认 profile 在 M4 落地前，
其余能力的 `core`/`plugins` 归属必须在对应迁移记录中重新验证。

`core.application.api.gateway` 是默认应用内部的 API gateway。它不同于
`plugins.integrations.gateway`：后者是供部署显式选择的外部通信网关体系。

## `plugins`：默认套件外插件

`plugins` 包含替代 Provider、外部平台集成、可选执行环境、非默认应用组合、示例和实验。

```text
dsh/plugins/
├── providers/                            # 默认实现的替代 Provider
│   ├── model/                            # 替代模型或搜索 Provider
│   ├── session/                          # SQLite 等替代持久化和标题实现
│   ├── storage/                          # 替代通用存储后端
│   └── shell/                            # 非沙箱或平台专用 Shell
├── execution/                            # 可选执行能力
│   ├── terminal/                         # PTY Definition、Provider 与工具
│   ├── persistent_shell/                 # 持久 Shell 工具
│   ├── lsp/                              # LSP Definition、Provider 与工具
│   └── e2b/                              # E2B 远程执行 Provider
├── agents/                               # 外部 Agent Provider
│   ├── acp/
│   ├── claude_code/
│   ├── codex/
│   └── dsh_sdk/
├── integrations/                         # 外部平台与通信协议
│   ├── messaging/                        # IM 与协作消息平台
│   ├── gateway/                          # 可选通信网关
│   ├── mcp/
│   ├── webhook/
│   ├── hooks/
│   └── acp/
├── automation/                           # 定时任务、Session 查询与导出
├── extensions/                           # Cordis 自检查与动态装载
├── applications/                         # 非默认应用、profile 与 SDK
├── examples/                             # 可复用示例组合
└── experimental/                         # 未发布、无兼容承诺的实验
```

当前已实施的可选产品树只有 `providers/model/llm_scripted`。它虽然服务于测试和 keyless 演示，
但具有独立配置、Adapter 注册和 Fiber 生命周期，因此是完整 Provider，而不是 `llm` 包内的
测试辅助代码。

### Messaging

Messaging 使用公共协议加平台 Provider 的结构：

```text
dsh/plugins/integrations/messaging/
├── common/
│   ├── messaging/                        # 统一消息 Service Definition
│   ├── messaging_router/                 # 入站与出站路由
│   ├── messaging_session/                # 外部会话与 DSH Session 映射
│   ├── messaging_attachment/             # 附件标准化
│   └── messaging_policy/                 # 白名单、群聊与提及策略
├── telegram/                             # Telegram Provider 与接入方式
├── discord/                              # Discord Provider 与 Gateway
├── slack/                                # Slack Provider 与 Events API
├── lark/                                 # 飞书/Lark Provider 与事件订阅
├── dingtalk/                             # 钉钉 Provider
├── wecom/                                # 企业微信 Provider
└── matrix/                               # Matrix Provider
```

平台适配只负责外部消息与统一消息模型之间的转换。完整的 Telegram Agent 等可启动组合属于
`dsh.plugins.applications.bundles`。

### Gateway

Gateway 分开表达传输机制、应用协议、策略和 Harness 桥接：

```text
dsh/plugins/integrations/gateway/
├── core/
│   ├── gateway/                          # Gateway Service Definition
│   ├── gateway_router/                   # 请求与连接路由
│   ├── gateway_connection/               # 连接生命周期
│   └── gateway_codec/                    # 编解码注册表
├── transports/                           # 数据如何传输
│   ├── http/                             # HTTP 请求/响应与 Server Provider
│   ├── websocket/                        # WebSocket 双向连接
│   ├── sse/                              # Server-Sent Events
│   ├── mqtt/                             # MQTT Client、Broker 与 topic 映射
│   └── webrtc/                           # Signaling、DataChannel 与媒体轨道
├── protocols/                            # Transport 上承载的应用协议
│   ├── json_rpc/
│   ├── openai/
│   ├── acp/
│   ├── mcp/
│   └── dsh/
├── policies/                             # 认证、授权、限流、超时与可观察性
├── bridges/                              # 外部请求与 Agent/Session/Tools/Events 的转换
└── bundles/                              # HTTP API、OpenAI API、MQTT Agent 等组合
```

HTTP、WebSocket、SSE、MQTT 和 WebRTC 是 Transport；OpenAI、JSON-RPC、ACP 和 MCP 是应用
协议；`gateway_agent`、`gateway_session` 等 Bridge 才能调用 Harness 服务。三层不得合并，
以便一个应用协议复用多种 Transport，一个 Transport 也能承载多种协议。

## 插件包与父子插件

目录用于发现和归属，不定义运行时所有权：

- Definition、Provider 和 Consumer 可以位于同一能力目录，但通常是同级插件包。
- 依赖同一个 Service 不表示 Fiber 父子关系。
- 可独立配置、替换、复用或由 Loader 直接引用的插件使用独立包。
- 只在一个父插件内部使用、没有独立配置和复用价值的私有子插件可以放在该包的
  `plugins/` 子目录中。
- `bundle` 包只负责选择和配置子插件，不复制子插件领域逻辑。

例如 OpenAI-compatible gateway 的运行时组合可以是：

```text
gateway_openai_api                   # composition 父插件
├── gateway                          # Definition
├── gateway_router
├── gateway_http_server
│   ├── gateway_http
│   └── gateway_sse
├── gateway_openai                   # 应用协议
├── gateway_agent                    # Harness bridge
├── gateway_auth
└── gateway_rate_limit
```

这棵树是 Fiber 所有权示例；只有组合插件实际通过 `ctx.plugin()` 挂载，或 Loader 使用
`children` 声明时才成立。

## 归类规则

新增包依次回答：

1. 它是否仅实现 Cordis 运行时而不认识 Harness 领域？是则进入 `dsh.cordis`。
2. 默认 profile 缺少它时，Harness 是否仍然完整？否则进入 `dsh.core`。
3. 它是否为替代 Provider、外部集成、可选能力或非默认应用？是则进入 `dsh.plugins`。
4. 它是否拥有独立配置或生命周期？是则建立独立插件包，否则保留为所属包的内部模块。

默认组合是 `core`/`plugins` 边界的权威证据。插件从可选变为默认或从默认移除时，应移动其
目录并一次性更新调用方；预发布阶段不保留旧 import 路径兼容层。

## 迁移约束

已实施的首轮物理迁移作为一次完整架构改动执行。后续跨分区移动仍必须至少同时更新：

- 所有 Python import、`__all__` 和 Loader `<module>:plugin` 引用；
- 插件 README、测试路径、构建包发现和类型检查配置；
- `docs/architecture.md`、本规范、迁移台账和调试文档；
- `.vscode/launch.json` 中受影响的测试路径；
- Provider/Consumer 契约测试与最小真实组合测试。

新增里程碑直接遵循三分区布局，但不提前建立候选空目录。默认 profile 在 M4 成为权威证据；
在此之前，尚未实现能力的归属只是提案，不能作为能力已交付或兼容性承诺。
