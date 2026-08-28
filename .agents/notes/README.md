# Agent Notes

Agent Note 记录代码本身难以表达、且未来改动必须知道的设计决策。它不是工作日志，也不
替代 `docs/architecture.md` 的当前状态说明。

以下情况应新增 Note：

- 改变公共 API、插件生命周期、并发/取消或持久化语义；
- Python 实现有意偏离 TypeScript 基准；
- 引入新的跨模块依赖方向或能力 seam；
- 在多个合理方案中作出会影响后续迁移的选择。

纯格式、局部修复、测试补充和无语义变化的重命名通常不需要 Note。

## 路径与命名

每份 Agent Note 的路径同时编码生命周期和类别：

```text
{lifecycle}/{class}/YYYY-MM-DD-short-title.md
```

日期是议题首次提出的日期。Note 在生命周期之间移动时保持文件名和类别不变，并修复所有
相对链接。生命周期/类别目录按需创建；空目录不要求进入版本控制，也不使用 `.gitkeep`。

## 生命周期目录

| 目录 | 含义 | 是否属于当前规范 |
|---|---|---|
| `proposed/` | 待讨论或待验证的方案 | 否 |
| `implemented/` | 已采纳并完成代码、测试及文档落地 | 是，但低于 `AGENTS.md`、当前架构文档和代码 |
| `rejected/` | 已明确否决，保留备选方案与否决原因 | 否 |
| `archived/` | 从 implemented 移出的低后续价值历史快照 | 否 |

目录是 Note 生命周期的主要来源，活动 Note 的 `Status:` 必须与所在目录一致；归档是唯一
例外，它保留 `Status: implemented` 并增加 `Archived: YYYY-MM-DD`。不要把 proposed Note
当作实施授权，也不要根据 rejected 或 archived Note 恢复旧行为。

## 决策类别

类别使用以下闭合集合；不要自行创建 `refactor`、`misc` 等重叠目录：

| 类别 | 适用范围 |
|---|---|
| `feature` | 新增用户或模型可见能力 |
| `bug-fix` | 修复缺陷或补齐已承诺行为 |
| `simplification` | 删除代码、行为或接口，不新增能力 |
| `architecture` | 已交付源码的模块关系、运行时语义与结构决策 |
| `process` | 工具链、策略、迁移和协作流程，不属于产品运行时 |
| `testing` | 测试基础设施、分层策略与验证方法 |

`architecture` 描述交付的代码如何组织和运行；`process` 描述围绕代码的开发方式。
重构如果只是移除复杂度归入 `simplification`；如果改变模块关系或运行时语义则归入
`architecture`。

## 生命周期

1. 尚未实施或只完成一部分的重大方案，使用 `template.md` 在 `proposed/<class>/` 创建
   Note；如果决定与实现已经同时完成，可以直接在 `implemented/<class>/` 记录已交付事实。
2. 方案落地且验证完成后，将文件移入 `implemented/<class>/`，状态改为 `implemented`，
   并把提案表述更新为实际交付的决定和验证证据。
3. 方案被否决时，将文件移入 `rejected/<class>/`，状态行改为
   `rejected — <简短原因>`；内容随后冻结。只有否决理由仍能阻止一个现实且有意义的错误
   时才保留 rejected Note，否则可以删除。
4. 只有 implemented Note 可以进入 `archived/<class>/`。归档时保留
   `Status: implemented`，增加归档日期；归档文件不再作为当前事实来源。不要归档
   proposed Note，过时提案应拒绝。

`implemented/` 中的 Note 应随对应实现更新路径、名称和默认值等事实，但不得把原决定改写
成另一个决定。决定被推翻时新建 Note 并交叉链接。`rejected/` 的正文在拒绝后冻结，但可
在理由不再有保留价值时删除；`archived/` 永久冻结，不编辑、移动或删除。当前事实始终以
代码、测试、`AGENTS.md` 和 `docs/` 为准。

活动清单由 `proposed/`、`implemented/` 和 `rejected/` 的目录树本身组成，不维护集中式
`INDEX.md`。`archived/` 是单独的历史集合，搜索当前决策时默认排除。
