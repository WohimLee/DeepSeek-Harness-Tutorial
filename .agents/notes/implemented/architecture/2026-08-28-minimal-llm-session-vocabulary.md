# Agent Note: M1 先固定最小 LLM 与 Session 共享词汇

Status: implemented

## Problem

Agent Loop、Session 和 Provider 必须共享消息、内容块和 raw stream 词汇。如果先在各插件中
建立临时 dict，后续工具调用、回放和持久化会需要同时迁移多份表示。反过来一次性移植上游
完整 LLM discovery、prepared call、surface replacement 和 Session persistence，会在首条
可运行请求之前固化大量尚无 Python Consumer 的 API。

## Decision

M1 在 `dsh.core.model.llm` 中定义不可变的 provider-neutral message、source、content block、stream
chunk、finish reason、usage 与 GenerateRequest。`LlmRuntime` 只拥有 adapter 路由注册和
`llm/stream` waterfall，Provider 异常转换为唯一终止 error finish，缺失 finish 自动补为 stop。

`dsh.core.runtime.session` 使用带连续 seq 的只追加内存事件。模型历史只投影 `user/message`、
`assistant/message` 和 `tool/result`；raw `assistant/chunk` 与 turn/step bracket 留在日志中但不
成为消息。按事件验证消息 role/source，避免错误表示进入未来持久化边界。

`dsh.plugins.providers.model.llm_scripted` 是独立 Provider 插件，通过配置按顺序产生确定性文本响应。它不进入真实
应用默认组合，只为 keyless 测试、示例和 transcript 提供可重复请求。

M1 有意不实现 seed/fork/persistence、request header、model discovery、retry、replay metadata
和完整 structured failure；这些字段只有在对应 Consumer 进入主干时扩展。

## Alternatives considered

**用无类型 dict 先打通请求。** 初期更短，但消息 role/source、工具调用关联和 finish 终止
规则无法由类型或构造函数保护，持久化前还要进行破坏性迁移。

**完整复制上游 LLM 与 Session API。** 接口表面更像上游，但多数功能当前没有 Provider、
Consumer 或验收场景，违反按现实需求建立抽象的项目规则。

**把 scripted adapter 放进 `dsh.llm.testing`。** 它实际上具有独立配置和 Fiber 生命周期；
使用 `dsh.plugins.providers.model.llm_scripted` 更符合一个插件一个 import package 的统一布局。

**让 Agent Loop 维护自己的 message list。** 省去初期投影，但破坏“模型可见即已记录”，
恢复、fork 和 transcript 会观察到不同历史。

## Consequences

M2 可以直接以 `Session.derive_messages()` 构造 GenerateRequest，并通过 BlockAssembler 同时保留
raw chunk 与最终 assistant message。Provider 与 Session 仍然互不导入具体实现，只共享
`dsh.core.model.llm` 词汇。

当前 dataclass 是预发布 Python API；加入图片、replay 或 surface replacement 时允许整体更新
构造器和测试，但不得引入旁路历史或让 Provider-specific wire 值进入核心消息。
