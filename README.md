# StudentAid 批量处理工具（第十二步无头稳定版）

Windows 桌面 GUI，批量处理 StudentAid 账户资料找回页面：

`https://studentaid.gov/fsa-id/sign-in/retrieve-account-details`

正式入口是 `ait7.py`；推荐双击 `启动StudentAid第十二步无头稳定版.cmd`。

## 第十二步完成内容

- GUI 有两个独立下拉框：浏览器后端选择 `browser-use` / `playwright`，浏览器显示选择 `窗口` / `无头`。
- 默认 `browser-use`、`无头`、2 线程；后端和显示模式可组成四种组合，每个 worker 都使用独立 Chrome、页面和缓存。
- `窗口` 显示 900×720 小窗口，页面 viewport 为 880×650。
- `无头` 不显示浏览器窗口。现场发现 Chromium 原生 headless 会被 StudentAid 以 HTTP/2 协议错误拒绝，因此本版在 Windows 上使用隐藏的普通 Chrome 网络栈，只隐藏本批次精确 PID 的窗口，不影响用户已有 Chrome。
- 修复小窗口下 Continue 没有真正点击：旧坐标点击取得的按钮位置曾为 `y=681`，超出 650 高 viewport；新版使用 `Locator.click()` 自动滚动并点击真实按钮，Enter 和 DOM click 仅作为带状态验证的兜底。
- browser-use 不再被默认 `--start-maximized` 放大到全屏；窗口实测为 900×720。清数据后新建的空白页也会恢复 880×650 viewport。
- 页面导航在收到主文档后返回，再严格等待表单字段可见和 `Loading...` 消失，避免被无关长连接资源拖住。
- browser-use 退出时先结束该 worker 的精确 Chrome PID 树、删除一次性 profile，再停止 CDP 客户端；停止、正常结束和失败结束都不会留下该批次缓存或浏览器进程。

第十一步的数据规则继续保留：

- `Account Not Found`：明确结果落盘并删输入行后，清浏览器数据、回到空白页，下一条重新打开找回页。
- `Retrieve Your Log-in Information`：记录脱敏电话、脱敏邮箱和恢复方式后，点击 `Cancel`，确认空表单再填下一条。
- `Limit Reached: Try Again in 24 Hours`：作为正常明确结果写入累计 CSV 第 6 列，删对应输入行并继续。
- 累计输出一直叠加，按第一列去重；输出第一列已存在的资料会从输入文件直接删除。
- 只有明确结果或输出中已存在的资料才删除；格式错误、网页失败、停止和未取得明确结果的行保留。

## 一键安装启动

双击：

```text
启动StudentAid第十二步无头稳定版.cmd
```

启动器执行规则：

1. Python 3.11+ 已存在则跳过，否则通过 `winget` 安装 Python 3.12。
2. Google Chrome 已存在则跳过，否则通过 `winget` 安装。
3. `.venv` 已存在则复用，否则在程序目录创建隔离环境。
4. `tkinter`、`playwright`、`openpyxl`、`browser-use` 都能导入则跳过；缺少时才按 `requirements.txt` 安装。
5. 使用 `.venv\Scripts\python.exe -B ait7.py` 启动，不生成运行字节码缓存。

本版使用系统 Google Chrome，不需要执行 `playwright install chromium`。

仅检查/安装、不打开 GUI：

```cmd
set STUDENTAID_INSTALL_ONLY=1
启动StudentAid第十二步无头稳定版.cmd
```

## GUI 使用

1. 选择输入 `.csv`、`.scv`、`.txt` 或 `.xlsx`。
2. 选择长期累计输出 CSV；已有内容不会覆盖。
3. 选择浏览器后端 `browser-use` 或 `playwright`。
4. 选择 `窗口` 或 `无头`；默认无头，不显示浏览器。
5. 线程数建议保持默认 2，然后点击“开始”。
6. 点击“停止”后停止领取新任务，保留未取得明确结果的输入行，清缓存并结束本批次全部 Chrome。

## 输入和累计输出

支持以下输入：

- 无表头：`SSN,月,日,年,姓,名,地址`
- 无表头：`SSN,DOB,First Name,Last Name,Address`
- 带常见英文表头的 CSV/TXT/XLSX
- DOB 支持数字日期及英文月份日期，例如 `09/07/1980`、`September 07, 1980`

累计输出无表头，每行固定 9 列，与 `实际输出结果参考.csv` 一致：

```text
输入第一列,DOB,First Name,Last Name,Address,Result Heading,Masked Phone,Masked Email,Recovery Method
```

每条明确结果按“SQLite → 累计 CSV → 输入删行”的顺序实时提交。CSV/TXT 和 XLSX 输入删行都使用锁与原子替换；程序中断后可依靠累计输出第一列去重继续。

## 页面流程

```text
2 个 worker，各自独立浏览器和缓存 → 打开找回页 → 填资料 → 真实点击 Continue
  ├─ Account Not Found → 落盘 → 删输入行 → 清全部数据 → about:blank
  ├─ Retrieve Your Log-in Information → 落盘 → 删输入行 → Cancel → 空表单
  ├─ Limit Reached: Try Again in 24 Hours → 正常落盘 → 删输入行 → 继续
  ├─ 点击未触发 → Locator / Enter / DOM click 分级验证
  ├─ Loading 超时或会话失效 → 清数据 → 重开 → 最多自动重试 2 次
  └─ 停止或结束 → 删除缓存/profile → 结束本批次全部 Chrome
```

## 验证结果

第十二步开发副本自动回归共 18 项并全部通过，覆盖 GUI 两个下拉框、四组合配置、两个后端的窗口/无头真实 Chrome、隐藏窗口 UA、`navigator.webdriver=false`、Continue 真点击、双线程、结果累计、输入删行、Cancel、缓存清理和停止一致性。正式发布目录按运行版精简，不附带开发测试脚本。

使用 `假资料测试4.xlsx` 隔离副本的最终四组合现场矩阵共处理 8 条：每组 2/2 完成、失败 0、输入剩余 0、输出均为两行且每行 9 列、退出后残留 Chrome 0。详细过程见 `CHANGELOG.md`。

开发测试脚本、测试资料、SQLite、累计结果、浏览器缓存、临时 profile 和录制文件均不进入发布包。
