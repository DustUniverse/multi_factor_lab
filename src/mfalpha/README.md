# mfalpha 核心包

`src/mfalpha` 是项目核心 Python 包，提供数据对齐、因子计算和后续检验 / 回测所需的基础模块。

## 目录说明

```text
src/mfalpha/
├─ data/
│  └─ pit_align.py          # 财务数据 PIT 对齐：按 ann_date 公告日生效
└─ factors/                 # 因子计算模块
   ├─ 价量类 7 个
   ├─ 技术类 4 个
   ├─ 财务类 4 个
   ├─ 估值类 2 个
   └─ 换手类 1 个
```

## 因子模块约定

- 输入：单股票 `pd.Series`；
- 参数：统一使用 `window` 参数；
- 输出：与输入等长的 `pd.Series`；
- 暖机期不足时返回 `NaN`；
- 滚动窗口的 `min_periods` 与 `window` 保持一致；
- 阶段二最终 8 因子方向已统一为"值越大 → 预期收益越高"，翻转只需乘 −1，不需重新标准化。

## PIT 对齐

财务数据必须按公告日 `ann_date` 生效，而不是报告期 `end_date`。  
相关实现：`src/mfalpha/data/pit_align.py`。

注意：

- Tushare 财务字段 `roe`、`netprofit_yoy`、`or_yoy` 是年内累计值，不是单季值；
- 同一 `ann_date + end_date` 可能有多条，需要去重；
- 未来公告日（追溯公告 / IPO 披露）在 PIT 下天然不生效。

## 导入方式

项目采用 `src` 布局，需先可编辑安装：

```powershell
pip install -e .
```

之后即可：

```python
from mfalpha.data.pit_align import ...
from mfalpha.factors import ...
```

## 测试

```powershell
python -m pytest tests
```

当前核心包相关测试均通过，总计 59 passed。

## 与阶段二的衔接

阶段二的检验、中性化、稳健性脚本位于 `scripts/validation/`，直接读取 `src/mfalpha` 计算出的因子面板。

- 最终 8 因子清单：`data/processed/final_factor_list.csv`
- 最终因子面板：`data/processed/factor_panel_final.parquet`（5,045,205 × 8，MultiIndex，方向已统一）