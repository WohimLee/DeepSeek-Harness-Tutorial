# Implemented Agent Notes

本目录保存已经交付的决策。遵循根 `AGENTS.md` 和 `../README.md`，Note 必须位于正确的
类别子目录并使用 `Status: implemented`。

实现中的路径、符号、默认值或机制改变时，同步更新拥有该决定的 Note 中的事实，不追加
变更日志。不得把 Note 原地改写成相反决定；决策反转时创建新的 proposed Note 并相互
链接。

当已交付决定完整结束，且其备选方案、所有权、不变量或重新引入条件不再可能指导后续工作
时，可按规则移入 `../archived/<class>/`。不能只根据文件年龄或字数归档。当前架构事实仍
以代码、测试、根 `AGENTS.md` 和 `docs/` 为最高依据。
