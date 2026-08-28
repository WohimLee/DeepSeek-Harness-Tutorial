# dsh.cordis

DeepSeek Harness Python 的插件运行时。它提供 Context、Fiber、Effect、事件、Service、配置
验证与声明式 Loader，是所有 Harness 插件的生命周期基础。

## 主要组件

- `Context`：服务解析、事件调用、派生作用域和子插件挂载。
- `Fiber`：一次插件挂载及其依赖驱动的激活 epoch。
- `EffectScope`：拥有并逆序撤销插件注册与异步资源。
- `EventsService`：emit、bail、serial、parallel 和 waterfall。
- `Service` / `ReflectService`：作用域化服务提供、查找与依赖通知。
- `dsh.cordis.loader`：安全解析、include/overlay 组合、entry tree 与配置重载。

## Harness 所需不变量

- 注册和子 Fiber 由当前 Fiber 所有，父卸载时递归撤销。
- 硬依赖缺失时 Fiber 保持 pending；Provider 替换后 Consumer 使用新 epoch 重启。
- 插件激活失败回滚本轮 Effect，清理错误不覆盖原始激活错误。
- waterfall 只有显式调用 `next_` 才继续下游。
- Loader 禁用父 entry 时不挂载其子树；配置更新失败保留原激活。

## 测试

测试位于 `dsh/cordis/tests/`，覆盖 Harness 依赖的生命周期、并发与 Loader 契约：

```bash
uv run pytest dsh/cordis/tests
```

Cordis 是运行时基础设施，不直接向模型提供 prompt、schema 或消息，因此没有直接 Model
Experience，也不改变模型请求前缀或 KV Cache。

## Known Limitations and Deferred Work

- 当前契约测试以 Python Harness 所需语义为边界，尚未形成与上游 vendored Cordis 全部测试
  的逐项映射。
- Loader 已支持显式 allow policy，但应用级 profile、插件发现和发布策略将在 headless 组装
  阶段确定。
