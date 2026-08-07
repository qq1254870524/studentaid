# StudentAid 批量处理工具（第八步实测）

Windows 桌面 GUI，用于在授权测试环境中批量验证 Federal Student Aid 账户信息找回流程。输入资料写入本地 SQLite（WAL），由独立浏览器处理线程执行，批次结束后导出 UTF-8 BOM CSV。

## 第八步修复

- 新增 Chrome CDP 复用模式，解决新 Playwright 浏览器访问站点时可能出现的 `ERR_HTTP2_PROTOCOL_ERROR`。
- 修复输入页标题被误判为成功结果：现在会等待 `Loading...` 结束，再判断 `Account Not Found`、找回结果或站点错误。
- 站点返回 `An unknown error has occurred` 时会准确记为失败，不再写成完成。
- 共享 Chrome 只断开自动化连接，不会被脚本关闭。
- GUI 状态区会显示 `完成（有失败）`，避免批次有失败时显示为全部成功。

## 安装

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

也可以双击 `安装StudentAid第八步.cmd`。

## 运行

双击：

```text
启动StudentAid第八步.cmd
```

或：

```powershell
python -B ait3.py
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
python -B ait3.py
```

关闭自动探测、强制使用 Playwright 独立浏览器：

```powershell
$env:STUDENTAID_CDP_URL='off'
python -B ait3.py
```

启动可连接的 Chrome 示例：

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

第八步实测覆盖：GUI 启动、输入导入、CDP 浏览器、页面提交等待、站点错误识别、SQLite WAL、CSV 导出和失败状态显示。

## 隐私

- 不要提交真实输入表、数据库或结果文件。
- 日志不显示 SSN 和整条原始资料。
- 仅保存页面已脱敏的联系方式，不推测完整信息。
