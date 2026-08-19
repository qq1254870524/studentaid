# StudentAid v0.32.0 HTTP 快速版源码

发布日期：2026-08-19

## 发布定位

本次发布把 `ait23.py` 至 `ait32.py` 已完成并验证的 HTTP 直连、万能输入适配、大文件持久化和 Windows 输出权限修复汇总为最新源码包。正式入口为 `ait32.py`；GUI 中将“搜索后端”选择为 `http` 即启用 HTTP 快速模式。

本次只整理和发布已验证源码，不改变 `ait32.py` 的搜索逻辑、结果字段或默认配置；已有用户配置仍按原值加载。

## HTTP 快速模式

- 每个 worker 使用独立 `requests.Session`，完成官网页面、keep-alive、sessionUser、gateway session、Cookie 与 CSRF 初始化后调用账户找回 JSON 接口。
- 401/403 自动重建会话一次；429、5xx 和未知响应进入原有队尾重试，不误记为明确完成。
- 官网恢复联系方式在写入累计结果前按展示规则遮挡；HTTP 模式与 `browser-use`、`playwright` 共用 SQLite、完整行去重、累计 CSV 和输入同步流程。
- GUI 仍保留三个后端：`http`、`browser-use`、`playwright`。快速处理时选择 `http`；需要浏览器页面流程时可切回原后端。

## v0.23.0 至 v0.32.0 累计更新

1. 新增 HTTP 官方接口直连后端与会话自动恢复。
2. 自动识别任意列顺序、中英文/供应方前缀表头、结果字段优先映射和多种 DOB 格式。
3. 无表头宽表按内容特征推断 SSN、DOB、姓名和地址，保留首行真实数据。
4. 去重、启动恢复、累计输出判重和输入删除统一使用完整原始输入行。
5. GUI 清空数据库改为后台执行，避免 Tk 主线程卡死。
6. 大型 XLSX 运行期间不再反复整表重写；批末通过 worksheet XML 单遍同步删除已完成资料。
7. 累计 CSV 自动迁移混合宽度旧行，固定 `Result Heading` 为唯一最后一列。
8. 自动修复输出目录及 SQLite WAL/SHM 的 Windows ACL，避免只读数据库和只读 CSV。
9. 最新 Step37 修复 Tab 分隔 TXT 字段内含逗号时的误判，并修复无表头宽表中城市/州抢占姓名列的问题。

## 最新现场验证

- `导入资料/8.18 强.txt`：4 行、每行 12 列，成功 4，失败 0。
- 字段映射：First Name 第 3 列、Last Name 第 4 列、Address 第 7 列、SSN 第 11 列、DOB 第 12 列。
- 12 个原始输入字段全部按原顺序保留；`Masked Phone`、`Masked Email`、`Recovery Method`、`Result Heading` 固定追加在末尾，状态位于唯一最后一列。

## 自动验证

- 命令：`python -B -m unittest tests.test_ait32 -v`
- 结果：`Ran 75 tests`，`OK (skipped=3)`。
- 跳过项均为当前机器缺少对应历史现场输入文件；其余 72 项通过。

## 源码包内容

- `ait32.py`：正式源码入口。
- `tests/test_ait32.py`：最新自动测试。
- `启动StudentAid.cmd`：Windows 一键检查依赖并启动源码 GUI。
- `requirements.txt`：运行依赖，包含 `requests`。
- `StudentAid.spec`、`version_info.txt`、`requirements-build.txt`、`exe_selftest_hook.py`：可选 PyInstaller 构建文件。
- `README.md`、`CHANGELOG.md`、本发布说明和 `PACKAGE_MANIFEST.txt`。

## 使用

1. 完整解压 `StudentAid-v0.32.0-HTTP-Fast-Source.zip`。
2. 双击 `启动StudentAid.cmd`；启动器会复用或创建 `.venv` 并补装缺少的依赖。
3. 在 GUI 中选择输入文件和累计输出 CSV。
4. 将“搜索后端”选择为 `http`，设置线程数后开始。

## 校验

下载后使用 PowerShell：

```powershell
Get-FileHash .\StudentAid-v0.32.0-HTTP-Fast-Source.zip -Algorithm SHA256
```

将输出与 Release 附件 `SHA256SUMS.txt` 对照。
