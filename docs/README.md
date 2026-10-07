```markdown
# docs — 文档与图表

## 文档

| 文件 | 说明 |
|---|---|
| `stage1_checklist.md` | **阶段一验收表**（已通过 ✅） |
| `reports/data_quality_report_tencent.md` | 数据质量报告（当前版本，腾讯源） |
| `reports/data_quality_report.md` | 数据质量报告（历史版本） |

## 图表

| 目录 / 文件 | 说明 |
|---|---|
| `figures/close_600519.png` | 贵州茅台收盘价示例图 |
| `figures/alphalens_ic/momentum_20/` | momentum_20 因子 IC 分析图（hist / qq / ts） |
| `figures/alphalens_ic/volatility_20/` | volatility_20 因子 IC 分析图 |

生成脚本见 [../scripts/README.md](../scripts/README.md) 中的 `analyze_factor.py` 与 `plot_close.py`。

## 维护规范

- 数据质量报告、验收表等长期文档放 `reports/` 或 `docs/` 根目录
- 单因子 IC 图放 `figures/alphalens_ic/<因子名>/`
- 阶段验收表命名：`stageN_checklist.md`