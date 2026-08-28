# dsh.llm

Provider-neutral LLM Service Definition。它拥有 `ctx.llm` adapter registry、共享消息/内容块
词汇、raw stream 协议与 `BlockAssembler`；具体 Provider 位于独立插件。

## Service

- Context key：`llm`
- `register_adapter(providers, adapter)`：原子注册路由，随调用 Fiber 撤销。
- `providers()`：按注册顺序列出活动路由。
- `stream(request)`：通过 `llm/stream` waterfall 分发，并以一个 `finish` 结束。

Adapter 抛出的错误转换为 `finish(error)`；调用取消转换为 `finish(aborted)`。middleware 与
调用方错误不属于 Provider 结果。

## Model Experience

本插件不添加 prompt、schema 或消息；它只传递调用者组装的请求，因此没有直接 token 或
KV Cache 影响。

## Known Limitations and Deferred Work

- M1 只实现路由注册与流式分发；model discovery、retry policy、prepared call 和 replay
  metadata 随真实 Provider 需求补充。
