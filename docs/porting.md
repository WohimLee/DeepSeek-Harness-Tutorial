# TypeScript → Python 迁移台账

本文件记录复现范围、顺序和验证依据。状态只使用：`待分析`、`进行中`、`已实现`、
`已验证`、`暂不移植`。其中“已实现”表示代码存在，“已验证”才表示已有足够行为证据。

## 原则

- 以上游公开行为、架构文档、测试和 fixture 为基准，不以文件数量衡量完成度。
- 先迁移底层协议与最小 Provider，再迁移 Consumer 和完整应用组装。
- Python API 可以采用 async context manager、Protocol、dataclass 等惯用表达，但差异必须明确。
- 每次迁移更新本表，并在“证据”列链接本仓库测试或记录上游来源。

## 路线图

| 阶段 | 上游范围 | Python 落点 | 状态 | 证据 / 下一步 |
|---|---|---|---|---|
| 0 | vendored Cordis core | `dsh/cordis/` | 已实现 | 补齐与上游 Cordis 生命周期的契约测试 |
| 0 | Cordis config loader / composition | `dsh/cordis/loader/` | 已实现 | 验证 overlay、环境变量、安全策略与重载 |
| 1 | `packages/core/session` | `dsh/session/` | 待分析 | 提取事件格式、append/fork/projection 行为 |
| 1 | `packages/llm/llm` | `dsh/llm/` | 待分析 | 定义流式事件和 adapter 协议 |
| 1 | `packages/core/system-prompt` | `dsh/core/system_prompt/` | 待分析 | 提取片段排序、schema 组装规则 |
| 1 | `packages/core/tools` | `dsh/tools/` | 待分析 | 提取注册、作用域和三段执行流水线 |
| 2 | `packages/core/agent` | `dsh/core/agent/` | 待分析 | 设计 inbox、状态与实时事件 |
| 2 | `packages/core/agent-loop` | `dsh/core/agent_loop/` | 待分析 | 复现 turn/step、工具续跑、取消和恢复 |
| 2 | DeepSeek LLM provider | `dsh/llm/deepseek/` | 待分析 | keyless fake provider + 可选真实 API 测试 |
| 3 | filesystem / shell / approval | 对应 `dsh/` 子包 | 待分析 | 按完整 seam 逐项迁移 |
| 3 | profile / boot / headless CLI | `dsh/app/` | 待分析 | 建立最小可运行组装和端到端 transcript |
| 4 | API、SDK、Web Client | 待定 | 暂不移植 | 核心 headless 路径稳定后重新评估 |

## 已知差异

- Python 最低版本为 3.12，使用 `asyncio` 表达异步生命周期。
- Python 包采用 `dsh.*` 命名空间，不复制上游 npm workspace 包名。
- 上游本地路径只用于开发对照；Python 构建和测试不得依赖该目录存在。
- 项目处于预发布阶段，当前不承诺读取上游持久化格式。

## 单项迁移记录模板

迁移模块时在相应表项下补充：

```markdown
### <能力名称>

- 上游来源：`packages/...`
- 可观察行为：...
- Python API：...
- 有意差异：...
- 验证：`tests/...`
- 未决问题：...
```
