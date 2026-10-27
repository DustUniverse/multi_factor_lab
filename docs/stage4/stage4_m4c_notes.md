# M4c 因子轮动 / 权重平滑（定稿）

## 做了什么
1. **前视修正**：`composite_factors_lasso_horizon_v2.py` 训练窗口加 `next_trade_date <= sig`，剔除标签未实现的最后一期训练样本（原版 12 个月窗口有 1 期隐性前视）
2. **权重平滑**：每期 Lasso 系数取最近 3 期均值后再预测，降低权重跳变
3. **top_n 保持 50**（不改规格）

## 绩效（v2 scores + M4a×M4b，top_n=50）
| 指标 | 基线 | M4a×M4b | M4c 最终 |
|---|---|---|---|
| Sharpe | 1.4611 | 1.4801 | **1.5527** |
| 期频 MDD | -21.84% | -18.26% | **-16.22%** |
| 年化收益 | 53.69% | 42.55% | 43.49% |

v2 相对 M4a×M4b：Sharpe +0.073，MDD -2.04pp。权重平滑**没有削 alpha**（ann_ret 反升 0.94pp），说明降噪有效。

## 被否决的方案（含完整证据）

### top_n=25（Sharpe 1.7173 达标）
| top_n | 全期 Sharpe | 剔除 2021 | 降幅 |
|---|---|---|---|
| 20 | 1.6922 | 0.6740 | -60.2% |
| **25** | **1.7173** | **0.6831** | **-60.2%** |
| 30 | 1.6527 | 0.6701 | -59.5% |
| 50 | 1.5527 | **0.7223** | -53.5% |

**否决理由**：剔除 2021 后 top_n=25（0.6831）**低于** top_n=50（0.7223），Sharpe 优势全部来自 2021 行情；且偏离项目"持仓 50 只"规格；换手 566%、成本 4.14%。

### 流动性过滤（阶段三 §7.2 建议）
| top_pct | Sharpe |
|---|---|
| 不过滤 | 1.5527 |
| 5% | 0.7458 |
| 10% | 0.6106 |
| 20% | 0.5282 |

**否决理由**：v2 top50 中平均 **43.2%** 落在 amihud top5% 尾部，alpha 高度集中在低流动性小盘股，过滤直接砍掉 alpha。**阶段三"建议加入流动性过滤"在本策略上不成立**——这是有价值的负面结论。

## 产出
- `scripts/backtest/composite_factors_lasso_horizon_v2.py`
- `scripts/stage4/position/m4c_backtest.py`、`m4c_liquidity_filter.py`、`m4c_topn_scan.py`、`m4c_topn_fine.py`、`m4c_robustness.py`、`m4c_final.py`
- `data/processed/composite_scores_lasso_horizon_all8_v2.parquet`（gitignore）