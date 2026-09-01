# `dsh.agent`

M2 的 Agent Definition/registry。`agents` 服务保存活动 Agent；每个 Agent 暴露只读 inbox
快照、`followup()`、`cancel()` 与可等待的 `when_idle()`。注册由调用方 Fiber 所有。

Agent 本身不调用模型、不组装 prompt，也不维护模型历史；这些分别属于 Agent Loop、System
Prompt 和 Session。`agent/status` 是实时状态通知，不进入模型历史。M2 只组装单 Agent、
next-turn followup 和整轮取消；steering、maintenance、恢复与多队列语义延期。
