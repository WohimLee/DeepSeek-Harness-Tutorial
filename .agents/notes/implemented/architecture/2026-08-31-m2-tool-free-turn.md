# Agent Note: M2 无工具轮次的最小边界

Status: implemented

## Decision

M2 采用三个独立生命周期单元：`dsh.system_prompt` 提供 `systemPrompt` registry，
`dsh.agent` 提供 `agents` registry 与 Agent 值，`dsh.agent_loop` 作为 Consumer 提供
`agentLoop`。Agent Loop 只从 Session 投影构造模型消息，不保存旁路历史。

每个 M2 turn 固定一个 step。成功 Provider call 记录 raw chunk 与 assistant message；in-band
`error/aborted` finish 只记录 raw finish、关闭 step/turn，并通过 `Agent.last_error` 与实时
`agent/request-error` 暴露失败。活动 driver task 由 Agent Loop Fiber 的 Effect 清理。

## Deferred

工具调用与续跑、steering、请求重试、prompt 动态 context/变量/scope、request header 持久化
不在 M2 暴露临时 API，分别在相应 seam 落地时实现。headless/CLI 仍属于 M4。

## Evidence

- 上游 `packages/core/agent-loop/tests/loop.spec.ts` 的简单轮次和事件边界。
- 上游 `packages/core/agent-loop/src/agent.ts` 的流组装与 error/aborted finish 分支。
- 上游 `docs/agent-lifecycle.md` 的 durable Session 与实时 `agent/*` 分工。
- Python `dsh/agent_loop/tests/test_service.py` 与 `tests/test_m2_tool_free_turn.py`。
