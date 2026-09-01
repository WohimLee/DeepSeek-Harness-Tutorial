# DeepSeek Harness Python

DeepSeek Harness Python（`deepseek-harness-py`）是对原 TypeScript 项目
`deepseek-harness` 的 Python 复现。项目以原 TypeScript
实现的外部行为和架构约束为基准，而不是逐行翻译源码。

原项目是一个由 Cordis 驱动的插件化 Agent Harness：模型适配器、会话、工具、Agent
Loop、能力提供方和应用入口都由插件组合。这个仓库延续“一切皆插件”的设计，并使用
`asyncio`、类型标注和 Python 原生协议表达相同的生命周期与扩展机制。

> 当前状态：最小 Harness 主干建设阶段。`dsh.cordis` 已通过 Harness 生命周期基线，
> `dsh.llm`、`dsh.llm_scripted` 与内存 `dsh.session` 已完成首条 keyless 日志投影竖切，
> System Prompt、Agent 与无工具 Agent Loop 已完成 M2 流式轮次。
> 项目尚未承诺稳定 API 或数据格式兼容性。

## 目标

- 保持原项目的关键运行语义：插件生命周期、服务注入、可逆副作用和事件流水线。
- 建立可替换的 Agent Harness 能力层，而不是把行为集中到不可扩展的核心类中。
- 用契约测试和端到端场景证明 Python 与 TypeScript 基准实现的行为一致。
- 提供符合 Python 生态习惯的 API；不机械复制 TypeScript 类型系统和包布局。

## 非目标

- 不追求 TypeScript 源码的逐行或逐文件翻译。
- 不在早期阶段保证与原项目所有内部 API、磁盘格式或 Web UI 完全兼容。
- 不先实现前端；当前优先级是 Cordis、核心 Agent Loop、LLM、工具和会话能力。

## 仓库结构

```text
dsh/
  cordis/             Python Cordis 运行时与声明式配置 loader
  agent/              Agent inbox、状态与 registry
  agent_loop/         默认无工具 Agent Loop Consumer
  llm/                LLM seam 与 adapter registry
  llm_scripted/       确定性 keyless Provider
  system_prompt/      有序 System Prompt registry
  tools/              工具注册与执行流水线（规划中）
  session/            内存会话事件日志与消息投影
  app/                CLI / headless 组装入口（规划中）
tests/                 单元、契约和集成测试
docs/architecture.md   Python 目标架构与关键不变量
docs/porting.md        TypeScript → Python 迁移策略与进度
.agents/               Agent 协作说明与决策记录
AGENTS.md              仓库级工程约束
```

实际存在的模块以源码为准；标注“规划中”的目录会在对应能力开始迁移时创建。

## 快速开始

项目要求 Python 3.12+，推荐使用 [uv](https://docs.astral.sh/uv/)：

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run mypy dsh
```

使用 VS Code 时可直接从“运行和调试”视图选择 Harness、Cordis 生命周期或当前 pytest
文件后按 F5；断点建议和状态观察项见 [F5 调试指南](docs/debugging.md)。

最小 Cordis 示例：

```python
import asyncio

from dsh.cordis import Context


async def main() -> None:
    ctx = Context()

    def plugin(plugin_ctx: Context, config: object) -> None:
        plugin_ctx.provide("answer", 42)

    fiber = ctx.plugin(plugin)
    await fiber.wait()
    assert ctx.answer == 42
    await ctx.aclose()


asyncio.run(main())
```

## 开发方式

开始改动前先阅读 [AGENTS.md](AGENTS.md) 和
[架构文档](docs/architecture.md)；新增插件遵循
[插件开发规范](docs/plugin-development.md)。移植新模块时，在
[迁移台账](docs/porting.md) 中记录来源、Python 落点和验证证据；非局部设计决策先在
`.agents/notes/{lifecycle}/{class}/` 记录 Agent Note；重大未来方案从 `proposed/` 开始，
随改动完成的决定记录在 `implemented/`。

## 上游基准

本地开发默认参考：

```text
/Users/wohim/Desktop/DockerVol/ubuntu22.04/wohim/AwsomeAgents/deepseek-harness
```

这个绝对路径只用于开发对照，不得写入运行时代码。若本地不存在该目录，仍应能安装、
测试和运行本项目。
