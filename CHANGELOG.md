# 更新日志

## v0.6-step11 — 2026-08-08

### GUI 与双后端

- 正式源码升级为 `ait6.py`，旧版 `ait5.py` 保持不改。
- GUI 新增 `browser-use` / `playwright` 下拉选项，默认 `browser-use`；线程默认值改为 2，可选 1-8。
- 两种后端都按 worker 创建独立 Chrome、页面和缓存，恢复任务队列与专用 SQLite writer；累计 CSV 和输入删行继续加锁并原子写回。
- browser-use 初版使用两个完整 BrowserSession 时，现场发现关闭阶段的标签页看门狗会和 Playwright 断开竞争；正式版改为直接采用 BrowserProfile 的 Chrome 参数与隔离 CDP 启动策略，复测不再出现事件循环/看门狗错误。
- browser-use 二线程实测得到两个不同 Chrome PID，两个 `navigator.webdriver=false`；关闭后两个 PID 和两个临时 profile 均不存在。

### 结果与数据修复

- `Limit Reached: Try Again in 24 Hours` 从“停止批次并保留输入”改为正常明确结果：原文写入累计 CSV 第 6 列，删除当前输入并继续后续资料。
- 继续保留 `Account Not Found` 落盘后清全部浏览器数据并回到 `about:blank`，以及 `Retrieve Your Log-in Information` 落盘后点击 `Cancel` 并确认空表单。
- 根据 `假资料测试3.xlsx` 和 `实际输出结果参考.csv` 补齐 `September 07, 1980` 等英文月份 DOB。现场首轮因此保留的唯一格式错误行，在修复后成功继续处理；没有误删失败输入。
- 5 列无表头资料的 DOB 在累计输出中保留原始显示文本；输出仍为无表头固定 9 列。
- 每字符输入延迟从 60ms 降至 20ms，字段稳定等待从 500ms 降至 200ms；真实键盘事件、失焦和 Continue 启用检查不变。

### 停止与清理

- `close()` 在停止和正常结束时都会清 cookie、cache、storage、service worker，回到空白页后结束脚本拥有的 Chrome。
- browser-use 同时删除每个 worker 的临时 user-data-dir；进程正常结束失败时按精确 PID 树兜底清理，不影响用户已有 Chrome。
- 两种后端各用 2 个真实 worker 运行中点击停止：均产生 2 条缓存/进程清理完成记录，最终状态 `stopped`，残留本脚本 Chrome PID 为 0。

### 现场验证

- `假资料测试3.xlsx` browser-use 二线程最终 6/6 完成、失败 0、输入剩余 0、累计输出 6 行且全部 9 列。
- 同一资料 Playwright 二线程 6/6 完成、失败 0、输入剩余 0、累计输出 6 行且全部 9 列。
- 两种后端现场都覆盖三种页面结果：`Account Not Found: Create a New Account`、`Retrieve Your Log-in Information`、`Limit Reached: Try Again in 24 Hours`。
- 两种后端各自把原始 6 行重新放回输入并复跑：启动阶段全部按累计输出第一列删除，浏览器处理数 0，累计输出仍为 6 行。
- 自动回归由 9 项增至 13 项并全部通过；browser-use 技能录制保存在本机 `studentaid-step11-live` 目录。

### 安装与发布

- 新增统一入口 `启动StudentAid第十一步稳定版.cmd`：检查 Python 3.11+、Chrome、隔离 `.venv` 和全部依赖；存在即跳过，缺少才创建/安装。
- `requirements.txt` 新增固定版 `browser-use==0.13.7`；仍使用系统 Chrome，不下载 Playwright Chromium。
- 全新目录执行安装模式成功创建 `.venv` 并安装依赖；立即二次执行显示环境与全部依赖均 `SKIP`。在该隔离环境内再次启动 browser-use 双线程，两个 PID/缓存目录均独立且关闭后无残留。
- GUI 实例检查确认下拉值严格为 `browser-use`、`playwright`，默认后端 `browser-use`、默认线程 `2`、可选范围 `1-8`。

## v0.5-step10 — 2026-08-08

### 修复

- 定位并修复 Playwright `Continue` 长期转圈：默认 Playwright Chrome 的 `navigator.webdriver=true`，而 browser-use 接管的 Chrome 为 `false`。新版 Chrome 启动加入 `--disable-blink-features=AutomationControlled`，保留独立 BrowserContext。
- 修复半成品遗漏的 `PageSubmissionStalled` 异常定义。
- 修复半成品 `Locator.filter(visible=True)` 非法用法；`Cancel` 现在先按固定 ID、再按可访问角色定位，并使用真实坐标点击。
- 修复用户在明确结果落盘后点击停止时，已完成记录可能被错误覆盖为 `stopped` 的状态问题。
- 新增 `Limit Reached: Try Again in 24 Hours` 明确识别；旧版会继续等待到超时，新版立即停止并保留所有未处理输入。

### 数据行为

- 输出改为用户选择的长期累计 CSV，结果实时追加且不覆盖。
- 输出第一列已存在时不重复追加，并在启动时从输入文件删除相同第一列。
- 明确结果严格按 SQLite、累计 CSV、输入删行的顺序提交；中断后可通过累计输出恢复一致性。
- CSV/TXT 使用同目录临时文件和 `os.replace` 原子改写；XLSX 删除匹配行后原子替换原工作簿。
- Account Not Found 落盘后清除专用上下文 cookie、cache、站点 storage、service worker，并回到 `about:blank`。
- Retrieve 结果落盘后点击 `Cancel`，等待所有输入字段清空再处理下一条。

### 启动与发布

- 新增唯一入口 `启动StudentAid第十步稳定版.cmd`：Python/Chrome/依赖存在就跳过，缺少才安装。
- 固定单线程顺序处理；GUI 不再提供无效的并发建议。
- 新增 9 项 Step 10 自动回归。

### 现场验证

- browser-use 同一测试资料：点击 Continue 后约 2 秒返回 `Account Not Found`。
- 旧 Playwright 独立 Chrome：`navigator.webdriver=true`，Continue 后等待 60 秒仍无明确结果。
- Playwright 连接 browser-use Chrome：约 1 秒识别相同 `Account Not Found`。
- 新版独立 Chrome 启动探针：`navigator.webdriver=false`。
- Account Not Found 后已实测清除浏览器数据、进入 `about:blank`、重新打开目标 URL。
- 后续实测命中官方九次限制；browser-use 和 Playwright 均显示 `Limit Reached: Try Again in 24 Hours`，证明它是站点限制而不是 Playwright 转圈。新版已即时识别，未继续消耗输入。
- 由于官方已进入 24 小时限制，本轮没有继续提交新的 Retrieve 资料；Retrieve/Cancel 使用页面真实按钮结构和本地 Playwright DOM 回归验证。
