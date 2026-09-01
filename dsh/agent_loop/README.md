# `dsh.agent_loop`

M2 的默认 Consumer，通过 `agentLoop` 服务创建 Agent，并串行驱动一次无工具 turn。硬依赖
`agents`、`llm`、`sessions` 和 `systemPrompt`。每轮先记录 turn/step 与用户消息，再完全从
Session 投影请求历史，组装 system prompt，记录全部 raw chunk 和成功的 assistant message，
最后记录 step/turn 收尾。

Provider 的 `error`/`aborted` finish 不写成功 assistant message，失败保存在 `Agent.last_error`
并发送实时 `agent/request-error`。活动任务由插件 Fiber Effect 所有，卸载会取消并等待静止。
M2 每轮只有一个 step；tool call 续跑、请求重试、steering 和并发策略属于后续里程碑。
