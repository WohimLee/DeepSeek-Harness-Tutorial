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

## 诊断日志

`dsh.cordis.logger` 暴露一个进程级 Loguru logger 单例。Cordis 内部模块直接调用
`logger.info(...)` 记录主生命周期；logger 不属于 Context、Fiber 或 EffectScope。默认关闭，
VS Code 仓库内的 F5 配置会自动开启。

```bash
DSH_CORDIS_LOG=1 uv run pytest dsh/cordis/tests -s
```

`DSH_CORDIS_LOG` 接受 `1`、`true`、`yes` 或 `on`。不设置它，或将其设为 `0`，即可整体
关闭。当前教学日志只使用 `INFO`，激活失败使用 `ERROR`。

也可以在运行时控制：

```python
from dsh.cordis import set_cordis_logging

set_cordis_logging(True)
set_cordis_logging(False)
```

当前只保留插件挂载、依赖等待、激活 epoch、Fiber 状态迁移、服务提供/移除和激活失败，
用来阅读“挂载 → 等待 → 激活 → 服务可用 → 卸载”主线。事件逐次派发、Context.get、refresh
调度等高频细节不打印。日志也不输出模型正文或原始配置内容。

## Known Limitations and Deferred Work

- 当前契约测试以 Python Harness 所需语义为边界，尚未形成与上游 vendored Cordis 全部测试
  的逐项映射。
- Loader 已支持显式 allow policy，但应用级 profile、插件发现和发布策略将在 headless 组装
  阶段确定。
