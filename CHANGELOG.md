# 更新日志

## v0.17.0-step22-account-not-found-create-new-account — 2026-08-12

### Account Not Found 完整状态

- 正式源码新增 `ait17.py`，`ait16.py` 保持不改。
- 点击 Continue 后精确出现 `Account Not Found: Create a New Account` 时，立即识别为正常明确结果，并将完整文案写入结果列。
- 仍沿用原有 Account Not Found 的结果落盘、输入删除、累计追加、浏览器数据清理、`about:blank` 和下一条资料处理流程。
- 仅调整该状态的常量、识别和结果收集；GUI 配置持久化、Continue/Cancel、浏览器复用、动态列、DOB、并发、SQLite 和其他明确结果保持不变。

### 验证与发布

- `ait16.py` 基线：20/20 测试通过。
- `ait17.py` 修改后：21/21 测试通过，新增完整状态识别/输出测试。
- PyInstaller Windows x64 独立 EXE、源码 ZIP 和 SHA256 校验文件随 GitHub Release 发布。


## v0.16.0-step21-gui-config-persistence — 2026-08-12

### GUI 配置持久化

- 正式源码升级为 `ait16.py`，`ait15.py` 保持不改。
- 保存输入文件、累计输出、浏览器后端、窗口/无头和线程数到运行目录 `studentaid_gui_config.json`。
- 启动时恢复上次配置；配置文件缺失、损坏、后端/显示模式非法或线程数小于 1 时回退默认值。
- 输入框、下拉框和线程数修改采用 300ms 防抖保存，点击“开始”和关闭窗口时强制保存，避免只改配置后退出导致丢失。
- 配置采用临时文件原子替换；`studentaid_gui_config.json` 已加入 `.gitignore`，不进入源码提交和发布包。
- 仅新增 GUI 配置读写；Continue、Cancel、浏览器生命周期、SQLite、输入删除、累计输出和既有明确结果逻辑未修改。

### 验证与启动

- `ait16.py` 基于 `ait15.py` 回归测试通过，并新增配置保存/恢复和损坏配置回退测试。
- PyInstaller 入口、源码启动器和 Windows 文件版本升级为 `ait16.py` / `0.16.0.0`。

## v0.15.1-startup-pythonw — 2026-08-11

### 源码启动不再保留黑色控制台

- `启动StudentAid.cmd` 继续保留 Python、Chrome、虚拟环境和依赖检查。
- 正常启动阶段改为 `start "" .venv\Scripts\pythonw.exe -B ait15.py`，与 `E:\txfgsales\启动_TXFGSales.cmd` 的无控制台启动方式一致。
- `python.exe` 只用于启动前检查和缺少依赖时的安装；GUI 本身由 `pythonw.exe` 启动，启动完成后不保留黑色控制台窗口。
- `ait15.py`、浏览器流程、输入输出、SQLite 和既有功能均未修改。

## v0.15.0-step20-account-recovery-in-progress — 2026-08-09

### 新增页面明确结果

- 正式源码升级为 `ait15.py`，`ait14.py` 保持不改。
- 点击 Continue 后出现 `Account Recovery In Progress` 时，立即识别为正常明确结果。
- 累计 CSV 的结果状态完整写入 `Account Recovery In Progress`，联系方式和恢复方式保持空白。
- 状态落入 SQLite 和累计 CSV、删除对应输入行后，沿用既有终态清理流程：清浏览器数据、进入 `about:blank`，复用当前 worker 处理下一条。

### 变更边界与验证

- 仅新增常量、页面判定、结果收集、终态清理成员和针对性测试；Step19 动态列、SSN 校验、Retrieve/Cancel、其他明确结果、并发队列、SQLite、输入删行和累计输出逻辑均未调整。
- `ait14.py` 基线 16 项通过；`ait15.py` 全量回归 18 项通过，新增状态识别/完整输出和终态清理 2 项通过。
- PyInstaller 和源码启动器入口升级为 `ait15.py`，Windows 文件版本升级为 `0.15.0.0`。

## v0.14.0-step19-windows-standalone — 2026-08-08

### 动态输入/输出列

- 正式源码升级为 `ait14.py`，`ait13.py` 保持不改。
- 根据 `假资料测试2.xlsx` 实际 14,482 行七列结构，紧凑无表头输入现在只固定前四个逻辑字段 `SSN,DOB,First Name,Last Name`；第 5 列及后续字段逐列透传，不限制总列数。
- 累计 CSV 改为“全部输入列 + 四个页面结果列”；四列输入输出 8 列、五列输入仍输出 9 列、七列输入输出 11 列，不再把地址、邮箱、电话拼进单个 Address 单元格。
- DOB 仍统一为单列 `MM/DD/YYYY`；旧七列拆分月/日/年输入和带表头任意顺序输入保留原输出分支，避免影响已正常功能。

### 新增页面明确结果

- 点击 Continue 后出现 `Enter a valid Social Security number.` 时，立即作为正常明确结果写入结果列，不再经历三次页面重建和三轮队尾重试。
- 结果写入 SQLite 和累计 CSV 后删除对应输入行，随后沿用终态清理、`about:blank` 和当前 worker 浏览器复用流程。
- 新增页面文案判定、完整结果、终态清理、四列无占位、七列透传、旧拆分日期和既有带表头分支回归；Step19 合计 16 项通过。

### 发布配置

- 统一启动器和 PyInstaller 入口升级为 `ait14.py`，Windows 文件版本升级为 `0.14.0.0`。
- Windows x64 正式版使用 PyInstaller 单文件窗口模式构建，发布包同时提供独立 EXE、推荐 ZIP、启动器、使用说明、完整更新日志和 SHA256 校验文件。
- GitHub Release 标签统一为 `stable-2026-08-08-step19-windows-standalone`，版本名统一为 `v0.14.0-step19-windows-standalone`。
- 发布包明确排除测试资料、真实输入输出、SQLite、日志、缓存、浏览器 profile、虚拟环境和构建临时目录。

## v0.13-step18-new-status-unlimited-threads — 2026-08-08

### 新增明确状态

- 正式源码升级为 `ait13.py`，`ait12.py` 保持不改。
- 点击 Continue 后出现 `Account Lookup Issue: Get Help` 时，立即作为正常明确结果写入累计 CSV 第 6 列，后续字段留空。
- 点击 Continue 后出现 `We are unable to retrieve your log-in information. Access your account by recovering your account with a photo ID.` 时，立即把完整文案作为正常明确结果写入第 6 列，不再误入 Retrieve 联系方式提取或等待超时。
- 两种新终态完成落盘和输入删行后，沿用已验证的终态清理路径：清浏览器数据、进入 `about:blank`，复用当前 worker 浏览器处理下一条。

### 任意线程与回归

- GUI 的线程控件从 1-8 Spinbox 改为可直接输入任意正整数的 Entry，批处理参数验证同步取消 8 线程硬上限；0 和负数仍明确拒绝。
- 原默认 2 线程不变；现场续跑仍按既有 `playwright + 窗口 + 8线程` 配置，不擅自提高并发。
- 新增两个终态识别、完整输出、清理分支、12 线程接受和 0 线程拒绝测试；Step18 共 11 项测试通过，Step15 回归 11 项通过、1 项依赖现场失败数据的测试跳过。
- Continue、Retrieve/Cancel、Account Not Found、Limit Reached、Account Disabled、生日格式、累计去重、输入删行、队尾重试等已正常功能未改。

### 发布配置

- 统一启动器与 PyInstaller 入口升级为 `ait13.py`，Windows 文件版本升级为 `0.13.0.0`。

## v0.12-step17-queue-retry — 2026-08-08

### 瞬时失败回到队尾

- 正式源码升级为 `ait12.py`，`ait11.py` 保持不改。
- 现场 `playwright + 窗口 + 8线程` 运行中发现 1 条唯一任务连续三次页面会话重建、约 208 秒后仍未取得官网明确结果；旧版正确释放了线程并保留输入，但只能等整批结束后人工重跑。
- 新版在一轮网页处理失败后把同第一列整组恢复为 pending，并把代表任务加入动态队列尾部；其他正常资料不受阻塞，失败项等待官网恢复后再试。
- 每个唯一任务最多三轮队列尝试，每轮继续包含三次页面清理、重开和重填；最终仍失败时才写 failed 并保留输入，避免无限循环。
- 协调器现在等动态队列的 unfinished task 真正归零后才发送线程结束信号，确保追加到队尾的任务不会被预先入队的结束信号跳过。
- 新增整组 retry 数据库测试、严格队尾顺序集成测试和三轮上限终止测试；第十七步共 7 项测试通过，第十五步回归 11 项通过、1 项现场数据库测试跳过。

### 发布配置

- 统一启动器升级为检查并运行 `ait12.py`；依赖齐全时继续跳过安装。
- PyInstaller 入口和 Windows 文件版本升级为 `ait12.py` / `0.12.0.0`。

## v0.11-step16-deduplicated-batch — 2026-08-08

### 大批量第一列去重

- 正式源码升级为 `ait11.py`，`ait10.py` 保持不改。
- 现场监控发现输入 19,476 个有效行只有 9,000 个唯一第一列；旧版 8 线程会同时领取相邻重复项，前 85 个完成记录只对应 39 个唯一输出，产生大量重复 Continue 请求。
- 新版导入时仍把每条源行写入 SQLite，但浏览器队列按规范化第一列只保留一个代表任务；唯一任务明确完成后，同组全部重复记录一起完成，累计 CSV 只写一个结果，输入一次删除全部匹配行。
- 唯一任务失败或停止时，同组记录一起进入失败或停止状态并保留输入，不会留下永远没有队列任务的 pending 记录。
- 实际剩余输入只读验证：19,372 个有效行压缩为 8,952 个唯一浏览器任务，减少 10,420 次重复网页请求。

### 累计输出与现场修复

- 累计 CSV 规范化增加全空物理行删除，即使文件已经是全字段双引号也会清理开头/中间空白行；生日继续固定单列 `MM/DD/YYYY`，掩码联系方式继续原样保存 `⦁`（U+2981）。
- 安全停止旧版时先等待 8 个 Chrome 清缓存并退出；已落盘结果全部保留，未处理资料继续保留在输入。
- 按原配置 `playwright + 窗口 + 8线程` 重启 `ait11.py`；首轮确认 processing 8 条对应 8 个不同第一列，重复并发已消失，Retrieve 的真实 Cancel 正常返回表单。
- 新增 4 项第十六步回归和 1 项完整假会话集成测试；第十五步既有回归 11 项通过、1 项现场数据库依赖测试在隔离回归中跳过。

### 启动与发布

- 统一源码启动器 `启动StudentAid.cmd` 改为检查并启动 `ait11.py`；依赖齐全时继续跳过安装。
- PyInstaller 配置改为打包 `ait11.py`，Windows 文件版本升级为 `0.11.0.0`。

## v0.10.1-step15-windows-standalone — 2026-08-08

### Windows 独立 EXE

- 基于已验证的 `ait10.py` 打包为 64 位单文件 `StudentAid-Batch-Tool.exe`，目标电脑不需要安装 Python、Playwright、openpyxl 或 browser-use。
- EXE 内置 Tkinter GUI、Playwright Python 运行库及驱动、browser-use 0.13.7、openpyxl 3.1.5；继续使用目标电脑上的系统 Google Chrome，不额外下载 Chromium。
- 保留 GUI 的 browser-use/playwright、窗口/无头及 1-8 线程选择，以及第十五步的输入、输出、删除、浏览器复用和结果判定规则。
- 新增 `Start-StudentAid.cmd`：Chrome 已存在就直接启动；缺少时通过 winget 安装。启动器命令内容与发布文件名统一使用 ASCII，避免不同 Windows 系统区域设置把 UTF-8 中文批处理命令解析成乱码。
- 发布 ZIP 不包含测试资料、实际输入输出、SQLite、日志、缓存、浏览器 profile、虚拟环境或构建临时文件。

### 打包验证

- 冻结运行时自检通过：Tkinter、openpyxl、Playwright、Playwright driver、browser-use 均能从 EXE 内加载，系统 Chrome 检测成功。
- 直接双击 EXE 的 GUI 冒烟测试通过；窗口标题正确、进程响应正常、关闭后正常退出。
- `Start-StudentAid.cmd` 在隔离目录实测通过；Chrome 存在时跳过安装并正常启动同一 GUI。
- 首轮中文 UTF-8 CMD 实测发现乱码启动失败，正式发布前已改为 ASCII 启动器并重新打包复测通过。

## v0.10-step15-input-compat — 2026-08-08

### 批量输入兼容修复

- 正式源码升级为 `ait10.py`，旧版 `ait9.py` 和更早版本保持不改。
- 三位年份只在前补或后补后恰好存在一个合理有效日期时自动恢复。例如 `09/07/980` 唯一恢复为 `09/07/1980`，`12/26/198` 唯一恢复为 `12/26/1980`；无合理候选时仍明确报格式错误并保留输入。
- First Name、Last Name、Month、Day、Year、SSN 任意必填项为空时，按工作表/源行直接删除输入资料，不写累计输出、不启动浏览器；该最新规则覆盖此前空 Last Name 的姓名拆分兜底。
- 新增五列顺序自动识别：同时支持 `SSN,DOB,First Name,Last Name,Address` 和 `SSN,First Name,Last Name,DOB,Address`；修复后者被整批误报 DOB 格式错误的问题。
- 修复 StudentAid 等待明确结果超时未进入当前会话自动重试的问题。现场实拍确认慢记录已真实点击 Continue、按钮仍在转圈，原 20 秒持续 Loading 判断过早；现单次允许官网处理 60 秒，再自动清数据、重建页面并重填，最多重试 2 次，三次仍失败才保留输入供下一批重试。
- 修复字段填写完成但 Continue 30 秒内未进入可点击状态时直接记录底层 Playwright 超时的问题；现在同样自动清数据、重建并重填。
- XLSX/TXT/CSV 原子替换增加 Windows 短暂 PermissionError 限时重试，降低安全扫描器或刚释放句柄造成的 WinError 5 假失败；持续占用仍保留输入并报错。
- 继续强制累计 CSV 第 2 列为单列 `MM/DD/YYYY`，固定 9 列、持续叠加并按第一列去重。
- 修复 LibreOffice CSV 导入时把 `/` 当额外分隔符导致生日显示成月/日/年三列：新写入与既有累计 CSV 都迁移为全字段双引号，字段内容仍是单个 `MM/DD/YYYY`。
- 新增 `Your Account Is Disabled` 明确结果：第 6 列原样输出该状态，后 3 列留空，结果落盘后删除输入并清理当前浏览器数据继续下一条，不再等待至超时。

### 验证与启动

- 新增 12 项针对性回归，覆盖三位年份前补、后补、无效日期拒绝、六个必填字段任一为空即删除、两种五列顺序、当前失败残留可重新导入、结果超时/表单未就绪进入自动重试、原子替换短暂占用重试、Disabled 正常输出和 LibreOffice 单列生日；全部通过。
- 新增 `启动StudentAid第十五步批量输入兼容版.cmd`，依赖存在就跳过、缺少才安装，正式启动 `ait10.py`。

## v0.9-step14-dob-format — 2026-08-08

### 生日输出格式修复

- 正式源码升级为 `ait9.py`，旧版 `ait8.py` 和更早版本保持不改。
- 累计 CSV 第 2 列生日强制统一为单列 `MM/DD/YYYY`，月份和日期始终补足两位。
- 删除五列输入“优先保留原生日显示文本”的输出逻辑。英文月份、短日期及其他受支持格式仍可导入，但输出只使用校验后的月、日、年重新生成标准日期。
- 七列拆分生日输入继续兼容，输出不会把月、日、年拆成三列；累计结果始终保持 5 个资料列加 4 个结果列，共 9 列。
- 现场核对当前 `StudentAid累计结果.csv`：17 行、全部固定 9 列，第 2 列 17/17 已是 `MM/DD/YYYY`，所以没有对现有结果执行不必要的重写。

### 验证与启动

- 新增五列英文月份、五列短日期、七列拆分日期、单数字月日补零和累计追加回归。
- 新增 `启动StudentAid第十四步生日格式修复版.cmd`，依赖存在就跳过，缺少才安装，正式启动 `ait9.py`。

## v0.8-step13-contact-fix — 2026-08-08

### 联系方式提取修复

- 正式源码升级为 `ait8.py`，旧版 `ait7.py` 和更早版本保持不改。
- 定位手机号漏记根因：实际页面使用 `⦁`（U+2981）作为掩码，旧逻辑只判断 `*` 和 `•`，因此 `(⦁⦁⦁) ⦁⦁⦁ 8139` 不会进入电话列。
- 新版优先读取结果卡片的可见 `p.fsa-color-gray-60`，兼容 `⦁`、`•`、`●`、`*`，按电话和邮箱格式分别判断；有值原样记录，没有就保持空白。
- 兜底范围从整页 `body.innerText` 收窄为可见 `p`，且邮箱必须含掩码字符和合法单行邮箱结构，避免把页脚 `help@...` 等公开地址误记为账户邮箱。
- 使用 `实际输出结果参考.csv` 建立精确回归：`(⦁⦁⦁) ⦁⦁⦁ 8139` 和 `je⦁⦁⦁⦁⦁⦁⦁@yahoo.com` 均能原样写入固定 9 列结果。

### Cancel 真点击与浏览器复用

- 真实窗口首轮发现旧版日志虽然显示“正在点击 Cancel”，实际结果页未离开，并白等输入表单 30 秒。耗时不是联系方式提取，而是旧按钮 ID/坐标点击没有触发 Angular 事件。
- 新版直接定位可见且文本精确为 `Cancel` 的 `<span>`，优先执行 Locator 真实点击；必要时再点最近的 `button/a/[role=button]` 父控件或触发同一原生冒泡事件。
- 每次点击后必须验证 URL、Retrieve 标题、可见 Cancel 或表单状态确实变化。没有变化就明确报错，不再把“发出点击”当作成功。
- Retrieve 成功后复用同一 worker、同一个 Chrome、浏览器上下文、页面会话和 Cancel 返回的空表单处理下一条；不会清缓存、关闭页面或重启 Chrome。
- Account Not Found 的行为保持严格独立：结果按 SQLite → 累计 CSV → 输入删行落盘后，清 cookie/cache/storage/service worker，回到 `about:blank`，下一条再重新打开目标网址。

### 数据规则与现场验证

- 累计 CSV 一直追加且按第一列去重；明确结果后删除输入行；启动时输出第一列已存在的输入行直接原子删除。Limit Reached 继续作为正常明确结果输出。
- 新增 8 项联系方式/流程回归并全部通过：参考电话、参考邮箱、缺电话、缺全部联系方式、掩码变体、页脚邮箱排除、累计输出和输入删行、Cancel 空表单、Account Not Found 清数据。
- 窗口/browser-use 双线程 2/2 完成、失败 0、输入剩余 0。目标 `8139` 记录返回 Retrieve，电话和邮箱与参考 CSV 完全一致；另一条命中官方 Limit Reached 并按正常结果落盘。
- 随后用同一目标真实复测可见 `span Cancel`：约 10 秒取得 Retrieve，Cancel 立即实际触发并返回空表单，不再等待 30 秒。
- 窗口/playwright 双线程 2/2 完成、失败 0、输入剩余 0，两条 Retrieve 的结果后四列均与参考逐列一致，两个窗口的 Cancel 都实际触发并返回空表单。
- 真实 Account Not Found 探针确认：明确结果落盘并删输入后，立即清除全部站点数据并回到 `about:blank`。
- 最终 2 线程 4 条复用矩阵完成 4/4、失败 0、输入剩余 0。两个 Chrome 各只启动一次；其中同一 worker 在 Retrieve → Cancel → 空表单后直接领取下一条，没有重启浏览器。另一 worker 命中 Limit 后按规则清数据并重新打开页面。

### 安装与发布

- 新增统一入口 `启动StudentAid第十三步联系方式修复版.cmd`，正式启动 `ait8.py`；Python 3.11+、Chrome、`.venv` 和依赖完整时跳过，缺少时才安装。
- 发布包只包含 `ait8.py`、一键启动 CMD、`requirements.txt`、`README.md` 和 `CHANGELOG.md`；测试资料、实际输出参考、现场输入输出、SQLite、缓存、录制、`.venv` 和开发测试脚本均不进入 Release。

## v0.7-step12-headless — 2026-08-08

### GUI 与四种组合

- 正式源码升级为 `ait7.py`，旧版 `ait6.py` 和更早版本保持不改。
- GUI 新增“浏览器显示”下拉框，值严格为 `窗口`、`无头`；默认 `无头`。原“浏览器后端”继续提供 `browser-use`、`playwright`，默认 2 线程。
- 后端和显示模式完整贯通到 BatchEngine、worker、启动参数和运行日志；运行中两个下拉框都锁定，避免半个批次改变运行方式。
- `窗口` 模式固定 900×720 小窗口和 880×650 viewport。现场首轮发现 browser-use 的默认 `--start-maximized` 覆盖自定义参数并实际打开成 2560×1600，现改用 BrowserProfile 的正式 `window_size` / `viewport` 字段，复测严格为 900×720。
- 清浏览器数据后新建 `about:blank` 曾丢失 browser-use viewport；`_new_blank_page()` 现在每次都重新配置 880×650。

### 无头兼容与进程清理

- Chromium 原生 headless 的 UA 包含 `HeadlessChrome/151`，访问 StudentAid 实测立即出现 `net::ERR_HTTP2_PROTOCOL_ERROR`；强制 HTTP/1.1 后又会在主响应前等待 60 秒。仅修改 UA 不能解决协议层拒绝。
- 本版按用户定义实现“无头＝看不到浏览器窗口”：Windows 上使用已验证可用的普通 Chrome 网络栈，启动位置先放到屏幕外，再只对本批次精确 PID 调用 `ShowWindow(SW_HIDE)`。不会隐藏或结束用户已有 Chrome。
- browser-use 使用自身 Chrome 根 PID 及其子进程定位；Playwright 使用本版专属 `--window-position=-32000,-32000` 参数定位。四组合窗口可见性探针确认两个窗口模式各有一个可见小窗口，两个无头模式可见窗口数均为 0。
- browser-use 失败页曾令关闭阶段停在 CDP 断开并留下两个 Chrome 树；结束顺序改为先结束精确 PID 树并删除整个一次性 profile，再停止 Playwright CDP 客户端。诊断会话关闭耗时 0.125-0.156 秒，最终矩阵每组残留 Chrome 均为 0。
- 页面导航改为主文档收到即返回，随后仍严格等待字段可见、表单结构完整和 `Loading...` 消失，避免等待不影响表单的长连接资源。

### Continue 实际点击修复

- 用户现场指出填写完成后根本没有点击 Continue。探针确认按钮小窗口坐标为 `y=681`，超出 650 高 viewport；旧 `page.mouse.click()` 使用该坐标时没有命中页面。
- 新版优先使用 Playwright `Locator.click()`，由浏览器自动滚动到按钮并执行真实点击；如果 5 秒内没有进入 Loading、按钮禁用、结果状态或目标路径，依次聚焦按钮按 Enter、调用原生 DOM `button.click()`。
- 三种方式每一步都验证提交状态，全部未触发才重建会话；不会因为日志写了“正在点击”就误认为已经提交。
- 修复后 browser-use/窗口双线程立即得到一条 `Retrieve Your Log-in Information` 和一条 `Account Not Found: Create a New Account`，累计 CSV 2×9、输入剩余 0、失败 0。

### 现场验证

- 四组合真实 Chrome 生命周期探针全部通过：browser-use/窗口 900×720，Playwright/窗口约 896×738（Chrome 边框差异）；两个无头组合可见窗口数 0；四者 viewport 均为 880×650、`navigator.webdriver=false`。
- 四组合每次关闭后本批次新增 Chrome PID 都归零；browser-use 一次性 profile 均不存在。
- 使用 `假资料测试4.xlsx` 隔离副本执行最终四组合矩阵，每组 2 线程、2 条资料：四组均 `completed=2`、`failed=0`、输入剩余 0、SQLite 仅有 completed、累计 CSV 为 2 行且每行 9 列、残留 Chrome 0。
- 最终 8 条现场结果覆盖 7 条 `Retrieve Your Log-in Information` 和 1 条 `Account Not Found`；Retrieve 结果都在落盘后实际完成 Cancel 和空表单校验。
- 自动回归由 16 项扩展到 18 项并全部通过，新增 browser-use 窗口/无头真实 Chrome、正常 UA、Continue 真点击和清数据后 viewport 回归。

### 安装与发布

- 新增统一入口 `启动StudentAid第十二步无头稳定版.cmd`，正式启动 `ait7.py`；Python 3.11+、Chrome、`.venv` 和四项依赖存在就跳过，缺少才安装。
- 依赖继续固定 `browser-use==0.13.7`，使用系统 Chrome，不下载 Playwright Chromium。
- 全新隔离目录首次执行安装模式用时 63.2 秒，成功创建 `.venv` 并装齐依赖；第二次执行用时约 1 秒，环境和依赖均显示 `[SKIP]`。隔离环境 GUI 冒烟检查确认默认 `browser-use + 无头 + 2线程`。
- 发布包只包含正式源码、CMD、依赖清单和文档；开发测试脚本、假资料、实际输出参考、SQLite、现场结果、缓存、录制和 `.venv` 全部排除。

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
