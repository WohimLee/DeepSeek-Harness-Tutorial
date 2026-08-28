# F5 调试指南

仓库已提供 VS Code 的 `debugpy` 配置。先执行一次：

```bash
uv sync --dev
```

然后打开“运行和调试”视图，选择配置并按 F5。所有配置都使用仓库的
`.venv/bin/python`，以项目根目录为工作目录，并开启 `asyncio` 调试模式。
这些 F5 配置还会设置 `DSH_CORDIS_LOG=1` 和 `DSH_CORDIS_LOG_LEVEL=DEBUG`，因此终端会同步
显示插件挂载、Fiber 状态变化、依赖解析、服务变化与事件调度。普通测试和应用运行默认
不输出这些诊断日志；开关与运行时 API 见 [`dsh.cordis` 文档](../dsh/cordis/README.md#诊断日志)。

`Harness: 当前阶段` 是长期稳定入口：它运行根 `tests/` 下所有跨插件组装与应用级测试。
随着 Harness 迭代，这个名字和启动方式保持不变，新阶段把自己的最小可运行竖切加入根
`tests/` 即可。阶段专属配置则作为历史学习路线保留，例如
`阶段 M1: 日志与模型协议`。

## 推荐调试顺序

### 1. `Cordis: Provider 生命周期`

这个场景展示 consumer 如何随 provider 出现、移除和替换而在
`PENDING → LOADING → ACTIVE → UNLOADING → PENDING` 之间变化。

建议依次在这些位置设置断点：

- `dsh/cordis/context.py` 的 `Context.plugin()`：插件挂载入口。
- `dsh/cordis/fiber.py` 的 `Fiber.bootstrap()`：建立父 Fiber 对子 Fiber 的所有权。
- `dsh/cordis/fiber.py` 的 `Fiber._resolve_dependencies()`：解析 `inject`。
- `dsh/cordis/fiber.py` 的 `Fiber._activate()`：插件激活和 Effect 作用域创建。
- `dsh/cordis/fiber.py` 的 `Fiber._unload()`：依赖消失时撤销本轮激活。
- `dsh/cordis/reflect.py` 的 `ReflectService.provide()`：服务注册和变更通知。

重点观察 `fiber.state`、`fiber.dependencies`、`fiber._epoch`、
`fiber.provided_names` 和 `fiber.effects.effects`。

### 2. `Cordis: 父子 Fiber 回滚`

这个场景让父插件在创建 Effect 和子插件后故意失败。观察父 Fiber 的 EffectScope
如何同时拥有普通清理动作和子 Fiber，并在失败时回滚。重点断点是
`Fiber._activate()` 的异常分支以及 `EffectScope.close()`。

### 3. `阶段 M1: 日志与模型协议`

这是当前最接近 Harness 的完整路径，但编排仍写在集成测试中，还不是 Agent Loop：

```text
Context
  → 挂载 LlmRuntime / SessionStore / ScriptedPlugin
  → Session 记录 user/message
  → LlmRuntime.stream() 路由到 ScriptedAdapter
  → BlockAssembler 组装流
  → Session 记录 assistant/message
  → derive_messages() 重建下一次模型上下文
```

建议在这些位置设置断点：

- `tests/test_m1_log_projection.py` 的每个 `session.append(...)`。
- `dsh/llm/service.py` 的 `LlmRuntime.stream()` 与 `_stream()`。
- `dsh/llm_scripted/plugin.py` 的 `ScriptedAdapter.stream()`。
- `dsh/llm/assembler.py` 的 `BlockAssembler.push()`。
- `dsh/session/service.py` 的 `Session.append()` 和 `derive_messages()`。

### 4. `Pytest: 当前文件`

打开任意测试文件后选择此配置按 F5，可调试整个当前文件。若只想调试单个测试，推荐在
VS Code 测试面板中点击该测试旁的“调试测试”按钮。

## 后续阶段如何维护

每个 Harness 里程碑达到“已验证”前，需要同时完成以下调试资产：

1. 在根 `tests/` 增加该阶段的最小组装测试，让 `Harness: 当前阶段` 自动覆盖它。
2. 若阶段引入重要新状态机或调用链，在 `.vscode/launch.json` 增加一个阶段专属配置；已有
   配置不删除，除非对应行为已从项目移除。
3. 在本文件补充调用链、推荐断点和关键观察变量。
4. 在 `docs/porting.md` 的阶段验证记录中写明对应测试和 F5 配置名称。

插件内部的局部行为仍放在 `dsh/<plugin>/tests/`，用 `Pytest: 当前文件` 或测试面板调试；
只有跨插件、能说明当前 Harness 整体进展的场景才进入根 `tests/`。

## 调试器里看什么

Cordis 中三个概念不要混在一起：

- `Context` 是插件可见的作用域视图，派生 Context 共享根注册表和事件系统。
- `Fiber` 是一次插件挂载及其激活周期；provider 更换会产生新的依赖 epoch。
- `Effect` 是一次激活拥有的可逆副作用；Fiber 卸载时按作用域统一撤销。

`Context.get()` 对 `Service` 返回的是绑定到调用方 Context 的 `ServiceView`。所以在调试器中
看到 `llm` 或 `sessions` 的运行时类型是 `ServiceView` 属于当前设计，并非解析到了错误对象；
其 `_target` 才是实际的 `LlmRuntime` 或 `SessionStore`。
