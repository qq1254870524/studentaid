# StudentAid 批量处理工具（第十步稳定版）

Windows 桌面 GUI，按顺序处理 StudentAid 账户资料找回页面：

`https://studentaid.gov/fsa-id/sign-in/retrieve-account-details`

正式入口是 `ait5.py`；推荐直接双击 `启动StudentAid第十步稳定版.cmd`。

## 第十步完成内容

- 修复 Playwright 点击 `Continue` 后长期停在 Loading：旧启动方式令 `navigator.webdriver=true`；新版使用与 browser-use 一致的 `AutomationControlled` Chrome 参数，实测为 `false`。
- 固定单线程顺序处理，避免多个页面共享 cookie、session 和站点次数状态。
- `Continue` 和 `Cancel` 都按可见按钮坐标点击，并等待明确页面状态。
- `Account Not Found`：先保存结果，再清除当前专用 BrowserContext 的 cookie、cache、storage 和 service worker，关闭当前页、回到 `about:blank`；下一条重新打开找回页面。
- `Retrieve Your Log-in Information`：先记录页面给出的脱敏联系方式和找回方式，再点击实际 `Cancel` 按钮，确认表单为空后填下一条。
- `Limit Reached: Try Again in 24 Hours`：立即结束当前批次，不再继续提交；当前及后续输入行全部保留。
- 每条明确结果按“SQLite → 累计 CSV → 删除输入行”的顺序实时落盘。
- 累计 CSV 永不覆盖已有数据；第一列已存在时跳过重复追加。
- 每次启动先读取累计输出第一列；同一第一列若仍出现在输入文件，会先从输入文件原子删除。
- 支持 `.csv`、`.scv`、`.txt`、`.xlsx`；XLSX 删除行时保留工作簿、工作表和其他行。

## 一键安装启动

双击：

```text
启动StudentAid第十步稳定版.cmd
```

启动器按以下规则执行：

1. Python 3.10+ 已存在则跳过，否则通过 `winget` 安装 Python 3.12。
2. Google Chrome 已存在则跳过，否则通过 `winget` 安装。
3. `tkinter`、`playwright`、`openpyxl` 都能导入则跳过，否则按 `requirements.txt` 安装缺少依赖。
4. 使用 `python -B ait5.py` 启动，不生成 `__pycache__`。

本版使用系统 Google Chrome，不需要执行 `playwright install chromium`。

## 输入和累计输出

支持以下常见输入：

- 无表头：`SSN,月,日,年,姓,名,地址`
- 无表头：`SSN,DOB,First Name,Last Name,Address`
- 带常见英文表头的 CSV/TXT/XLSX

累计输出每行固定 9 列，与现有参考结果一致：

```text
输入第一列,DOB,First Name,Last Name,Address,Result Heading,Masked Phone,Masked Email,Recovery Method
```

输出保持连续叠加且按第一列去重。程序只会删除已经取得明确结果，或第一列已经存在于累计输出的输入行。格式错误、网页失败、站点限制和未取得明确结果的行都不会删除。

## 页面流程

```text
打开找回页 → 填资料 → Continue
  ├─ Account Not Found → 落盘 → 删输入行 → 清全部浏览器数据 → about:blank
  ├─ Retrieve Your Log-in Information → 落盘 → 删输入行 → Cancel → 空表单
  ├─ Loading 超时/会话失效 → 清数据 → 重开 → 最多自动重试 2 次
  └─ Limit Reached → 停止批次 → 保留当前和后续输入行
```

## 可选显式 CDP

默认无需启动 browser-use 或手工配置 CDP。若明确要复用已经打开的 Chrome，可设置：

```powershell
$env:STUDENTAID_CDP_URL='http://127.0.0.1:9223'
python -B ait5.py
```

程序会拒绝 `navigator.webdriver=true` 的 CDP 浏览器，避免再次进入 Continue 长期 Loading。

## 测试

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -B tests\test_ait5.py -v
```

第十步自动回归覆盖：

- Chrome 启动后的 `navigator.webdriver=false`
- Account Not Found 清 cookie/cache/storage 后回到 `about:blank`
- Retrieve 结果保存后的真实 `Cancel` 结构与空表单
- Loading 卡住后的会话重建
- 九次/24 小时站点限制即时识别和输入保留
- CSV/XLSX 第一列去重删除
- 累计结果追加、不覆盖、不重复
- 停止请求不会覆盖已经落盘的完成状态

现场对照结果见 `CHANGELOG.md`。测试数据、SQLite、累计结果和录制文件均由 `.gitignore` 排除。
