# DeepSeek Harness Python 架构

本文描述 Python 复现的目标架构、已实现边界和必须保持的不变量。原 TypeScript 项目的
`docs/architecture.zh.md` 是产品语义的主要参考；Python 实现允许采用不同的模块组织，
但不得静默改变可观察行为。

## 当前边界

目前已实现 `dsh.cordis` 及其声明式配置 loader。Harness 核心、LLM、工具、会话和应用
组装仍处于规划阶段。因此下文除 Cordis 章节外描述的是目标架构，具体进度以
[`porting.md`](porting.md) 为准。

## 分层

```text
CLI / Headless / API adapters                         应用入口
                    │
Profiles + configuration loader                      组合层
                    │
Agent Loop ─ Session ─ System Prompt ─ Tool pipeline 核心编排
                    │
LLM / FS / Shell / Web / Subagent / Approval seams   可替换能力
                    │
Cordis Context / Fiber / Effect / Events / Service   插件运行时
```

依赖只向下指向接口。应用入口负责选择插件与配置，能力 Consumer 只能依赖 Service
Definition，不直接导入 Provider。Provider 可以替换而不修改 Agent Loop。

## Cordis 运行时（已实现）

`dsh.cordis` 是插件树的生命周期内核：

- `Context`：插件可见的作用域视图，负责服务解析、事件与插件挂载。
- `Fiber`：一次插件挂载及其激活 epoch；依赖出现、消失或替换时重新评估生命周期。
- `Effect` / `EffectScope`：拥有注册资源并按生命周期撤销。
- `RegistryService` / `ReflectService`：规范化插件并解析隔离作用域内的服务实现。
- `EventsService`：提供 emit、bail、serial、parallel 与 waterfall 事件模式。
- `Service`：服务定义与上下文绑定。
- `dsh.cordis.loader`：解析 YAML/TOML、组合 overlay、安全解析模块并重载插件树。

关键不变量：插件贡献的资源由其 Fiber 所有；插件卸载后不可继续解析其服务或收到其监听；
依赖未满足时插件不激活；激活失败必须回滚本轮已安装的 Effect。

## Harness 核心（规划中）

核心由五个可独立测试与替换的部分构成：

- Session：仅追加事件日志，是回放、持久化和模型历史投影的事实来源。
- System Prompt：从插件贡献的片段与工具 schema 组装请求上下文。
- Tools：作用域化注册表，以及 pre-execute → execute → post-execute 流水线。
- Agent：活跃实例、inbox、状态和实时 `agent/*` 扩展事件。
- Agent Loop：一次轮次内驱动模型请求、工具执行与续跑的默认实现。

一个 step 是一次模型请求及其工具调用；一个 turn 包含零或多个 step。持久事实写入 Session，
进行中的拦截和观察使用实时 Agent/能力事件，二者不得混用。

## 能力 seam（规划中）

每项可替换能力包含三种角色：

| 角色 | 职责 | 示例 |
|---|---|---|
| Service Definition | 定义请求、结果、错误与服务协议 | `LLMService` |
| Provider | 实现协议并通过 Cordis 提供服务 | DeepSeek provider |
| Consumer | 将能力接入 Agent 或暴露为工具 | model caller / web tool |

默认值与配置归拥有它的 Provider；Consumer 不猜测 Provider 行为。部署可变参数来自经验证的
插件配置，协议常量和安全不变量可以固定在代码中。

## 事件与状态

- Session 事件记录持久事实，必须能够回放和投影。
- Agent 事件描述活跃轮次，可用于拦截、改写或观察。
- 能力事件给工具、文件系统、审批等 seam 添加策略。
- waterfall 是 around-middleware；监听器只有调用 `next_` 才会继续下游。

最重要的产品不变量是“模型可见即已记录”：模型请求中的消息、注入上下文、工具结果等必须
可由 Session 日志确定性重建。添加模型可见输入时必须同时设计对应事件及投影。

## 错误、取消与清理

- 配置自身可判定的错误在加载阶段失败；依赖相关错误在最早能够判断时失败。
- 取消是正常生命周期路径。清理函数应可等待且可重复调用，不吞掉 `CancelledError`。
- 激活和回滚同时失败时保留两者，例如使用 `BaseExceptionGroup`。
- 跨网络、进程、文件和持久化边界的错误转换为稳定的领域错误；内部编程错误不伪装成
  Provider 故障。

## 验证策略

测试分为三层：

1. 单元测试验证数据结构、事件模式和局部状态转换。
2. 契约测试让多个 Provider 运行同一套 Definition/Consumer 行为用例。
3. 组装测试通过真实 Cordis 插件树验证轮次、日志、工具和取消路径。

声称与上游等价时，测试应注明上游测试、fixture、文档段落或可复现对照脚本。Python
特有的 API 差异记录在迁移台账，不以隐式兼容逻辑掩盖。
