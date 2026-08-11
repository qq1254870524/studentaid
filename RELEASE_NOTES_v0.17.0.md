# StudentAid v0.17.0 Step22 Windows 正式版

版本：`v0.17.0-step22-account-not-found-create-new-account`  
标签：`stable-2026-08-12-step22-account-not-found-create-new-account`  
日期：2026-08-12  
平台：Windows 10/11 x64

## 本版更新

- 正式源码升级为 `ait17.py`，`ait16.py` 保持不改。
- 点击 Continue 后出现 `Account Not Found: Create a New Account` 时，立即将完整状态写入累计输出结果列。
- 结果仍按原流程落盘、删除输入行、清理浏览器数据、返回 `about:blank`，再复用当前浏览器处理下一条。
- GUI 上次配置保存/恢复，以及其他页面状态、动态输入列、DOB、线程、SQLite、Retrieve/Cancel 和浏览器生命周期逻辑未改。

## 验证

- 基线 `ait16.py`：20/20 通过。
- 修改后 `ait17.py`：21/21 通过。
- PyInstaller Windows x64 窗口模式 EXE 自检通过。
- 发布包不包含测试资料、累计输出、SQLite、配置、缓存、虚拟环境或构建临时文件。

## 使用

推荐下载 `StudentAid-Step22-Windows-x64-Standalone-20260812.zip`，解压后双击 `StudentAid-Batch-Tool.exe`。源码用户可运行 `启动StudentAid.cmd`，依赖存在时自动跳过安装。
