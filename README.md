# StudentAid 批量处理工具（第十一步稳定版）

Windows 桌面 GUI，批量处理 StudentAid 账户资料找回页面：

`https://studentaid.gov/fsa-id/sign-in/retrieve-account-details`

正式入口是 `ait6.py`；推荐直接双击 `启动StudentAid第十一步稳定版.cmd`。

## 第十一步完成内容

- GUI 新增“浏览器后端”下拉框，可选择 `browser-use` 或 `playwright`。
- 默认 2 个处理线程，可选 1-8；每个 worker 都有独立 Chrome 进程、页面和缓存目录，不共享标签页。
- `browser-use` 使用 BrowserProfile 的 Chrome 参数、隔离目录和独立 CDP 启动策略；`playwright` 直接启动独立 Chrome。两种后端都保持 `navigator.webdriver=false`。
- `Limit Reached: Try Again in 24 Hours` 现在是正常明确结果：原样写入累计 CSV 第 6 列，删除对应输入行并继续下一条，不再中断批次。
- `Account Not Found`：结果落盘后清 cookie、cache、storage 和 service worker，回到 `about:blank`；下一条重新打开找回页。
- `Retrieve Your Log-in Information`：记录脱敏电话、脱敏邮箱和恢复方式后，点击真实 `Cancel`，确认空表单再处理下一条。
- 停止或正常结束时，每个 worker 都清除缓存并结束本脚本创建的 Chrome；browser-use 临时配置目录同时删除。
- 输入速度由每字符 60ms 提升到 20ms，仍保留真实键盘事件、失焦、字段完整性和 Continue 启用校验。
- 支持 `September 07, 1980` 这类英文月份 DOB，并在输出中保留 5 列输入的原始日期文本。
- SQLite 使用专用 writer 线程；累计 CSV 追加和 CSV/XLSX 输入删行继续串行加锁、原子替换。

## 一键安装启动

双击：

```text
启动StudentAid第十一步稳定版.cmd
```

启动器按以下规则执行：

1. Python 3.11+ 已存在则跳过，否则通过 `winget` 安装 Python 3.12。
2. Google Chrome 已存在则跳过，否则通过 `winget` 安装。
3. `.venv` 已存在则复用，否则在程序目录创建隔离环境。
4. `tkinter`、`playwright`、`openpyxl`、`browser-use` 都能导入则跳过；缺少时才按 `requirements.txt` 安装。
5. 使用 `.venv\Scripts\python.exe -B ait6.py` 启动，不生成 `__pycache__`。

本版使用系统 Google Chrome，不需要执行 `playwright install chromium`。

仅检查/安装、不打开 GUI：

```cmd
set STUDENTAID_INSTALL_ONLY=1
启动StudentAid第十一步稳定版.cmd
```

## GUI 使用

1. 选择输入 `.csv`、`.scv`、`.txt` 或 `.xlsx`。
2. 选择长期累计输出 CSV；已有内容不会覆盖。
3. 在“浏览器后端”选择 `browser-use` 或 `playwright`。
4. 线程数建议保持默认 `2`，然后点击“开始”。
5. 点击“停止”后，程序停止领取新任务，保留未取得明确结果的输入行，清缓存并结束所有本批次浏览器。

## 输入和累计输出

支持以下常见输入：

- 无表头：`SSN,月,日,年,姓,名,地址`
- 无表头：`SSN,DOB,First Name,Last Name,Address`
- 带常见英文表头的 CSV/TXT/XLSX
- DOB 支持数字日期及英文月份日期，例如 `09/07/1980`、`September 07, 1980`

累计输出无表头，每行固定 9 列，与 `实际输出结果参考.csv` 一致：

```text
输入第一列,DOB,First Name,Last Name,Address,Result Heading,Masked Phone,Masked Email,Recovery Method
```

输出一直叠加并按第一列去重。每次启动先读取输出第一列；如果同一第一列仍出现在输入文件，会直接从输入原子删除。只有取得明确结果或输出中已经存在的输入行才删除；格式错误、网页失败和未取得结果的行保留。

## 页面流程

```text
二线程各自独立浏览器 → 打开找回页 → 填资料 → Continue
  ├─ Account Not Found → 落盘 → 删输入行 → 清全部数据 → about:blank
  ├─ Retrieve Your Log-in Information → 落盘 → 删输入行 → Cancel → 空表单
  ├─ Limit Reached: Try Again in 24 Hours → 正常落盘 → 删输入行 → 继续
  ├─ Loading 超时/会话失效 → 清数据 → 重开 → 最多自动重试 2 次
  └─ 停止 → 不再领任务 → 清缓存 → 结束本批次全部 Chrome
```

## 测试

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -B tests\test_ait6.py -v
```

第十一步自动回归覆盖 13 项，包括：

- GUI 后端值和后端校验
- 两个 worker 真正并发并分别关闭
- Limit 正常累计、继续处理和输入删行
- 英文月份 DOB 导入与原始输出格式
- Account Not Found 数据清理、Retrieve/Cancel 空表单
- Loading 卡住自动重建
- CSV/XLSX 第一列去重删除及累计输出不重复
- 停止请求不会覆盖已经落盘的完成状态
- Playwright 独立 Chrome 的 `navigator.webdriver=false`

现场实测细节见 `CHANGELOG.md`。测试资料、SQLite、累计结果、浏览器缓存和录制文件均由 `.gitignore` 排除。
