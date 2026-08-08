# StudentAid 批量处理工具（第十五步批量输入兼容版）

Windows 桌面 GUI，批量处理 StudentAid 账户资料找回页面：

`https://studentaid.gov/fsa-id/sign-in/retrieve-account-details`

正式源码入口是 `ait10.py`。给普通 Windows 用户使用时，推荐下载 GitHub Release 的独立 ZIP，完整解压后直接双击 `StudentAid-Batch-Tool.exe`；目标电脑不需要安装 Python。缺少 Google Chrome 时可双击 `Start-StudentAid.cmd` 自动安装后启动。

源码运行仍可双击 `启动StudentAid第十五步批量输入兼容版.cmd`。

## 第十五步完成内容

- 修复批量输入中三位年份：只有“前补一位”或“后补一位”恰好有一个候选能形成 1900 年至当前年份的有效日期时才自动恢复；例如 `09/07/980` 和 `12/26/198` 都唯一恢复为 `09/07/1980`、`12/26/1980`。
- First Name、Last Name、Month、Day、Year、SSN 任意必填项为空时，按工作表和源行直接从输入文件删除；不写累计输出、不启动浏览器。该规则覆盖此前对空 Last Name 的姓名拆分兜底。
- 五列输入自动区分 `SSN,DOB,First Name,Last Name,Address` 与 `SSN,First Name,Last Name,DOB,Address`，以实际可解析 DOB 所在列判断，不要求手工换列。
- 网页等待明确结果超时现在视为可恢复的页面停滞：单次允许官网处理 60 秒，之后自动清数据、重建页面并重填，最多重试 2 次；三次仍失败、停止或其他未取得明确结果的资料继续保留在输入文件，下次运行自动重试。
- 字段已填但 Continue 30 秒内未进入可点击状态也按页面停滞自动重建，不再直接落为 Playwright 超时失败。
- Windows/安全扫描器短暂占用输入文件导致原子替换出现 WinError 5 时会限时重试；仍被持续占用才保留资料并明确报错。
- 第十四步的生日输出规则继续保留：累计 CSV 第 2 列始终为单列 `MM/DD/YYYY`，每行固定 9 列。
- 累计 CSV 新写入和既有内容统一采用全字段双引号；LibreOffice 即使启用了 `/` 作为“其他分隔符”，引号内的 `MM/DD/YYYY` 也不会被拆成月、日、年三列。
- `Your Account Is Disabled` 作为正常明确结果：累计 CSV 第 6 列原样写入该状态，联系方式/恢复方式列留空，删除对应输入并继续下一条。

## 第十四步完成内容

- 累计输出第 2 列生日始终写成单列 `MM/DD/YYYY`，月份和日期不足两位时自动补零。
- 五列输入中的英文月份、短日期或其他受支持格式只用于导入解析，不再原样写入输出。
- 七列 `SSN,月,日,年,姓,名,地址` 输入仍可正常读取，但输出生日不会拆成三列；累计 CSV 始终固定 9 列。
- 启动本次修复前已核对当前累计 CSV：17 行生日全部已经是单列 `MM/DD/YYYY`、每行 9 列，因此没有重写或损坏现有结果。

第十三步的联系方式和页面流程继续保留：

- 修复手机号漏记。StudentAid 当前实际使用 `⦁`（U+2981）遮挡号码；例如 `(⦁⦁⦁) ⦁⦁⦁ 8139` 现在会完整写入累计 CSV 第 7 列。
- 脱敏邮箱同样从结果卡片的可见联系方式段落提取，例如 `je⦁⦁⦁⦁⦁⦁⦁@yahoo.com` 写入第 8 列。有手机号/邮箱就原样记录，没有就保持空白。
- 联系方式优先限定到 `p.fsa-color-gray-60`，兜底也只检查可见 `p`，不会把页脚公开邮箱误记为账户邮箱。
- 修复 Retrieve 结果页的 `Cancel` 实际未点击：现在直接点击可见的 `<span>Cancel</span>`，并验证 URL、结果标题、Cancel 或输入表单确实发生变化，不能只凭“已发出点击”日志判断成功。
- `Cancel` 成功后复用当前 worker 的同一个 Chrome、会话、页面和空表单直接填写下一条；不清缓存、不结束浏览器、不新建 Chrome。
- `Account Not Found` 仍严格在结果落盘和输入删行后清 cookie/cache/storage/service worker，进入 `about:blank`；下一条再打开指定网址。
- 累计 CSV 始终追加且按第一列去重。每条明确结果后删除输入行；启动时若输出第一列已存在于输入，也直接删除对应输入行。

第十二步的显示模式和浏览器生命周期继续保留：

- GUI 有两个独立下拉框：浏览器后端选择 `browser-use` / `playwright`，浏览器显示选择 `窗口` / `无头`。
- 默认 `browser-use`、`无头`、2 线程；后端和显示模式可组成四种组合，每个 worker 都使用独立 Chrome、页面和缓存。
- `窗口` 显示 900×720 小窗口，页面 viewport 为 880×650。
- `无头` 不显示浏览器窗口。现场发现 Chromium 原生 headless 会被 StudentAid 以 HTTP/2 协议错误拒绝，因此本版在 Windows 上使用隐藏的普通 Chrome 网络栈，只隐藏本批次精确 PID 的窗口，不影响用户已有 Chrome。
- 修复小窗口下 Continue 没有真正点击：旧坐标点击取得的按钮位置曾为 `y=681`，超出 650 高 viewport；新版使用 `Locator.click()` 自动滚动并点击真实按钮，Enter 和 DOM click 仅作为带状态验证的兜底。
- browser-use 不再被默认 `--start-maximized` 放大到全屏；窗口实测为 900×720。清数据后新建的空白页也会恢复 880×650 viewport。
- 页面导航在收到主文档后返回，再严格等待表单字段可见和 `Loading...` 消失，避免被无关长连接资源拖住。
- browser-use 退出时先结束该 worker 的精确 Chrome PID 树、删除一次性 profile，再停止 CDP 客户端；停止、正常结束和失败结束都不会留下该批次缓存或浏览器进程。

既有结果规则继续保留：

- `Account Not Found`：明确结果落盘并删输入行后，清浏览器数据、回到空白页，下一条重新打开找回页。
- `Retrieve Your Log-in Information`：记录脱敏电话、脱敏邮箱和恢复方式后，点击 `Cancel`，确认空表单再填下一条。
- `Limit Reached: Try Again in 24 Hours`：作为正常明确结果写入累计 CSV 第 6 列，删对应输入行并继续。
- `Your Account Is Disabled`：作为正常明确结果写入累计 CSV 第 6 列，删对应输入行并继续。
- 累计输出一直叠加，按第一列去重；输出第一列已存在的资料会从输入文件直接删除。
- 只有明确结果或输出中已存在的资料才删除；格式错误、网页失败、停止和未取得明确结果的行保留。

## 一键安装启动

双击：

```text
启动StudentAid第十五步批量输入兼容版.cmd
```

启动器执行规则：

1. Python 3.11+ 已存在则跳过，否则通过 `winget` 安装 Python 3.12。
2. Google Chrome 已存在则跳过，否则通过 `winget` 安装。
3. `.venv` 已存在则复用，否则在程序目录创建隔离环境。
4. `tkinter`、`playwright`、`openpyxl`、`browser-use` 都能导入则跳过；缺少时才按 `requirements.txt` 安装。
5. 使用 `.venv\Scripts\python.exe -B ait10.py` 启动，不生成运行字节码缓存。

本版使用系统 Google Chrome，不需要执行 `playwright install chromium`。

仅检查/安装、不打开 GUI：

```cmd
set STUDENTAID_INSTALL_ONLY=1
启动StudentAid第十五步批量输入兼容版.cmd
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
  ├─ Retrieve Your Log-in Information → 落盘 → 删输入行 → 点击可见 span Cancel
  │  → 验证结果页离开 → 同一浏览器/会话/页面的空表单直接填下一条
  ├─ Limit Reached: Try Again in 24 Hours → 正常落盘 → 删输入行 → 继续
  ├─ 点击未触发 → Locator / Enter / DOM click 分级验证
  ├─ Loading 超时或会话失效 → 清数据 → 重开 → 最多自动重试 2 次
  └─ 停止或结束 → 删除缓存/profile → 结束本批次全部 Chrome
```

## 验证结果

第十五步新增三位年份双向唯一恢复、无歧义姓名拆分、当前失败残留重新导入、结果/表单超时自动重试和输入原子替换占用重试回归；第十四步生日输出回归继续覆盖五列英文月份、五列短日期、七列拆分日期和补零格式。所有输出均为固定 9 列，生日严格为 `MM/DD/YYYY`。第十三步的联系方式、Cancel、Account Not Found、累计输出和输入删行逻辑继续保留。

窗口/browser-use 双线程现场 2/2 完成；包含参考手机号 `8139` 的记录，其电话和邮箱与 `实际输出结果参考.csv` 完全一致。窗口/playwright 双线程 2/2 完成，两条结果后四列均与参考逐列一致。另完成真实 Account Not Found 清数据/`about:blank` 验证，以及 2 线程 4 条复用矩阵：两个 Chrome 各只启动一次，Retrieve 后实际点击 Cancel 并复用空表单继续处理，最终 4/4 完成、失败 0、输入剩余 0。

开发测试脚本、测试资料、SQLite、累计结果、浏览器缓存、临时 profile 和录制文件均不进入发布包。
