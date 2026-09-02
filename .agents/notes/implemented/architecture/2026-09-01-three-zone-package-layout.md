# Agent Note: 将 DSH 包目录收敛为 Cordis、Core 与 Plugins 三个分区

Status: implemented

## Problem

迁移前 Python 插件全部位于 `dsh.<plugin_name>`，随着 Session Provider、执行环境、外部 Agent、
Messaging 和多协议 Gateway 增加，顶层包名将同时承担领域、角色、默认性和厂商信息，无法从
物理位置判断一个插件是否属于默认 Harness。原 TypeScript 仓库按几十个能力组平铺，直接复制
会把上游 workspace 数量变成 Python 顶层目录数量。

目录也容易被误解为 Cordis 父子关系。Definition、Provider 和 Consumer 通常通过服务连接，
而不是互相拥有生命周期；需要在目录设计中保留这种区别。

## Decision

将 `dsh` 产品包的一级目录收敛为 `cordis`、`core` 和 `plugins`：

- `dsh.cordis` 只包含 Cordis 插件运行时，不认识 Agent、Session、LLM 或 Tool。
- `dsh.core` 包含默认 profile 正常运行所需的完整 Harness 套件，包括默认 Provider、策略和
  应用组合。
- `dsh.plugins` 包含替代 Provider、外部平台集成、可选执行能力、非默认应用、示例和实验。

领域下沉到后续层级。`core` 使用 runtime、model、session、execution、context、
collaboration、delegation、knowledge、storage、configuration、policy、application 和
internal；`plugins` 使用 providers、execution、agents、integrations、automation、extensions、
applications、examples 和 experimental。

Gateway 在 `plugins.integrations.gateway` 下进一步分为 core、transports、protocols、policies、
bridges 和 bundles。HTTP、WebSocket、SSE、MQTT、WebRTC 是传输机制；OpenAI、JSON-RPC、ACP、
MCP 是应用协议；Bridge 负责连接 Agent、Session、Tools 和事件。Messaging 使用公共消息
Definition 加各平台 Provider，并与完整应用 bundle 分离。

目录不隐式创建 Fiber 父子关系。只有 `ctx.plugin()` 和 Loader `children` 决定生命周期所有权；
普通能力目录中的 Definition、Provider、Consumer 默认是兄弟插件。目标结构和详细职责见
[`docs/package-layout.md`](../../../../docs/package-layout.md)。

迁移已在预发布阶段一次性更新所有 import、Loader 配置、测试、文档和调试路径，不提供旧模块
兼容层。旧的 `dsh.<plugin_name>` ABI 未保留兼容层，后续也不预建候选空目录。

## Alternatives considered

**继续使用全部顶层 `dsh.<plugin_name>` 包。** 初期 import 较短，但插件增长后无法从目录区分
默认套件、替代 Provider 和外部集成，也缺少稳定的领域导航。

**完全复制 TypeScript 的 `packages/<group>/<package>`。** 便于逐项对照上游，但会将上游历史
workspace 分组直接固化为 Python 公共结构，且不能清楚区分默认套件与可选扩展。

**按 Definition、Provider、Consumer 建一级目录。** 角色边界明确，但会拆散同一能力族；一次
文件系统或 Gateway 改动需要跨多个远距离目录。

**用目录嵌套表示父子插件。** 导航直观，但静态路径不能表达 Loader overlay、作用域隔离和
部署时组合，会让服务依赖被误认为生命周期所有权。

## Implemented evidence

- `dsh` 产品代码只使用 `cordis`、`core`、`plugins` 三个一级分区。
- M0–M2 默认运行时位于 `core`；可选 scripted Provider 位于 `plugins`。
- 每个独立插件仍导出唯一 `plugin` 入口，并拥有包级测试和 README。
- 所有 import、测试、构建发现、文档和 VS Code 调试引用已更新，未保留旧路径兼容包。
- 全量测试、Ruff、mypy、wheel 构建与安装产物 import smoke test 通过。
- Gateway、Messaging 等尚未实现的深层目录只是候选分类，不能作为已交付 API。

## Risks

- 默认 profile 边界可能随产品选择变化，导致插件在 `core` 与 `plugins` 之间移动；默认组合必须
  作为权威来源并在变更时同步验证。
- 深层 import 路径增加输入成本；公共 API 应由每个插件包明确导出，不能通过聚合入口隐藏
  插件生命周期。
- 一次性迁移影响构建、测试与文档引用，拆分提交可能产生不可运行的中间状态。
- Gateway 和 Messaging 当前尚未在 Python 版实现，目录只是约束未来落点，不能作为能力已交付
  的声明。
