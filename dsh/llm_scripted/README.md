# dsh.llm_scripted

面向测试、示例和 keyless transcript 的确定性 LLM Provider。它向 `ctx.llm` 注册一个路由，
每次请求消费一条预配置文本并发出 `text-delta` 与 `finish(stop)`。

## Configuration

- `provider`：路由名，默认 `scripted`。
- `responses`：按请求顺序消费的字符串数组，必填；队列耗尽以 Provider error finish 结束。

硬依赖：`llm`。注册随本插件 Fiber 撤销。

## Model Experience

模型侧输出完全由 `responses` 决定；本插件自身不添加 prompt 或 schema。它只用于确定性测试，
不进入真实应用的默认组合。

## Known Limitations and Deferred Work

- 当前配置只表达文本响应；M3 工具闭环会增加结构化 chunk script，而不是把 Provider 行为
  写入 Agent Loop fixture。
