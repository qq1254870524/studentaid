# StudentAid Step19 Windows 独立正式版

版本：`v0.14.0-step19-windows-standalone`
标签：`stable-2026-08-08-step19-windows-standalone`
日期：2026-08-08
平台：Windows 10/11 x64

## 下载与使用

推荐下载 `StudentAid-Step19-Windows-x64-Standalone-20260808.zip`：

1. 完整解压 ZIP，不能直接在压缩包内运行。
2. 已安装 Google Chrome：双击 `StudentAid-Batch-Tool.exe`。
3. 未安装 Google Chrome：双击 `Start-StudentAid.cmd`，启动器会在缺少时通过 winget 安装 Chrome 后启动。
4. 在 GUI 中选择输入文件、累计输出 CSV、`browser-use` / `playwright`、窗口 / 无头和线程数。

目标电脑不需要安装 Python、Playwright、openpyxl 或 browser-use。

## 本版更新

- 正式源码升级为 `ait14.py`，PyInstaller 和源码启动器全部切换到该入口。
- 紧凑无表头输入固定前四个逻辑列 `SSN,DOB,First Name,Last Name`；第 5 列起允许任意数量的附加列，并逐列原样透传。
- 累计 CSV 改为“全部输入列 + 4 个页面结果列”；四列输入输出 8 列、五列输入输出 9 列、七列输入输出 11 列。
- DOB 继续统一为单列 `MM/DD/YYYY`，旧七列拆分月/日/年和带表头任意顺序输入保持兼容。
- 页面出现 `Enter a valid Social Security number.` 时立即作为正常明确结果落盘、删除对应输入行、清理页面并复用当前 worker。
- 保留 Step18 的 `Account Lookup Issue: Get Help`、Photo ID recovery 文案和任意正整数线程数。
- 保留 Step17 的队尾重试：官网瞬时失败不阻塞其余资料，每个唯一任务最多三轮队列尝试。
- 保留同第一列批内去重、SQLite → 累计 CSV → 输入删行提交顺序、Retrieve 后 Cancel、终态清理和浏览器复用。

## 发布资产

- `StudentAid-Step19-Windows-x64-Standalone-20260808.zip`：推荐完整独立包。
- `StudentAid-Batch-Tool.exe`：Windows x64 单文件 EXE。
- `SHA256SUMS.txt`：发布资产 SHA256 校验值。
- `EXE独立版更新说明.md`：独立版更新说明。
- `CHANGELOG.md`：完整历史更新日志。

## 发布包边界

发布包不包含测试资料、真实输入输出、SQLite、日志、缓存、浏览器 profile、`.venv`、`build-venv` 或 PyInstaller 构建临时文件。
