# StudentAid 第二十步 Windows 正式版

版本：`v0.15.0-step20-windows-standalone`
日期：2026-08-09
平台：Windows 10/11 x64

## 直接使用

1. 完整解压 ZIP。
2. 电脑已安装 Google Chrome 时，直接双击 `StudentAid-Batch-Tool.exe`。
3. 没安装 Chrome 时，双击 `Start-StudentAid.cmd`，启动器会在缺少时通过 winget 安装 Chrome。
4. 在 GUI 中选择输入文件、累计输出 CSV、浏览器后端、窗口/无头和线程数，然后开始。

目标电脑不需要安装 Python，也不需要手工安装 Playwright、browser-use 或 openpyxl。

## 本版内容

- browser-use / playwright 双后端。
- 窗口 / 无头双显示模式。
- 任意正整数线程数（默认 2）。
- 官网瞬时故障一轮仍无明确结果时把任务放到队尾，最多三轮队列尝试，不阻塞其他资料。
- 动态队列完全清空后才结束工作线程，队尾重试任务不会遗漏。
- 同一批输入按第一列去重，只为每个唯一值创建一个浏览器任务；同组结果整体落库并一次删除输入匹配行。
- 紧凑输入固定前四个逻辑字段，第 5 列起允许任意列数并逐列透传；累计 CSV 在全部输入列后追加四个结果列。
- 四列输入输出 8 列、五列输入输出 9 列、七列输入输出 11 列；DOB 继续保持单列 `MM/DD/YYYY`。
- Continue 真实点击和停滞自动重试。
- Retrieve 结果提取后真实点击 Cancel，并复用当前浏览器和空表单。
- Account Not Found 落盘后清全部站点数据、进入 `about:blank`，复用当前浏览器处理下一条。
- `Limit Reached: Try Again in 24 Hours` 与 `Your Account Is Disabled` 作为正常明确结果输出。
- `Account Lookup Issue: Get Help` 作为正常明确结果输出。
- `We are unable to retrieve your log-in information. Access your account by recovering your account with a photo ID.` 作为正常明确结果输出。
- `Enter a valid Social Security number.` 作为正常明确结果输出。
- `Account Recovery In Progress` 作为正常明确结果输出，落盘后沿用终态清理流程。
- 手机号和脱敏邮箱有值就记录，没有就留空。
- 累计 CSV 全部字段加双引号，生日保持单列 `MM/DD/YYYY`，附加输入列不合并。
- 六个必填字段任一缺失时直接删除该输入行；输出第一列已存在的输入也直接删除。

## 发布包边界

发布包不包含测试资料、真实输入输出、SQLite、日志、缓存、浏览器 profile、`.venv` 或构建文件。EXE 未做商业代码签名，部分电脑首次运行可能显示 Windows SmartScreen 提示。
