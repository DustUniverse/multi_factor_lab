# tests 单元测试

本目录存放项目单元测试。当前状态：**59 passed**。

## 运行测试

```powershell
cd C:\Users\16075\code\multi_factor_lab
.\.venv\Scripts\Activate.ps1
python -m pytest
```

期望输出包含：

```text
59 passed
```

## 覆盖范围

| 模块 | 覆盖内容 |
|---|---|
| 价量因子 | 7 个价量因子计算与边界 |
| 技术因子 | 4 个技术因子计算与暖机期 |
| 换手因子 | `turnover` |
| PIT 对齐 | 公告日生效、去重、未来公告日等 |
| 估值因子 | `ep_ttm`、`bp` |
| 其他 | 数据清洗、面板一致性等 |

## 新增测试规范

- 预期值要手算或使用可信小样本，不要凭感觉；
- 滚动窗口注意 `pct_change()` 引入的额外 NaN；
- MACD 暖机期为 `slow + signal - 2`；
- 新增因子必须同时新增对应单测；
- 测试通过后再提交，提交信息可用 `test: ...`。

## 常见失败

| 现象 | 排查 |
|---|---|
| `ModuleNotFoundError: mfalpha` | 执行 `pip install -e .` |
| 预期值差 1 天 | 检查 `pct_change()` 与 `min_periods` |
| MACD 暖机期不符 | 暖机期是 `slow + signal - 2` |
| 财务对齐不符 | 检查是否按 `ann_date` 而非 `end_date` |