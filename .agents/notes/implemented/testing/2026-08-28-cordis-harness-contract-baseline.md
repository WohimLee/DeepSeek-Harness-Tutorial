# Agent Note: Cordis 以 Harness 所需契约作为首个验证基线

Status: implemented

## Problem

`dsh.cordis` 已有 Python 实现，但仓库只有包导入烟测。继续实现 Session、LLM 和 Agent Loop
会把服务替换、父子所有权、异步清理或 Loader tree 中的潜在错误传播到所有插件。逐项复制
上游 Cordis 的全部测试范围较大，也不能优先证明 Python Harness 当前真正依赖的语义。

## Decision

M0 先建立一套位于 `dsh/cordis/tests/` 的 Harness 契约基线。它验证：

- Provider 出现、移除和替换驱动 Consumer Fiber 在 pending/active 之间转换；
- 父 Fiber 撤销子 Fiber，父激活失败回滚子插件与已安装 Effect；
- Effect 失败 setup 逆序回滚，重复 close 幂等，取消外层 waiter 不取消内部清理；
- waterfall 按注册顺序嵌套，且只有显式 `next_` 才继续；
- 监听器与其他注册随拥有它的 Fiber 撤销；
- Loader entry children、禁用子树、叶配置更新和失败后保留旧激活；
- YAML 不执行 Python tag，环境变量、include cycle 和 overlay deep merge 行为确定。

这些是后续 Harness 插件可以依赖的最低运行时契约。根 `tests/` 继续只保存跨包烟测，Cordis
契约由 Cordis 包自身拥有。

## Alternatives considered

**先实现 Harness，遇到 Cordis 问题再补测试。** 这会让生命周期缺陷首先表现为 Session 或
Agent Loop 的间歇故障，难以判断所有权根因。

**完整翻译上游 Cordis 全部测试后再开始。** 覆盖更广，但会延迟首个 Harness 闭环；部分
JavaScript 特有行为也不是 Python 运行时的当前契约。

**只测试公开 happy path。** 无法证明 HMR/替换、失败回滚和取消清理，而这些正是插件化
Harness 最容易泄漏资源的路径。

## Consequences

M0 现在由 17 个包内测试保护，并与 Ruff、严格 mypy 一起通过。后续 Cordis 改动必须保持这
套契约；发现新的 Harness 依赖语义时在对应文件补充回归测试。

这不表示 Python Cordis 已与上游所有内部行为逐项等价。尚未映射的上游特性按实际 Consumer
需要逐步加入，且每项等价声明仍需指向上游测试或可重复对照证据。
