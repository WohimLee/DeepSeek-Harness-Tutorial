# Agent 工作区

`.agents/` 保存面向协作 Agent 的过程信息；正式工程约束位于根目录 `AGENTS.md`，当前
架构事实位于 `docs/`。

## 内容

- `notes/{lifecycle}/{class}/`：按生命周期与决策类别保存 Agent Note；完整目录约定见
  `notes/README.md`。
- `notes/proposed/`：正在讨论、尚未形成工程约束的方案。
- `notes/implemented/`：已经采纳并落地，仍可解释当前实现的决策。
- `notes/rejected/`：经过评估但明确不采用的方案及原因。
- `notes/archived/`：已完成历史使命并冻结的已实现决策。
- `notes/README.md`：Note 的适用范围、状态流转和维护规则。

不要在这里保存临时聊天记录、执行日志、密钥或只能在单台机器使用的路径。短期任务计划
应留在任务系统中；只有值得后续维护者理解的决策才形成 Note。

## 开始任务

1. 阅读根 `AGENTS.md` 与相关架构文档。
2. 检查 `git status --short`，辨认并保留现有改动。
3. 在 `docs/porting.md` 找到上游来源和当前状态。
4. 选择最小相关测试作为基线，再开始修改。

## 完成任务

1. 运行与改动范围匹配的测试、lint 和类型检查。
2. 更新迁移台账及受影响文档。
3. 若引入非局部设计决策，重大未来方案写入 `notes/proposed/<class>/`，随当前改动完成的
   决定可直接写入 `notes/implemented/<class>/`；后续状态变化时保持类别并移动生命周期。
4. 汇报实际运行的命令和未解决风险，不把未运行的检查写成已通过。
