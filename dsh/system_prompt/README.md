# `dsh.system_prompt`

M2 的 System Prompt Consumer/registry，通过 `systemPrompt` 服务注册具名有序 section，并在
每次模型请求前运行 `system-prompt/assemble` waterfall。注册由调用方 Fiber 的 Effect 所有，
卸载贡献插件后 section 消失。

配置只包含可选字符串 `persona`。当前 Model Experience 是将非空 section 按 `(order, name)`
排序并以空行连接后放入 `GenerateRequest.system`。M2 暂不支持动态 context、变量、工具 schema、
complete section 与 scope shadowing；这些不会以临时兼容接口提前暴露。
