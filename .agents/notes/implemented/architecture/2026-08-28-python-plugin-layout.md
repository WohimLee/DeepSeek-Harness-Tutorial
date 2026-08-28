# Agent Note: Python 插件采用单 distribution 下的独立 import package

Status: implemented

## Problem

原 DSH 以一个 npm workspace package 表示一个插件，这同时提供独立 manifest、构建、导出
和依赖边界。Python 复现当前只有一个 distribution。如果机械复制为大量独立 Python
distribution，每个插件都需要重复构建元数据和发布协调；如果把所有插件写进少数大模块，
又会丢失插件入口、依赖和生命周期的清晰边界。

Cordis loader 已使用 `<module>:<attribute>` 解析插件，并支持 function、class 与带 `apply()`
的对象，因此需要确定官方插件的标准 import 路径和统一导出。

## Decision

本仓库发布一个 `deepseek-harness-py` distribution。每个具有独立配置或生命周期的官方插件
使用一个 `dsh.<snake_case_name>` import package，并从 `__init__.py` 导出唯一标准入口
`plugin`。Loader 统一引用 `dsh.<name>:plugin`。

Service Definition、Provider 与 Consumer 在需要独立演进或依赖不同时使用不同 import
package，例如 `dsh.shell`、`dsh.shell_local` 和 `dsh.tool_shell`。Python package 名采用
snake_case，插件诊断名采用 kebab-case；服务键在移植上游能力时保留既有领域词汇。

插件包只创建职责需要的文件。`plugin.py` 拥有入口，`config.py` 拥有完整配置解析，
`service.py` 拥有 Service Definition 或主要实现，`models.py` 存放运行时值，测试在
插件包内的 `tests/`。根 `tests/` 只验证跨插件组合和应用入口。每个产品插件拥有 README，
但不拥有独立 `pyproject.toml`；构建时排除插件测试。

第三方插件使用独立 distribution `dsh-plugin-<name>` 和顶层 import package
`dsh_plugin_<name>`，不得向本项目的普通 `dsh` package 注入文件。自动 entry-point discovery
不是当前兼容承诺。

完整实现规范由 [`docs/plugin-development.md`](../../../../docs/plugin-development.md) 维护。

## Alternatives considered

**每个插件一个 Python distribution。** 边界最强，但在尚未稳定的单仓库复现阶段产生大量
重复 manifest、依赖解析和版本发布工作，不能提升运行时插件隔离。

**所有 Provider 放入 Definition 包的 `providers/`。** 文件较集中，但会让抽象能力包安装
具体 SDK 和系统依赖，并允许 Consumer 轻易反向依赖实现。

**所有插件放入 `dsh.plugins.<group>.<name>`。** 路径能表达上游 group，但 group 只是源码
容器而非运行时概念，会形成冗长 Loader 引用并偏离当前 `dsh.session`、`dsh.llm` 规划。

**依赖模块导入副作用自动注册。** 写法更短，但无法让 Cordis Fiber 拥有注册，也无法可靠
卸载、重载或在同进程组合多个隔离实例。

## Consequences

官方插件保持独立 import 与生命周期边界，同时共享一次构建、版本和质量门禁。插件数量增多
会扩大 `dsh` 顶层命名空间，但路径直接对应配置和诊断名，搜索成本低于额外 group 层。

Definition 不得导入 Provider，组合插件不得拥有子插件逻辑。所有插件必须显式导出 `plugin`，
通过 `name/inject/Config/apply` ABI 被 Cordis 解析，并用生命周期测试证明贡献可撤销。

组合插件可以用 `ctx.plugin()` 建立父子 Fiber 树。该嵌套只表达生命周期所有权：父 Fiber
撤销时递归撤销子 Fiber；服务依赖仍由 `inject` 表达，Provider 与 Consumer 默认作为同级
子插件通过服务连接。

如果未来某个官方插件需要独立发布，可以在保持内部模块职责的前提下迁出 distribution；在
出现该现实需求之前，不为假设的独立版本建立兼容层。
