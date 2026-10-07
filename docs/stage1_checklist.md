# 阶段一验收表 — multi_factor_lab

> 最后更新：2026-10-07
> 阶段目标：全市场数据体系搭建 + 三大类基础因子库（价量/财务/技术，≥18 个因子）

---

## 一、数据体系

| 验收项 | 标准 | 实际 | 状态 |
|---|---|---|---|
| 股票池规模 | 全市场 A 股 | 5026 只，成功抓取 4853 只（96.5%） | ✅ |
| 覆盖板块 | 主板 / 创业板 / 科创板 | 全覆盖 | ✅ |
| 时间跨度 | ≥ 5 年 | 2019-09-30 ~ 2024-09-30，1213 个交易日 | ✅ |
| 复权处理 | 前复权 | 腾讯前复权 | ✅ |
| 停牌处理 | 不含停牌日 | 前复权数据不含停牌日 | ✅ |
| 退市处理 | 含退市股（无幸存者偏差） | 含退市股 | ✅ |
| 单字段缺失率 | < 2% | 均 < 2% | ✅ |
| 清洗后面板 | — | 5,088,372 行 × 12 列 | ✅ |
| 质量报告 | 有 | `docs/reports/data_quality_report_tencent.md` | ✅ |

**清洗后面板列名**：`symbol, date, open, high, low, close, volume, pct_chg, board, is_suspended, is_limit_up, is_limit_down`

---

## 二、因子库（18 个）

### 价量类（7 个）

| 因子 | 说明 | 缺失率 |
|---|---|---|
| momentum_20 | 20 日动量 | 1.91% |
| reversal_20 | 20 日反转 | 1.91% |
| volatility_20 | 20 日波动率 | 1.91% |
| corr_pv_20 | 20 日量价相关性 | 1.81% |
| volume_ratio | 量比 | 1.81% |
| amplitude_20 | 20 日振幅 | 1.91% |
| amihud_20 | Amihud 非流动性（close × volume 近似） | 1.91% |

### 技术类（4 个）

| 因子 | 说明 | 缺失率 |
|---|---|---|
| rsi_14 | 相对强弱指标（Wilder 平滑） | 1.33% |
| bias_20 | 20 日乖离率 | 1.81% |
| boll_dev_20 | 布林带偏离 | 1.81% |
| macd_dev | MACD 偏离（已归一化） | 3.14% |

### 财务类（4 个，PIT 对齐）

| 因子 | 说明 | 缺失率 |
|---|---|---|
| roe | 净资产收益率 | 0.37% |
| netprofit_yoy | 净利润同比增速 | 0.06% |
| or_yoy | 营业收入同比增速 | 0.16% |
| debt_to_assets | 资产负债率 | 0.02% |

### 估值类（2 个）

| 因子 | 说明 | 缺失率 |
|---|---|---|
| ep_ttm | 1 / PE_TTM（PE 倒数） | 17.39% |
| bp | 1 / PB（PB 倒数） | 1.24% |

### 换手类（1 个）

| 因子 | 说明 | 缺失率 |
|---|---|---|
| turnover | 换手率（daily_basic） | 0.84% |

**说明**：
- 财务类采用 Point-in-Time 对齐（按 `ann_date` 公告日生效），已规避前视偏差
- `ep_ttm` 缺失率偏高（17.39%）属正常：亏损股 PE 无意义，返回 NaN
- `turnover` 原计划用流通股本自算，后直接采用 Tushare `daily_basic` 的换手率字段

---

## 三、工程与测试

| 验收项 | 标准 | 实际 | 状态 |
|---|---|---|---|
| 单元测试 | 覆盖所有因子 | 59 passed（含 PIT 对齐、估值因子） | ✅ |
| 代码风格 | black + isort + flake8 | pre-commit 全过 | ✅ |
| 因子模块风格 | 单股票 `pd.Series` 输入，等长输出 | 统一 | ✅ |
| 目录结构 | scripts 按用途分类 | data / quality / factors / probe | ✅ |

**测试清单**（59 个）：
- 价量类 7 个：amihud / amplitude / corr_pv / momentum / reversal / volatility / volume_ratio
- 技术类 4 个：bias / boll_dev / macd_dev / rsi
- 财务类 1 个：turnover（旧测试）
- 基础工具 2 个：pit_align / valuation

---

## 四、一键脚本

| 脚本 | 用途 | 输出 |
|---|---|---|
| `scripts/factors/build_factor_panel.py` | **主入口**，生成 18 因子 | `data/processed/factor_panel.parquet` |
| `scripts/factors/build_factor_panel_11f.py` | 历史保留，生成 11 因子 | `data/processed/factor_panel_11f.parquet` |
| `scripts/data/fetch_daily_basic.py` | 拉取 daily_basic | `data/raw/financial/daily_basic_*.parquet` |
| `scripts/data/fetch_fina_indicator.py` | 拉取财务指标 | `data/raw/financial/fina_indicator_part_*.parquet` |

**主入口输出**：5,088,372 行 × 20 列（symbol + date + 18 因子）

---

## 五、交付物清单

| 交付物 | 路径 | 状态 |
|---|---|---|
| 清洗后日线面板 | `data/processed/daily_panel_tencent_clean.parquet` | ✅ |
| 18 因子面板 | `data/processed/factor_panel.parquet` | ✅ |
| 11 因子面板（历史） | `data/processed/factor_panel_11f.parquet` | ✅ |
| 财务 PIT 面板 | `data/processed/financial_panel_pit.parquet` | ✅ |
| 数据质量报告 | `docs/reports/data_quality_report_tencent.md` | ✅ |
| 财务数据原始（daily_basic） | `data/raw/financial/daily_basic_*.parquet` | ✅ |
| 财务数据原始（fina_indicator） | `data/raw/financial/fina_indicator_part_*.parquet` | ✅ |

---

## 六、已知限制与遗留问题

1. **Tushare 校园网 IP 限制**：在校园网下批量拉取会触发"IP 数量超限"，需切换到手机热点/家庭宽带。建议后续部署 `tushareproxy` 本地缓存代理根治。
2. **财务字段为累计值**：`roe`、`netprofit_yoy`、`or_yoy` 均为年内累计（Q1/Q2/Q3/Q4 累计），因子检验时需注意季节性影响，或考虑后续差分成单季值。
3. **tushareproxy 未部署**：仅作为工程优化建议，不影响当前数据获取。
4. **未做因子有效性检验**：18 个因子尚未进行 IC / 分层回测，属于阶段二任务。

---

## 七、阶段一验收结论

| 硬指标 | 目标 | 实际 | 结论 |
|---|---|---|---|
| 数据覆盖 | 全市场 A 股 | 4853 只（96.5%） | ✅ 达成 |
| 时间跨度 | ≥ 5 年 | 5 年完整 | ✅ 达成 |
| 因子数量 | ≥ 18 | **18** | ✅ 达成 |
| 一键因子面板 | 有 | `build_factor_panel.py` | ✅ 达成 |
| 数据质量报告 | 有 | `data_quality_report_tencent.md` | ✅ 达成 |
| 单元测试 | 覆盖核心逻辑 | 59 passed | ✅ 达成 |

**阶段一验收：全部通过 ✅**

---

## 八、下一步（阶段二）

1. 因子有效性检验（IC / 分层回测）
2. 因子中性化（行业 / 市值）
3. 多因子合成与回测骨架
4. 归因分析