# 更新日志

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
