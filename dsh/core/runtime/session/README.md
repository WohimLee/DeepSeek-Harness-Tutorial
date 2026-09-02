# `dsh.core.runtime.session`

M1 的内存 Session Service Definition/Provider。`ctx.sessions` 创建 Session；Session 只追加
带连续 `seq` 的事件，并从 `user/message`、`assistant/message` 与 `tool/result` 投影下一次
模型请求历史。

## Service

- Context key：`sessions`
- `create(session_id?)`：创建空 Session。
- `get_session(id)`、`list_sessions()`：读取当前进程中的 Session。
- `Session.append(type, data)`：验证核心 payload 并追加。
- `Session.derive_messages()`：只从日志投影模型历史，忽略 raw chunk 与生命周期 bracket。

## Model Experience

Session 不添加文本；它决定哪些已记录消息进入后续请求。追加新模型可见输入必须增加事件并
更新投影，Agent Loop 不得维护旁路历史。

## Known Limitations and Deferred Work

- M1 仅支持新建内存 Session；seed/replay、fork、surface replacement、JSON 持久化验证与
  request header 在后续阶段实现。
- `turn/end` 暂用最小 reason 词汇；结构化取消和 Provider failure 随 Agent Loop 引入。
