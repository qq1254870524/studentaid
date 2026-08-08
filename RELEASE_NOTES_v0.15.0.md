# StudentAid Step20 Windows 独立正式版

版本：`v0.15.0-step20-windows-standalone`
标签：`stable-2026-08-09-step20-windows-standalone`
日期：2026-08-09
平台：Windows 10/11 x64

## 本版更新

- 正式源码升级为 `ait15.py`，`ait14.py` 保持不改。
- 点击 Continue 后出现 `Account Recovery In Progress` 时，立即作为正常明确结果输出。
- 累计 CSV 的结果状态完整写入 `Account Recovery In Progress`，联系方式和恢复方式留空。
- 结果落盘并删除对应输入行后，清浏览器数据、进入 `about:blank`，当前 worker 继续处理下一条。
- 其他页面结果、动态列、DOB、并发队列、SQLite、累计去重、Retrieve/Cancel 和浏览器生命周期逻辑保持不变。

## 验证

- `ait14.py` 基线测试：16/16 通过。
- `ait15.py` 修改后回归：18/18 通过。
- 新增状态识别、完整状态输出和终态清理测试：2/2 通过。
- Windows x64 单文件 EXE 自检通过。

## 下载与使用

推荐下载 `StudentAid-Step20-Windows-x64-Standalone-20260809.zip`，完整解压后运行 `StudentAid-Batch-Tool.exe`。
目标电脑不需要安装 Python；需要 Google Chrome。未安装 Chrome 时可运行包内 `Start-StudentAid.cmd`。

## 发布资产

- `StudentAid-Step20-Windows-x64-Standalone-20260809.zip`
- `StudentAid-Batch-Tool.exe`
- `RELEASE_ASSETS_SHA256.txt`

发布包不包含测试资料、真实输入输出、SQLite、日志、缓存、浏览器 profile、虚拟环境或构建临时文件。
