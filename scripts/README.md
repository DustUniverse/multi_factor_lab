# scripts 脚本目录

本目录存放项目可执行脚本，按用途分为 `data / quality / factors / probe` 四类。

## 运行前准备

```powershell
cd C:\Users\16075\code\multi_factor_lab
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## 子目录说明

| 子目录 | 用途 | 典型内容 |
|---|---|---|
| `data/` | 数据拉取与构建 | 腾讯日线、Tushare `daily_basic`、`fina_indicator`、PIT 财务面板 |
| `quality/` | 数据质量检查 | 缺失率、重复值、极端涨跌幅、面板完整性 |
| `factors/` | 因子面板构建 | `build_factor_panel.py`（18 因子主入口） |
| `probe/` | 接口探测与临时诊断 | AKShare 参数探测、Tushare 字段检查 |

## 常用脚本

| 脚本 | 说明 | 输出 |
|---|---|---|
| `scripts/factors/build_factor_panel.py` | 一键生成 18 因子面板，主入口 | `data/processed/factor_panel.parquet`，5,088,372 行 × 20 列 |
| `scripts/factors/build_factor_panel_11f.py` | 旧 11 因子面板脚本，保留兼容 | `data/processed/factor_panel_11f.parquet` |

> 其他数据拉取、质量检查脚本以仓库实际文件为准，新增后请更新本表。

## 注意事项

- Tushare 批量拉取必须在干净 IP 下进行，校园网可能触发“IP 数量超限”。
- 抓取脚本应支持断点续传，跳过已存在文件。
- 运行脚本报 `ModuleNotFoundError: mfalpha` 时，先执行 `pip install -e .`。
- 输出文件默认写入 `data/processed/`，该目录不提交 Git。