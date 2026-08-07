# StudentAid 批量处理工具（第九步源码校验）

Windows 桌面 GUI，用于在授权测试环境中批量验证 Federal Student Aid 账户信息找回流程。输入资料先写入本地 SQLite（WAL），由独立 Playwright 处理线程执行，批次结束后导出 UTF-8 BOM CSV。

## 第九步校验与修复

- `browser-use` 已独立走完真实网页流程：新开页面、等待页面就绪、填写全部字段、校验 `Continue`、点击提交、跟踪 `Loading...`，最终准确识别 `Account Not Found`。
- 确认 `An unknown error has occurred` 可由页面停留过久/会话失效触发。源码检测到该状态后会新开页面并完整重填、重提一次。
- Playwright 仍是正式运行根基；`browser-use` 不参与批量运行，只用于交叉校验 selector、交互步骤和结果判定。
- CDP 模式复用 Chrome 默认上下文并只关闭任务新开的页面，不关闭用户 Chrome。
- 输入改用真实键盘事件、逐字符输入、字段失焦和提交前稳定等待。实测修复了过快 `fill()` 导致官方页面返回 unknown error 的问题。
- 删除“姓名输入框消失即成功”的宽泛判断；只有 `Account Not Found` 或明确账户找回标志才会写成完成。
- 修复结果轮询超时比较错误，未识别页面不会无限等待。
- 每条记录实时输出打开页面、填写、提交、等待、识别等阶段；等待超过 5 秒时输出心跳。
- 每条最终结果实时写入 SQLite 并立即刷新 GUI 进度；UTF-8 BOM CSV 在批次结束或停止后统一导出。
- 日志不记录姓名、SSN、DOB、地址或整条原始资料。

## 安装

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

也可以双击：

```text
安装StudentAid第九步.cmd
```

## 运行

推荐双击：

```text
启动StudentAid第九步.cmd
```

启动器会检查本机 `http://127.0.0.1:9223`。如果 CDP 尚未启动，会使用独立用户目录启动可连接的 Google Chrome，然后运行：

```powershell
python -B ait4.py
```

支持 `.csv`、`.scv`、`.txt`、`.xlsx`。数据文件、SQLite 和结果 CSV 已由 `.gitignore` 排除，避免误上传。

## Chrome CDP 模式

程序默认探测：

```text
http://127.0.0.1:9223
```

如果 Chrome 使用其他端口：

```powershell
$env:STUDENTAID_CDP_URL='http://127.0.0.1:9333'
python -B ait4.py
```

关闭自动探测、强制使用 Playwright 独立浏览器：

```powershell
$env:STUDENTAID_CDP_URL='off'
python -B ait4.py
```

手动启动可连接 Chrome：

```powershell
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' `
  --remote-debugging-port=9223 `
  --remote-debugging-address=127.0.0.1 `
  --user-data-dir="$env:USERPROFILE\.studentaid-chrome"
```

## 测试

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m unittest discover -s tests -v
```

第九步自动测试覆盖：CDP 上下文复用、页面会话失效自动重开重填、明确结果判断、DOM 消失不误判、Loading 心跳、超时退出、实时 SQLite 日志、失败状态、CSV 导出和 SSN 前导零兼容。

第九步真实 Playwright 回归结果：1 条测试资料完成 1、失败 0；识别为 `account_not_found`；阶段日志、实时 SQLite、GUI progress 和最终 CSV 链路一致。

## 隐私

- 不要提交真实输入表、数据库、结果文件或浏览器录制。
- 日志不显示 SSN 和整条原始资料。
- 仅保存页面已经脱敏的联系方式，不推测完整信息。
