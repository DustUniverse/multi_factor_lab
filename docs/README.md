# docs 文档目录

本目录维护项目文档、验收表和阶段报告。根 README 只放总览和索引，详细文档放在这里。

## 文件索引

| 文件 | 说明 |
|---|---|
| `stage1_checklist.md` | 阶段一验收表，状态：全部通过 ✅ |
| `reports/data_quality_report_tencent.md` | 腾讯前复权数据质量报告，单字段缺失率 < 2% |

## 阶段一文档

- 数据覆盖：4853 只股票（96.5%）
- 时间跨度：2019-09-30 ~ 2024-09-30，1213 个交易日
- 因子库：18 个
- 单元测试：59 passed

## 阶段二文档计划

| 文档 | 内容 | 状态 |
|---|---|---|
| `reports/factor_ic_report.md` | 18 因子 IC / ICIR / 分层收益汇总 | 待创建 |
| `reports/neutralization_report.md` | 行业、市值中性化说明与结果 | 待创建 |
| `reports/backtest_report.md` | 回测骨架、净值曲线、绩效指标 | 待创建 |
| `reports/attribution_report.md` | 收益归因分析 | 待创建 |

## 维护规则

- 新增报告后，在本 README 和根 README 的“子目录 README 索引”中同步更新。
- 报告文件名建议使用小写英文 + 下划线，例如 `factor_ic_report.md`。
- 涉及数据的结论必须写清楚数据区间、股票池、因子版本和运行脚本。