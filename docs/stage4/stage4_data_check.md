# 阶段四数据检查报告
生成时间: 2026-10-27 20:06:22

### composite_holdings_lasso_horizon_all8.csv
- shape: (2600, 4)
- columns(4): ['signal_date', 'trade_date', 'symbol', 'rank']
- trade_date 范围: 2020-06-01 ~ 2024-09-02
- signal_date 范围: 2020-05-29 ~ 2024-08-30
- symbol 样例: ['000595', '002575', '002289']
- trade_date 样例: ['2020-06-01', '2020-07-01', '2020-08-03']

### composite_bt_lasso_horizon_all8.csv
- shape: (51, 8)
- columns(8): ['signal_date', 'trade_date', 'next_trade_date', 'gross_ret', 'turnover', 'cost', 'net_ret', 'n_holding']
- trade_date 范围: 2020-06-01 ~ 2024-08-01
- signal_date 范围: 2020-05-29 ~ 2024-07-31
- next_trade_date 范围: 2020-07-01 ~ 2024-09-02
- trade_date 样例: ['2020-06-01', '2020-07-01', '2020-08-03']

### composite_bt_summary.csv
- shape: (10, 15)
- columns(15): ['tag', 'label', 'n_periods', 'ann_return', 'ann_vol', 'sharpe', 'max_drawdown', 'calmar', 'win_rate', 'pnl_ratio', 'avg_turnover', 'bench_ann', 'excess_ann', 'excess_cum', 'nav_final']

### composite_weights_lasso_horizon_all8.csv
- shape: (11, 53)
- columns(53): ['Unnamed: 0', '2020-05-29', '2020-06-30', '2020-07-31', '2020-08-31', '2020-09-30', '2020-10-30', '2020-11-30', '2020-12-31', '2021-01-29', '2021-02-26', '2021-03-31', '2021-04-30', '2021-05-31', '2021-06-30', '2021-07-30', '2021-08-31', '2021-09-30', '2021-10-29', '2021-11-30', '2021-12-31', '2022-01-28', '2022-02-28', '2022-03-31', '2022-04-29'] ...

### industry_map.parquet
- shape: (7740, 5)
- columns(5): ['ts_code', 'l1_code', 'l1_name', 'in_date', 'out_date']
- 缺失率 Top: out_date=67.3%
- ts_code 样例: ['000001.SZ', '000002.SZ', '000004.SZ']

### hs300_weight.parquet
- shape: (18000, 3)
- columns(3): ['trade_date', 'con_code', 'weight']
- trade_date 范围: 2020-01-23 ~ 2024-12-31
- trade_date 样例: ['2020-01-23', '2020-02-28', '2020-03-31']

### hs300_benchmark.parquet
- shape: (1213, 8)
- columns(8): ['trade_date', 'open', 'high', 'low', 'close', 'pct_chg', 'vol', 'amount']
- trade_date 范围: 2019-09-30 ~ 2024-09-30
- trade_date 样例: ['2019-09-30', '2019-10-08', '2019-10-09']

### mktcap_panel.parquet
- shape: (1200, 4853)
- columns(4853): ['000001', '000002', '000006', '000007', '000008', '000009', '000011', '000012', '000014', '000017', '000019', '000020', '000021', '000025', '000026', '000027', '000028', '000029', '000030', '000031', '000032', '000034', '000035', '000036', '000037'] ...
- index 范围: 2019-09-30 ~ 2024-09-30
- 缺失率 Top: 301551=99.9%, 301618=99.9%, 688615=99.8%, 603091=99.4%, 301600=99.1%, 301607=98.6%, 001277=98.5%, 688710=98.5%

### stock_basic.parquet
- shape: (5573, 6)
- columns(6): ['ts_code', 'symbol', 'name', 'industry', 'market', 'list_date']
- 缺失率 Top: industry=0.0%
- symbol 样例: ['920157', '920202', '920025']
- ts_code 样例: ['920157.BJ', '920202.BJ', '920025.BJ']
- industry 样例: ['通信设备', '汽车配件', '专用机械']

### final_factor_list.csv
- shape: (8, 6)
- columns(6): ['factor', 'flipped', 'category', 'IC_20D_raw', 'IC_20D_final', 'note']

### factor_ic_daily_1d.parquet
- shape: (1199, 8)
- columns(8): ['turnover', 'volatility_20', 'amihud_20', 'bp', 'corr_pv_20', 'reversal_20', 'bias_20', 'ep_ttm']
- index 范围: 2019-09-30 ~ 2024-09-27
- 缺失率 Top: volatility_20=0.8%, amihud_20=0.8%, reversal_20=0.8%, corr_pv_20=0.8%, bias_20=0.8%

### quantile_returns_volatility_20.csv
- shape: (1173, 11)
- columns(11): ['Unnamed: 0', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

### brinson_lasso_all8_2023.csv
- shape: (12, 14)
- columns(14): ['signal_date', 'trade_date', 'next_date', 'n_holdings', 'Rp', 'Rb', 'excess', 'A', 'S', 'I', 'residual', 'n_unknown_port', 'n_unknown_bench', 'n_industries']
- trade_date 范围: 2023-01-03 ~ 2023-12-01
- signal_date 范围: 2022-12-30 ~ 2023-11-30
- trade_date 样例: ['2023-01-03', '2023-02-01', '2023-03-01']

## daily_basic 逐年检查

### daily_basic_2020
- shape: (946540, 5)
- ts_code 样例: ['300120.SZ', '603595.SH', '300218.SZ']
- trade_date 样例: ['20200102', '20200103', '20200106']
- 缺失率: pb=0.9%, pe_ttm=17.5%, turnover_rate=0.0%

### daily_basic_2021
- shape: (1062121, 5)
- ts_code 样例: ['603159.SH', '600812.SH', '002712.SZ']
- trade_date 样例: ['20210104', '20210105', '20210106']
- 缺失率: pb=0.9%, pe_ttm=15.8%, turnover_rate=0.0%

### daily_basic_2022
- shape: (1171418, 5)
- ts_code 样例: ['000503.SZ', '002492.SZ', '301086.SZ']
- trade_date 样例: ['20220104', '20220105', '20220106']
- 缺失率: pb=0.8%, pe_ttm=17.9%, turnover_rate=0.0%

### daily_basic_2023
- shape: (1258734, 5)
- ts_code 样例: ['600521.SH', '300215.SZ', '300884.SZ']
- trade_date 样例: ['20230103', '20230104', '20230105']
- 缺失率: pb=0.7%, pe_ttm=21.9%, turnover_rate=0.0%

### daily_basic_2024
- shape: (967096, 5)
- ts_code 样例: ['002465.SZ', '002913.SZ', '920578.BJ']
- trade_date 样例: ['20240102', '20240103', '20240104']
- 缺失率: pb=0.6%, pe_ttm=23.2%, turnover_rate=0.0%
