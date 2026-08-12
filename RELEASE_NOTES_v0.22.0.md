# StudentAid v0.22.0 Step27 源码正式版

发布日期：2026-08-12

## 本次修复

- 累计输出完整保留输入文件的全部列，不删除、不替换、不调整顺序。
- 页面结果只追加在原始输入行最后：`Result Heading`、`Masked Phone`、`Masked Email`、`Recovery Method`。
- 完整行去重、启动同步和结果完成后的输入删行统一使用原始输入整行。
- 同一 SSN 但其他任意列不同的资料继续分别处理。
- `E:\studentaid\存资料处` 的 MyLife 输入为 20 列；新版验证输出为原始 20 列加 4 个结果列，共 24 列。

## 保持不变

- Continue 和真实 Cancel 点击。
- `browser-use` / `playwright`、窗口 / 无头和任意正整数线程。
- 每线程浏览器复用、Account Not Found 清数据、明确结果识别、GUI 实时进度。
- SQLite 状态、累计追加、输入删除时机、停止清缓存和结束浏览器进程。

## 验证结果

- `ait21.py` 基线：`Ran 40 tests ... OK`。
- `ait22.py`：`Ran 40 tests ... OK`。
- 现场文件探针：94 条有效资料生成结果的前 20 列均与原始输入行逐字段一致，输出宽度全部为 24。
- 一键启动安装检查通过，不生成或上传 EXE。

## 启动

解压源码 ZIP 后双击：

```text
启动StudentAid.cmd
```

依赖齐全时直接跳过安装，缺少时自动安装；正式入口为 `ait22.py`。
