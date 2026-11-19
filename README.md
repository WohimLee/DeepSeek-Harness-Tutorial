# DeepSeek Harness 学习笔记

这个仓库用于学习 DeepSeek Harness 和基于它构建的 Super-agent 研究原型。以官方源码、文档和测试为依据，沿着真实调用链弄清楚应用如何启动、插件如何协作、一轮 Agent 请求如何执行，以及仓库事件如何触发和推进一项编程任务。

- **DeepSeek Harness**：学习 profile、Cordis 插件、会话、模型调用和 Agent Loop。[上游仓库](https://github.com/deepseek-ai/deepseek-harness) · [官方架构文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md)
- **Super-agent**：学习如何把 GitHub 和可选的飞书接入做成 Harness 插件包，为单个 GitHub 仓库处理任务。[上游仓库](https://github.com/deepseek-ai/dsh-superagent-prototype)

## 学习目标

1. **应用入口与启动**。梳理请求从哪里进入，以及 profile 和 bundle 如何组装运行所需的插件。
2. **Cordis 插件机制**。理解插件如何挂载和卸载，如何提供与依赖服务，以及事件和副作用如何随插件生命周期管理。
3. **Agent 运行链路**。跟踪一轮请求从进入会话到构造模型上下文、接收流式响应、执行工具，再到记录结果的过程。
4. **Super-agent 任务编排**。跟踪一条 GitHub Issue 评论如何经过事件接入和授权、触发或续接 Ticket、交给 Worker 会话执行，再回到原讨论串回复。梳理这些步骤分别由 Super-agent 和 Harness 的哪些模块负责。

第一阶段从一个调用入口入手，先跟完一轮无工具请求，再跟踪一次带工具调用的轮次。记录用到的上游版本、源码入口和关键事件，方便回看和复现。

第二阶段从白名单用户在 GitHub Issue 中 `@` Agent 的场景入手，顺着 **Source → Engine → Ticket → Worker → 回帖或 PR** 对照源码和测试。再看 PR 后续评论如何回到同一个 Ticket，以及主动规则在 `observe` 模式下如何记录候选任务。飞书作为另一种 Source，用来对照共用的任务链路。[架构与源码索引](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/007-architecture.md) · [安装与验证](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/SETUP.md)

## 笔记

- [调用方式](Tutorial/调用方式.md)记录了已有的对外调用入口和本地安装观察。笔记中的命令和运行状态对应当时观察的版本与环境。
