# DSH Python 插件开发规范

本文定义本仓库中 Harness 插件的统一入口、职责边界、目录组织、命名、配置、生命周期、
文档和测试要求。它将原 DSH 的 npm workspace 约定翻译为单一 Python distribution 下的
模块规范；Cordis 本身的 API 见 [`dsh/cordis`](../dsh/cordis)。

## 1. 原 DSH 插件标准是什么

原 DSH 中一个可装载单元通常是一个 npm package，位于
`packages/<group>/<package>/`。它至少包含 package manifest、TypeScript 配置、
`src/index.ts` 和 README，测试放在包级 `tests/`。插件入口有两种形式：

- Service 插件导出 Service class；类声明服务名、依赖与配置 schema。
- Function 插件导出 `name`、`inject`、`Config` 和 `apply()`。

比文件名更重要的是以下运行时约定：

1. 插件显式声明所需服务；依赖未满足时 Fiber 保持 pending。
2. 配置在激活前验证并补齐默认值，错误应尽早且明确地失败。
3. 注册是 Effect：服务、事件、工具、prompt section 等贡献由 Fiber 所有，卸载时撤销。
4. 可替换能力按 Service Definition、Provider、Consumer 组织；Consumer 不导入具体
   Provider。
5. 产品可见插件必须在真实组合中验证，注册表贡献还必须证明卸载后消失。
6. 插件 README 记录 API、配置、事件、模型可见影响、限制与延期事项。

Python 版保留这六条语义，但不复制每个 npm package 的构建文件和 TypeScript 声明合并。

## 2. Python 插件 ABI

### 2.1 统一装载入口

每个官方插件包必须从 `__init__.py` 导出名为 `plugin` 的唯一标准入口：

```python
from .plugin import plugin

__all__ = ["plugin"]
```

Loader 配置始终引用显式属性：

```yaml
- id: echo-tool
  module: dsh.tool_echo:plugin
  config:
    prefix: "Echo: "
```

禁止依赖“导入模块本身就完成注册”的副作用。导入插件包只定义对象；挂载 `plugin` 才能
改变 Context。

Cordis 当前接受函数、class 或带 `apply()` 的对象。官方插件选择如下：

- 定义并提供一个命名服务时，`plugin` 指向 `Service` 子类。
- 只注册工具、监听器、策略或组合子插件时，`plugin` 指向带元数据和 `apply()` 的对象。
- 极小的测试/示例插件可以直接使用函数；产品插件不通过给函数动态附加属性来声明配置。

### 2.2 Service 插件

Service class 同时是插件入口和 Service Provider：

```python
from dsh.cordis import Context, Service

from .config import Config


class GreetingRegistry(Service):
    """Own named greeting providers for the current Cordis scope."""

    provide = "greetings"
    inject = ("logger",)
    Config = Config

    def __init__(self, ctx: Context, config: Config) -> None:
        super().__init__(ctx)
        self.config = config


plugin = GreetingRegistry
```

服务键使用稳定的领域名。拥有多个具名成员的 registry 使用复数，例如 `tools`；单一
executor、policy、store 或 runtime 使用单数。不要只因为继承了 `Service` 就把类命名为
`SomethingService`，应优先选择 Registry、Store、Provider、Policy、Executor 等真实角色。

### 2.3 Function/object 插件

不提供新服务的产品插件使用显式对象，以便静态声明元数据：

```python
from dataclasses import dataclass

from dsh.cordis import Context

from .config import Config


@dataclass(frozen=True, slots=True)
class EchoToolPlugin:
    name = "tool-echo"
    inject = ("tools",)
    Config = Config

    def apply(self, ctx: Context, config: Config) -> None:
        ctx.tools.register(...)


plugin = EchoToolPlugin()
```

`name` 使用小写 kebab-case，作为诊断与配置中的稳定插件名；Python import package 使用
snake_case。`inject` 只列硬依赖。真正可选的服务通过 `ctx.get(name)` 显式查询，并在缺少时
实现文档声明的降级或失败行为，不要伪装成硬注入。

### 2.4 配置

配置使用不可变、带类型的值对象。标准库足以表达时优先采用 frozen dataclass；需要复杂
JSON Schema 或第三方校验器时，应先形成独立决策，不让某个插件私自规定全仓库框架。

```python
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Config:
    prefix: str = "Echo: "

    @classmethod
    def validate(cls, value: object) -> Self:
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise TypeError("config must be a mapping")
        prefix = value.get("prefix", "Echo: ")
        if not isinstance(prefix, str) or not prefix:
            raise TypeError("prefix must be a non-empty string")
        return cls(prefix=prefix)
```

插件通过 `Config = Config` 暴露 validator。validator 必须返回完整解析值；默认值在这里统一
解析，不在执行路径散落 `value or default`。部署可变选择必须进入配置，协议常量与安全
不变量留在代码中。配置自身可判定的错误在加载时失败。

无配置插件省略 `Config`，接收的 `config` 视为 `None`。不要为了形式制造空配置类。

### 2.5 生命周期与 Effect

所有注册贡献必须由挂载 Fiber 拥有：

```python
def apply(self, ctx: Context, config: Config) -> None:
    ctx.tools.register(...)
    ctx.on("tools/result", self._observe)
    ctx.effect(self._start_watcher, "tool-echo watcher")
```

注册 API 应直接返回 `Effect` 或 disposer，并把它附着到调用者 Context。插件自行启动的任务、
文件监听器、client、进程或临时资源必须通过 `ctx.effect()` / `ctx.effect_async()` 注册清理。
清理应可等待、可重复调用，并在返回前达到 quiescence：不再有回调、任务或后台写入。

不得在模块全局保存活动 Context、Service、task 或 client。只读常量、不可变 schema 和纯函数
可以放在模块级。

## 3. 官方插件目录组织

本仓库发布一个 `deepseek-harness-py` wheel，而不是为每个插件发布一个 distribution。
每个具有独立配置或生命周期的官方插件对应一个顶层 import package：

```text
dsh/<plugin_name>/
  __init__.py       唯一公共入口；导出 plugin 和明确支持的公共 API
  plugin.py         插件组装或入口 class/object
  config.py         Config 与配置错误；无配置时省略
  service.py        Service Definition 或主要 service；不需要时省略
  models.py         运行时数据值、请求、结果、事件 payload；不需要时省略
  errors.py         稳定领域错误；不需要时省略
  registry.py       动态注册表实现；确有该角色时使用
  invariant.py      包拥有的运行时关系检查；MVP 后建立 invariant 基础设施时启用
  README.md         插件 API、配置、事件、模型影响和限制
  tests/            插件自己拥有的测试，不进入发布 wheel
    test_config.py
    test_service.py
    test_plugin.py
    test_lifecycle.py  注册撤销、取消和清理证据
```

整个 `dsh` distribution 的类型标记统一放在 `dsh/py.typed`，子插件不重复放置。
仓库根 `tests/` 只放跨插件组合、Loader、CLI、构建与端到端 transcript 测试；能够只依赖一个
插件完成的测试必须放回该插件的 `tests/`。构建配置排除插件测试，测试不成为运行时 API。

这是可选文件清单，不是要求每个插件生成所有文件。小插件保持紧凑，例如：

```text
dsh/tool_echo/
  __init__.py
  plugin.py
  config.py
  README.md
  tests/
    test_plugin.py
    test_lifecycle.py
```

复杂模块按职责拆文件，不按“helpers”“utils”“manager”一类含混名称堆放代码。`models.py`
包含运行时 dataclass/enum；只有纯类型 Protocol/TypeAlias 才进入 `typing.py`。共享工具只有在
至少两个当前 Consumer 需要且依赖方向合理时，才提取到 `dsh.util_*`，不建立通用 `utils.py`。

### 3.1 命名映射

| 概念 | 规范 | 示例 |
|---|---|---|
| Python package | snake_case | `dsh.llm_deepseek` |
| 插件诊断名 | kebab-case | `llm-deepseek` |
| Context 服务键 | camelCase 或既有稳定键 | `llm`, `systemPrompt` |
| Service / model class | PascalCase | `DeepSeekProvider` |
| 配置类型 | `Config` | `Config` |
| Loader 引用 | `<module>:plugin` | `dsh.llm_deepseek:plugin` |

服务键与上游语义对应时保留上游键，避免移植期间出现两套词汇；Python 属性不适合直接表达
的 camelCase key 通过 `ctx.get("systemPrompt")` 或服务绑定访问，不能悄悄改名造成组合不兼容。

### 3.2 Capability seam 的物理拆分

Definition、Provider、Consumer 需要独立演进或具有不同依赖时，使用独立插件包：

```text
dsh/shell/          # Service Definition: ctx.shell 请求/结果/错误协议
dsh/shell_local/    # Provider: 本机 subprocess 实现，inject = ("shell",) 或注册到定义服务
dsh/tool_shell/     # Consumer: 模型工具 schema，inject = ("shell", "tools")
```

Provider 命名必须说明厂商、协议、环境或机制，例如 `llm_deepseek`、`session_sqlite`、
`shell_local`。Definition 使用能力名，不以首个 Provider 命名。Consumer 使用其真实表面，
例如 `tool_web`、`command_compact`。

如果三个角色只有一个 Consumer、一起变化且没有额外重依赖，可以暂时放在一个包中，但
代码仍分别定义协议、实现与消费入口；出现第二个 Provider 或独立发布需求时再物理拆分。

### 3.3 Composition 插件

组合插件只挂载子插件并转发自己拥有的配置：

```text
dsh/harness/
  __init__.py
  plugin.py
  config.py
  README.md
```

组合插件不得复制子插件逻辑、直接注册子插件拥有的服务，或选择应由应用入口决定的具体
后端。共享主干选择 Definition 与 Consumer；headless/API 等叶子入口选择 LLM、Shell、
持久化等 Provider。

### 3.4 父子插件与 Fiber 所有权

DSH 有父子插件。这里的“父子”是 Cordis Fiber 的生命周期所有权，不是 Python class
继承、import 关系或 Service Definition / Provider / Consumer 关系。

父插件在自己的 `apply()` 中调用 `ctx.plugin()`，得到一个子 Fiber：

```python
class HarnessPlugin:
    name = "harness"

    def apply(self, ctx: Context, config: Config) -> None:
        ctx.plugin(session_plugin, config.session)
        ctx.plugin(llm_plugin, config.llm)
        ctx.plugin(agent_loop_plugin, config.agent_loop)


plugin = HarnessPlugin()
```

其生命周期语义为：

- 子 Fiber 由父 Fiber 的 EffectScope 所有；卸载父插件会递归卸载所有子插件。
- 父插件激活时依次挂载子插件；某个子插件激活失败会让父插件激活失败，并回滚此前已经
  挂载的子插件及其他 Effect。
- 子插件拥有自己的 `inject`、Config、状态和 EffectScope，不与父插件共用清理函数。
- 子插件使用父插件传入的 Context，因此继承父级 isolate/intercept 视图；需要独立服务
  作用域时，父插件先 `ctx.isolate(...)`，再从派生 Context 挂载。
- 父插件可以选择和配置子插件，但不应代理子插件的公共 API 或复制其领域逻辑。

声明式 Loader 也支持 entry tree。配置中的 `children` 在父 entry 激活后挂载到父 Context；
父 entry 被禁用、替换或卸载时，其整棵子树一起处理。代码组合插件适合固定共享主干及配置
转发，声明式 children 适合部署组合与 overlay；两者产生相同的 Fiber 所有权语义。

父子关系与以下关系必须区分：

| 关系 | 表达方式 | 含义 |
|---|---|---|
| 生命周期所有权 | `ctx.plugin(child, config)` / Loader `children` | 父卸载时子必定卸载 |
| 服务依赖 | `inject = ("tools",)` | Provider 出现或消失时 Fiber 激活状态重算 |
| 能力角色 | Definition / Provider / Consumer | 架构依赖方向，通常作为同级插件组合 |
| Python 代码依赖 | `import` | 静态模块引用，不产生运行时所有权 |

Provider 与 Consumer 通常应作为组合父插件的同级子节点，通过服务连接，而不是互为父子。
只有确实属于父插件内部生命周期的资源才挂成子插件；不要用嵌套隐藏应由 profile 或应用入口
替换的 Provider。

## 4. 外部插件仓库

第三方插件是独立 Python distribution，推荐使用 `src/` 布局：

```text
dsh-plugin-example/
  pyproject.toml
  README.md
  src/
    dsh_plugin_example/
      __init__.py
      plugin.py
      config.py
      py.typed
  tests/
    test_plugin.py
    test_lifecycle.py
```

distribution 名使用 `dsh-plugin-<name>`，import package 使用
`dsh_plugin_<name>`，Loader 引用为 `dsh_plugin_<name>:plugin`。外部 distribution 不向
`dsh` 包目录写入文件，避免多个 wheel 争用同一普通 package。Loader 只有在应用配置明确
允许该 package 后才解析它；当前不承诺自动 entry-point discovery。

## 5. README 规范

每个产品插件的 README 至少包含：

1. 职责与非职责；它属于 Definition、Provider、Consumer 还是 composition。
2. 导出的 Service/API 与 Context key。
3. `inject` 硬依赖和可选依赖。
4. 配置字段、默认值、验证失败方式。
5. 注册或消费的事件及事件模式（emit/serial/parallel/waterfall）。
6. 生命周期、取消、清理和持久状态所有权。
7. Model Experience：模型看到什么、何时出现、token 与前缀缓存影响；没有直接影响也要说明。
8. Known Limitations and Deferred Work：持久缺口和维护约束，不写普通待办清单。

稳定的模型可见文本、工具描述和错误文本应由 snapshot/transcript 固定。README 说明归属和
条件，不复制其他插件拥有的完整行为。

## 6. 测试标准

一个插件标记为“已验证”前至少具备与其角色相符的证据：

- Config：默认值、边界值、未知/错误类型和跨字段约束。
- Unit：纯数据、状态转换和领域错误。
- Contract：同一 Service Definition 的每个 Provider 运行同一套请求/结果/取消测试。
- Lifecycle：挂载后贡献可见；dispose Fiber 后服务、工具、监听器和任务消失。
- Composition：通过 Loader 和实际组合加载，不只手写 `ctx.plugin()`。
- Product-visible：模型或用户可见行为进入 keyless transcript/snapshot。

只实现 Service Definition 时可以没有 Provider 测试，但不能宣称 seam 已完成。只有 Provider
而没有 Definition，或只有工具 schema 而没有执行 Consumer，均不视为完成的能力插件。

## 7. 新增插件检查清单

1. 在 `docs/porting.md` 记录上游来源、角色和 Python 落点。
2. 判断它是独立插件还是现有插件内部模块；不要为了文件对称拆包。
3. 明确 Service Definition / Provider / Consumer 与依赖方向。
4. 创建最小必要文件，导出唯一 `plugin` 入口。
5. 实现 Config 验证和稳定错误，不在运行路径隐藏默认值。
6. 让所有注册和后台资源归当前 Fiber 所有。
7. 添加生命周期测试及对应角色的单元/契约/组合测试。
8. 编写插件 README；更新架构、迁移台账和相关 Agent Note。
9. 运行相关 `pytest`、`ruff`、`mypy` 与 `git diff --check`。

首个正式 Harness 插件开始实现前，应先为 Cordis 增加类型安全的插件定义辅助 API，避免每个
插件重复对象样板；该辅助 API 只能封装本规范，不能改变 `name/inject/Config/apply` ABI。
