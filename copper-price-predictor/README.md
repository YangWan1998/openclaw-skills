# 铜价预测智能体 (Copper Price Predictor)

一个基于 AI 的铜价预测系统，通过分析新闻情绪、技术指标和宏观因子，生成铜价走势预测。

---

## 目录
- [功能需求 (Functional Requirements)](#功能需求-functional-requirements)
- [非功能需求 (Non-Functional Requirements)](#非功能需求-non-functional-requirements)
- [项目结构](#项目结构)
- [脚本说明](#脚本说明)
- [数据文件说明](#数据文件说明)
- [API 说明](#api-说明)
- [工作流程](#工作流程)
- [English Version](#english-version)

---

## 功能需求 (Functional Requirements)

### 1. 数据采集
- **FR-001**: 自动获取上海期货交易所铜主力合约实时价格
- **FR-002**: 自动获取美元指数、美国PMI、美联储政策等宏观数据
- **FR-003**: 自动搜索铜相关新闻（英文），覆盖价格、供需、库存、政策等维度

### 2. AI 分析
- **FR-004**: 使用 AI 对新闻进行情感分析（-1.0 到 +1.0 评分）
- **FR-005**: 使用 AI 对宏观因子进行评分（-10 到 +10 评分）
- **FR-006**: 基于时间权重计算加权平均情感得分

### 3. 预测生成
- **FR-007**: 综合舆情（40%）、技术（35%）、宏观（25%）生成预测
- **FR-008**: 生成 5天、1周、1个月三个时间窗口的预测
- **FR-009**: 输出预测方向（上涨/下跌/震荡）和目标价格

### 4. 报告输出
- **FR-010**: 生成每日预测报告（文本格式）
- **FR-011**: 保存预测历史，支持后续验证
- **FR-012**: 生成验证报告，计算方向准确率、MAE、RMSE

### 5. 学习闭环 (Learning Loop)
- **FR-013**: 自动记录每次验证结果到学习日志
- **FR-014**: 对错误预测进行 AI 归因分析（舆情/技术/宏观哪个因子导致偏差）
- **FR-015**: 基于历史错误统计生成权重调整建议
- **FR-016**: 记录权重变更历史（变更前→变更后、原因、批准人）
- **FR-017**: 支持自动/半自动权重调整（需满足错误率阈值和最小样本数）

---

## 非功能需求 (Non-Functional Requirements)

### 性能
- **NFR-001**: 单次完整运行时间 < 15 分钟（含 AI 分析）
- **NFR-002**: 新闻搜索响应时间 < 60 秒
- **NFR-003**: AI 情感分析单条 < 30 秒

### 可靠性
- **NFR-004**: 支持多数据源回退（akshare → Yahoo Finance → 模拟数据）
- **NFR-005**: 关键步骤失败时记录日志，不中断整体流程

### 可维护性
- **NFR-006**: 所有数据保存为 CSV 格式，便于查看和调试
- **NFR-007**: 配置文件独立（config/prediction_model.json），支持动态调整权重
- **NFR-010**: 学习日志和权重历史独立存储，支持复盘分析

### 扩展性
- **NFR-008**: 模块化设计，每个脚本独立运行
- **NFR-009**: 支持添加新的数据源或分析因子
- **NFR-011**: 权重调整规则可配置（调整幅度、阈值、最小样本数）

---

## 项目结构

```
copper-price-predictor/
├── config/
│   └── prediction_model.json          # 预测模型配置（权重、置信度）
├── data/                              # 数据目录（运行时生成）
│   ├── current_price.csv              # 当前铜价
│   ├── price_history.csv              # 历史价格
│   ├── latest_news.csv                # 最新新闻
│   ├── macro_data.csv                 # 宏观数据
│   ├── macro_ai_analysis.json         # AI宏观分析结果
│   ├── predictions.csv                # 预测历史
│   ├── latest_prediction.csv          # 最新预测
│   ├── learning_log.csv               # 学习日志（验证结果、错误归因）
│   ├── weight_history.csv             # 权重变更历史
│   └── validation/                    # 验证报告
├── reports/                           # 预测报告
│   └── YYYY-MM-DD_分析报告.txt
├── scripts/                           # 核心脚本
│   ├── run_mvp.py                     # MVP主运行脚本
│   ├── fetch_copper_price_v2.py       # 获取铜价
│   ├── fetch_macro_data.py            # 获取宏观数据
│   ├── search_copper_news.py          # 搜索新闻+AI情感分析
│   ├── analyze_and_predict.py         # 生成预测
│   ├── generate_report.py             # 生成报告
│   ├── validate_predictions.py        # 验证预测（含AI归因分析）
│   ├── learning_manager.py            # 学习日志管理（统计、建议生成）
│   ├── update_weights.py              # 权重调整工具
│   ├── analyze_sentiment_ai.py        # AI情感分析模块
│   ├── analyze_macro_ai.py            # AI宏观分析模块
│   ├── data_storage.py                # 数据存储工具
│   └── fetch_historical_prices.py     # 补齐历史数据
└── README.md                          # 本文件
```

---

## 脚本说明

### 1. run_mvp.py
**功能**: MVP 主运行脚本，串联整个流程

**调用链**:
```
run_mvp.py
├── fetch_copper_price_v2.py
├── fetch_macro_data.py
├── search_copper_news.py
├── analyze_and_predict.py
└── generate_report.py
```

**使用方法**:
```bash
python3 scripts/run_mvp.py
```

---

### 2. fetch_copper_price_v2.py
**功能**: 获取铜价数据

**数据源**:
- **akshare** (优先): 上海期货交易所铜主力连续合约(CU0)
- **Yahoo Finance** (备用): COMEX 铜期货(HG=F)

**API 说明**:
```python
import akshare as ak
# 获取期货主力连续数据
df = ak.futures_main_sina(symbol="CU0", start_date="20250601", end_date="20260702")
```

**输出文件**:
- `data/current_price.csv`: 当前价格
- `data/price_history.csv`: 历史价格（追加）

**字段说明**:
| 字段 | 说明 |
|------|------|
| date | 日期 |
| price | 收盘价 |
| change | 涨跌额 |
| change_percent | 涨跌幅 |
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| volume | 成交量 |
| hold | 持仓量 |

---

### 3. fetch_macro_data.py
**功能**: 获取宏观数据并进行 AI 分析

**数据源**:
- **美元指数**: Yahoo Finance (DX-Y.NYB)
- **美国 ISM PMI**: investing.com
- **LME 库存**: smm.cn
- **COMEX 库存**: smm.cn
- **美联储政策**: investing.com

**API 说明**:
```python
# 使用 web_fetch 获取网页数据
from skills import web_fetch
result = web_fetch(url="https://hk.finance.yahoo.com/quote/DX-Y.NYB")
```

**AI 分析**:
调用 `analyze_macro_ai.py` 中的 AI 对每个宏观因子评分

**输出文件**:
- `data/macro_data.csv`: 原始宏观数据
- `data/macro_ai_analysis.json`: AI 分析结果

---

### 4. search_copper_news.py
**功能**: 搜索铜相关新闻并进行 AI 情感分析

**搜索 API**:
```python
from search import search_tavily
# Tavily 搜索 API
result = search_tavily(
    query="copper price LME market news",
    max_results=3,
    search_depth="advanced"
)
```

**搜索查询词** (15个):
1. copper price LME COMEX market news
2. copper price analysis forecast today
3. LME copper price outlook commentary
4. copper supply demand deficit inventory
5. LME copper warehouse stock level
6. copper mine production strike Chile Peru
7. Fed interest rate decision copper impact
8. US dollar copper price correlation
9. China copper demand economy
10. electric vehicle copper demand EV
11. renewable energy copper consumption
12. AI data center copper usage
13. Goldman Sachs copper price forecast
14. Citi copper market outlook
15. Morgan Stanley copper analysis

**AI 情感分析**:
调用 `analyze_sentiment_ai.py` 中的 `batch_analyze_sentiment()`

**输出文件**:
- `data/latest_news.csv`: 新闻数据（含情感分析结果）

**字段说明**:
| 字段 | 说明 |
|------|------|
| date | 新闻日期 |
| title | 标题 |
| source | 来源 |
| url | 链接 |
| summary | 摘要 |
| score | Tavily 相关度分数 |
| sentiment | positive/negative/neutral |
| sentiment_score | -1.0 到 +1.0 |
| is_recent | 是否最近 |
| days_old | 距今天数 |
| time_weight | 时间权重（当天1.0，1周内0.8，1月内0.5） |

---

### 5. analyze_and_predict.py
**功能**: 综合分析并生成预测

**输入**:
- `data/current_price.csv`: 当前价格
- `data/latest_news.csv`: 新闻数据
- `data/macro_data.csv`: 宏观数据
- `config/prediction_model.json`: 权重配置

**预测模型**:
```
综合评分 = 舆情评分 × 40% + 技术指标 × 35% + 宏观因素 × 25%
```

**输出文件**:
- `data/predictions.csv`: 预测历史
- `data/latest_prediction.csv`: 最新预测

---

### 6. generate_report.py
**功能**: 生成每日预测报告

**输入**:
- 当前价格、宏观数据、新闻情感、预测结果

**输出**:
- `reports/YYYY-MM-DD_分析报告.txt`

---

### 7. validate_predictions.py
**功能**: 验证历史预测准确性，并进行AI错误归因分析

**验证指标**:
- 方向准确率（预测涨跌 vs 实际涨跌）
- MAE（平均绝对误差）
- RMSE（均方根误差）
- 置信度校准

**AI错误归因分析**:
- 对预测错误的记录，调用AI分析原因
- 识别导致偏差的主要因子（舆情/技术/宏观）
- 生成权重调整建议

**学习日志记录**:
- 自动保存验证结果到 `data/learning_log.csv`
- 记录预测方向、实际方向、错误归因、AI分析

**限制**:
- 需要等待预测时间窗口结束后才能验证
- 5天预测 → 5天后验证
- 1周预测 → 1周后验证
- 1月预测 → 1月后验证

---

### 12. learning_manager.py
**功能**: 学习日志管理核心模块

**主要功能**:
```python
# 追加学习日志
append_learning_log(record)

# 获取错误统计（按归因分类）
get_error_statistics(days=30)

# 生成本周错误归因统计报告
generate_weekly_summary()

# 生成权重调整建议（基于代码规则）
generate_weight_adjustment_suggestion()

# 记录权重变更历史
record_weight_change(old_weights, new_weights, reason, triggered_by)

# 更新权重配置
update_weights(new_weights, reason, triggered_by, approved_by)
```

**输出文件**:
- `data/learning_log.csv`: 学习日志
- `data/weight_history.csv`: 权重变更历史

---

### 13. update_weights.py
**功能**: 权重调整工具脚本

**使用方法**:
```bash
# 查看当前状态
python3 scripts/update_weights.py --status

# 仅生成建议（不修改）
python3 scripts/update_weights.py --suggest

# 查看权重调整历史
python3 scripts/update_weights.py --history

# 自动调整（需满足条件：错误率>阈值且样本足够）
python3 scripts/update_weights.py --auto

# 预览模式（不实际修改）
python3 scripts/update_weights.py --auto --dry-run
```

**自动调整条件**:
- 错误率阈值: 默认 60%
- 最小样本数: 默认 5条
- 短期(7天)和长期(30天)错误模式一致

**权重调整规则**:
- 舆情因子错误多 → 降低舆情权重 0.03，增加技术和宏观
- 技术因子错误多 → 降低技术权重 0.03，增加舆情和宏观
- 宏观因子错误多 → 降低宏观权重 0.03，增加舆情和技术

---

### 8. analyze_sentiment_ai.py
**功能**: AI 情感分析模块

**调用方式**:
```python
from analyze_sentiment_ai import analyze_sentiment_ai, batch_analyze_sentiment

# 单条分析
score = analyze_sentiment_ai(title, content)  # 返回 -1.0 到 +1.0

# 批量分析（最多15条）
results = batch_analyze_sentiment(news_list, max_batch_size=15)
```

**AI 调用**:
```bash
openclaw agent --agent main --message "分析prompt" --json --local --timeout 30
```

---

### 9. analyze_macro_ai.py
**功能**: AI 宏观分析模块

**调用方式**:
```python
from analyze_macro_ai import analyze_macro_factor

score = analyze_macro_factor(indicator, value, context)
# 返回 -10 到 +10 的整数
```

---

### 10. data_storage.py
**功能**: 数据存储工具函数

**主要函数**:
```python
save_csv(filename, records, fieldnames)      # 保存CSV
load_csv(filename)                            # 读取CSV
save_current_price(price_data)               # 保存当前价格
save_price_history(price_data)               # 保存价格历史
save_news_data(news_data)                    # 保存新闻
save_prediction(prediction)                  # 保存预测
save_validation_report(report, details)      # 保存验证报告
```

---

### 11. fetch_historical_prices.py
**功能**: 补齐历史铜价数据

**用途**:
- 首次运行时获取历史数据用于训练
- 补充 price_history.csv

---

## 数据文件说明

### current_price.csv
当前铜价快照，每次运行覆盖。

### price_history.csv
历史价格记录，追加模式。

### latest_news.csv
最新新闻及AI情感分析结果。

### macro_data.csv
宏观数据原始值。

### macro_ai_analysis.json
AI对宏观因子的分析结果:
```json
{
  "composite": {
    "composite_score": 2.9,
    "direction": "positive"
  },
  "factors": {
    "USD_INDEX": {"score": 3, "direction": "positive"},
    "US_ISM_PMI": {"score": 5, "direction": "positive"}
  }
}
```

### predictions.csv
预测历史记录，用于后续验证。

### latest_prediction.csv
最新预测结果。

### learning_log.csv
学习日志，记录每次验证的详细结果:
| 字段 | 说明 |
|------|------|
| date | 记录日期 |
| prediction_date | 预测日期 |
| period | 预测周期 |
| predicted_direction | 预测方向 |
| actual_direction | 实际方向 |
| direction_correct | 是否正确 |
| error_analysis | AI错误分析 |
| factor_attribution | 错误归因（舆情/技术/宏观） |
| weight_adjustment_suggestion | 权重调整建议 |

### weight_history.csv
权重变更历史:
| 字段 | 说明 |
|------|------|
| date | 变更日期 |
| old_sentiment_weight | 旧舆情权重 |
| new_sentiment_weight | 新舆情权重 |
| change_reason | 变更原因 |
| triggered_by | 触发条件 |
| approved_by | 批准人 |
| auto_adjusted | 是否自动调整 |

---

## API 说明

### 1. akshare (Python库)
**用途**: 获取国内期货数据
**安装**: `pip install akshare`
**主要函数**:
```python
ak.futures_main_sina(symbol="CU0", start_date, end_date)
```

### 2. Tavily Search API
**用途**: 搜索铜相关新闻
**来源**: moochmaniac-tavily-search skill
**调用**:
```python
from search import search_tavily
search_tavily(query, max_results=3, search_depth="advanced")
```

### 3. OpenClaw AI Agent
**用途**: AI 情感分析和宏观分析
**调用**:
```bash
openclaw agent --agent main --message "prompt" --json --local --timeout 30
```

### 4. web_fetch
**用途**: 获取网页内容（宏观数据）
**调用**:
```python
from skills import web_fetch
web_fetch(url="https://example.com")
```

---

## 工作流程

### 完整流程图

```
┌─────────────────┐
│   run_mvp.py    │
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬─────────────────┬──────────────┐
    ▼         ▼             ▼                 ▼              ▼
┌────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐
│fetch_  │ │fetch_    │ │search_       │ │analyze_and_ │ │generate_ │
│copper_ │ │macro_    │ │copper_       │ │predict.py   │ │report.py │
│price   │ │data.py   │ │news.py       │ │             │ │          │
└────┬───┘ └────┬─────┘ └──────┬───────┘ └──────┬──────┘ └────┬─────┘
     │          │              │                │             │
     ▼          ▼              ▼                ▼             ▼
┌────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐
│current_│ │macro_    │ │latest_       │ │predictions. │ │reports/  │
│price.  │ │data.csv  │ │news.csv      │ │csv          │ │YYYY-MM-  │
│csv     │ │macro_ai_ │ │              │ │latest_pred  │ │DD_分析   │
│price_  │ │analysis. │ │              │ │iction.csv   │ │报告.txt  │
│history.│ │json      │ │              │ │             │ │          │
│csv     │ │          │ │              │ │             │ │          │
└────────┘ └──────────┘ └──────────────┘ └─────────────┘ └──────────┘
```

### 数据流

```
价格数据 ──┐
           ├──→ analyze_and_predict.py ──→ predictions.csv
新闻数据 ──┤      ↑
           │      └──── config/prediction_model.json (权重配置)
宏观数据 ──┘
```

### 验证与学习闭环流程

```
┌─────────────────────────────────────────────────────────────┐
│                     学习闭环 (Learning Loop)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  predictions.csv ──┐                                        │
│                    ├──→ validate_predictions.py              │
│  price_history.csv─┘         │                              │
│                              ▼                              │
│                    ┌─────────────────┐                      │
│                    │ 1. 计算准确率    │                      │
│                    │ 2. AI错误归因    │                      │
│                    │ 3. 保存学习日志  │──→ learning_log.csv  │
│                    └────────┬────────┘                      │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │ 生成权重建议     │                      │
│                    │ (代码规则-based) │                      │
│                    └────────┬────────┘                      │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │ 通知用户确认     │                      │
│                    │ 等待人工批准     │                      │
│                    └────────┬────────┘                      │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │ update_weights.py│                     │
│                    │ --auto / --suggest│                    │
│                    └────────┬────────┘                      │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │ 更新配置文件     │──→ weight_history.csv│
│                    │ prediction_model │                     │
│                    └─────────────────┘                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 配置说明

### prediction_model.json

```json
{
  "scoring_weights": {
    "sentiment": {"weight": 0.40, "description": "舆情情绪"},
    "technical": {"weight": 0.35, "description": "技术指标"},
    "macro": {"weight": 0.25, "description": "宏观因子"}
  },
  "confidence_levels": {
    "5_days": {"default": 0.6},
    "1_week": {"default": 0.5},
    "1_month": {"default": 0.4}
  }
}
```

---

## 使用说明

### 首次运行
```bash
# 1. 补齐历史数据
python3 scripts/fetch_historical_prices.py

# 2. 运行完整MVP流程
python3 scripts/run_mvp.py
```

### 日常运行
```bash
# 运行完整流程
python3 scripts/run_mvp.py
```

### 单独运行某步骤
```bash
# 只获取价格
python3 scripts/fetch_copper_price_v2.py

# 只搜索新闻
python3 scripts/search_copper_news.py

# 只生成预测（需先运行前面步骤）
python3 scripts/analyze_and_predict.py
```

### 验证预测
```bash
# 需要积累足够数据后运行
python3 scripts/validate_predictions.py
```

### 查看学习日志和权重建议
```bash
# 查看当前状态
python3 scripts/update_weights.py --status

# 生成权重调整建议（不修改）
python3 scripts/update_weights.py --suggest

# 查看权重变更历史
python3 scripts/update_weights.py --history

# 自动调整权重（需满足条件）
python3 scripts/update_weights.py --auto

# 预览自动调整（不实际修改）
python3 scripts/update_weights.py --auto --dry-run
```

---

## 注意事项

1. **API 限制**: Tavily 搜索和 OpenClaw AI 有调用频率限制
2. **运行时间**: 完整流程约 10-15 分钟（主要在 AI 分析）
3. **验证延迟**: 预测需要等待时间窗口结束后才能验证
4. **数据质量**: 新闻搜索使用英文查询，确保网络可访问国际网站
5. **学习闭环**: 权重调整建议基于代码规则，AI仅用于错误归因分析
6. **自动调整**: 默认不自动应用权重调整，需人工确认后执行

---

# English Version

# Copper Price Predictor

An AI-based copper price prediction system that generates price forecasts by analyzing news sentiment, technical indicators, and macro factors.

---

## Functional Requirements

### 1. Data Collection
- **FR-001**: Automatically fetch real-time copper prices from Shanghai Futures Exchange
- **FR-002**: Automatically fetch macro data (USD index, US PMI, Fed policy)
- **FR-003**: Automatically search copper-related news (English), covering price, supply/demand, inventory, policy

### 2. AI Analysis
- **FR-004**: Use AI for news sentiment analysis (-1.0 to +1.0 scoring)
- **FR-005**: Use AI for macro factor scoring (-10 to +10)
- **FR-006**: Calculate time-weighted average sentiment score

### 3. Prediction Generation
- **FR-007**: Generate predictions based on sentiment (40%), technical (35%), macro (25%)
- **FR-008**: Generate predictions for 5-day, 1-week, 1-month windows
- **FR-009**: Output direction (up/down/stable) and target prices

### 4. Reporting
- **FR-010**: Generate daily prediction reports (text format)
- **FR-011**: Save prediction history for future validation
- **FR-012**: Generate validation reports with accuracy metrics

### 5. Learning Loop
- **FR-013**: Automatically record validation results to learning log
- **FR-014**: AI error attribution analysis (sentiment/technical/macro factor identification)
- **FR-015**: Generate weight adjustment suggestions based on historical error statistics
- **FR-016**: Record weight change history (before→after, reason, approver)
- **FR-017**: Support automatic/semi-automatic weight adjustment (requires error rate threshold and minimum samples)

---

## Non-Functional Requirements

### Performance
- **NFR-001**: Complete run time < 15 minutes (including AI analysis)
- **NFR-002**: News search response time < 60 seconds
- **NFR-003**: AI sentiment analysis per item < 30 seconds

### Reliability
- **NFR-004**: Multi-source fallback (akshare → Yahoo Finance → mock data)
- **NFR-005**: Log errors without interrupting overall workflow

### Maintainability
- **NFR-006**: All data saved as CSV for easy inspection
- **NFR-007**: Independent config file (config/prediction_model.json)
- **NFR-010**: Learning log and weight history stored separately for review

### Extensibility
- **NFR-008**: Modular design, each script runs independently
- **NFR-009**: Support adding new data sources or analysis factors
- **NFR-011**: Weight adjustment rules configurable (adjustment magnitude, threshold, minimum samples)

---

## Project Structure

```
copper-price-predictor/
├── config/
│   └── prediction_model.json          # Prediction model config
├── data/                              # Data directory (generated at runtime)
│   ├── current_price.csv              # Current copper price
│   ├── price_history.csv              # Price history
│   ├── latest_news.csv                # Latest news
│   ├── macro_data.csv                 # Macro data
│   ├── macro_ai_analysis.json         # AI macro analysis results
│   ├── predictions.csv                # Prediction history
│   ├── latest_prediction.csv          # Latest prediction
│   ├── learning_log.csv               # Learning log (validation results, error attribution)
│   ├── weight_history.csv             # Weight change history
│   └── validation/                    # Validation reports
├── reports/                           # Prediction reports
│   └── YYYY-MM-DD_Analysis_Report.txt
├── scripts/                           # Core scripts
│   ├── run_mvp.py                     # MVP main script
│   ├── fetch_copper_price_v2.py       # Fetch copper price
│   ├── fetch_macro_data.py            # Fetch macro data
│   ├── search_copper_news.py          # Search news + AI sentiment
│   ├── analyze_and_predict.py         # Generate predictions
│   ├── generate_report.py             # Generate reports
│   ├── validate_predictions.py        # Validate predictions (with AI attribution)
│   ├── learning_manager.py            # Learning log management (statistics, suggestions)
│   ├── update_weights.py              # Weight adjustment tool
│   ├── analyze_sentiment_ai.py        # AI sentiment module
│   ├── analyze_macro_ai.py            # AI macro module
│   ├── data_storage.py                # Data storage utilities
│   └── fetch_historical_prices.py     # Fetch historical data
└── README.md
```

---

## Script Descriptions

### 1. run_mvp.py
**Purpose**: MVP main script, orchestrates the entire workflow

**Call Chain**:
```
run_mvp.py
├── fetch_copper_price_v2.py
├── fetch_macro_data.py
├── search_copper_news.py
├── analyze_and_predict.py
└── generate_report.py
```

**Usage**:
```bash
python3 scripts/run_mvp.py
```

---

### 2. fetch_copper_price_v2.py
**Purpose**: Fetch copper price data

**Data Sources**:
- **akshare** (primary): SHFE Copper Main Contract (CU0)
- **Yahoo Finance** (fallback): COMEX Copper (HG=F)

**API**:
```python
import akshare as ak
df = ak.futures_main_sina(symbol="CU0", start_date="20250601", end_date="20260702")
```

**Output**:
- `data/current_price.csv`: Current price
- `data/price_history.csv`: Price history (append mode)

---

### 3. fetch_macro_data.py
**Purpose**: Fetch macro data and perform AI analysis

**Data Sources**:
- **USD Index**: Yahoo Finance (DX-Y.NYB)
- **US ISM PMI**: investing.com
- **LME Inventory**: smm.cn
- **COMEX Inventory**: smm.cn
- **Fed Policy**: investing.com

**AI Analysis**:
Calls `analyze_macro_ai.py` to score each macro factor

**Output**:
- `data/macro_data.csv`: Raw macro data
- `data/macro_ai_analysis.json`: AI analysis results

---

### 4. search_copper_news.py
**Purpose**: Search copper-related news and perform AI sentiment analysis

**Search API**:
```python
from search import search_tavily
result = search_tavily(
    query="copper price LME market news",
    max_results=3,
    search_depth="advanced"
)
```

**Search Queries** (15 total):
1. copper price LME COMEX market news
2. copper price analysis forecast today
3. LME copper price outlook commentary
4. copper supply demand deficit inventory
5. LME copper warehouse stock level
6. copper mine production strike Chile Peru
7. Fed interest rate decision copper impact
8. US dollar copper price correlation
9. China copper demand economy
10. electric vehicle copper demand EV
11. renewable energy copper consumption
12. AI data center copper usage
13. Goldman Sachs copper price forecast
14. Citi copper market outlook
15. Morgan Stanley copper analysis

**AI Sentiment Analysis**:
Calls `analyze_sentiment_ai.py` `batch_analyze_sentiment()`

**Output**:
- `data/latest_news.csv`: News data with sentiment analysis

---

### 5. analyze_and_predict.py
**Purpose**: Comprehensive analysis and prediction generation

**Inputs**:
- `data/current_price.csv`: Current price
- `data/latest_news.csv`: News data
- `data/macro_data.csv`: Macro data
- `config/prediction_model.json`: Weight configuration

**Prediction Model**:
```
Composite Score = Sentiment × 40% + Technical × 35% + Macro × 25%
```

**Output**:
- `data/predictions.csv`: Prediction history
- `data/latest_prediction.csv`: Latest prediction

---

### 6. generate_report.py
**Purpose**: Generate daily prediction reports

**Output**:
- `reports/YYYY-MM-DD_Analysis_Report.txt`

---

### 7. validate_predictions.py
**Purpose**: Validate historical prediction accuracy and perform AI error attribution analysis

**Metrics**:
- Direction accuracy (predicted vs actual)
- MAE (Mean Absolute Error)
- RMSE (Root Mean Square Error)
- Confidence calibration

**AI Error Attribution**:
- For incorrect predictions, call AI to analyze the cause
- Identify the main factor causing deviation (sentiment/technical/macro)
- Generate weight adjustment suggestions

**Learning Log**:
- Automatically save validation results to `data/learning_log.csv`
- Record predicted direction, actual direction, error attribution, AI analysis

**Limitation**:
- Must wait for prediction time window to end before validation
- 5-day prediction → validate after 5 days
- 1-week prediction → validate after 1 week
- 1-month prediction → validate after 1 month

---

### 12. learning_manager.py
**Purpose**: Learning log management core module

**Main Functions**:
```python
# Append learning log
append_learning_log(record)

# Get error statistics (by attribution)
get_error_statistics(days=30)

# Generate weekly error attribution report
generate_weekly_summary()

# Generate weight adjustment suggestion (code rule-based)
generate_weight_adjustment_suggestion()

# Record weight change history
record_weight_change(old_weights, new_weights, reason, triggered_by)

# Update weight configuration
update_weights(new_weights, reason, triggered_by, approved_by)
```

**Output Files**:
- `data/learning_log.csv`: Learning log
- `data/weight_history.csv`: Weight change history

---

### 13. update_weights.py
**Purpose**: Weight adjustment tool script

**Usage**:
```bash
# View current status
python3 scripts/update_weights.py --status

# Generate suggestion only (no modification)
python3 scripts/update_weights.py --suggest

# View weight change history
python3 scripts/update_weights.py --history

# Auto-adjust (requires conditions: error rate > threshold and sufficient samples)
python3 scripts/update_weights.py --auto

# Preview mode (no actual modification)
python3 scripts/update_weights.py --auto --dry-run
```

**Auto-Adjustment Conditions**:
- Error rate threshold: default 60%
- Minimum samples: default 5
- Short-term (7-day) and long-term (30-day) error patterns consistent

**Weight Adjustment Rules**:
- Sentiment factor errors → Decrease sentiment weight by 0.03, increase technical and macro
- Technical factor errors → Decrease technical weight by 0.03, increase sentiment and macro
- Macro factor errors → Decrease macro weight by 0.03, increase sentiment and technical

---

### 8. analyze_sentiment_ai.py
**Purpose**: AI sentiment analysis module

**Usage**:
```python
from analyze_sentiment_ai import analyze_sentiment_ai, batch_analyze_sentiment

# Single analysis
score = analyze_sentiment_ai(title, content)  # Returns -1.0 to +1.0

# Batch analysis (max 15 items)
results = batch_analyze_sentiment(news_list, max_batch_size=15)
```

**AI Call**:
```bash
openclaw agent --agent main --message "analysis prompt" --json --local --timeout 30
```

---

### 9. analyze_macro_ai.py
**Purpose**: AI macro analysis module

**Usage**:
```python
from analyze_macro_ai import analyze_macro_factor
score = analyze_macro_factor(indicator, value, context)
# Returns integer -10 to +10
```

---

### 10. data_storage.py
**Purpose**: Data storage utility functions

**Main Functions**:
```python
save_csv(filename, records, fieldnames)      # Save CSV
load_csv(filename)                            # Load CSV
save_current_price(price_data)               # Save current price
save_price_history(price_data)               # Save price history
save_news_data(news_data)                    # Save news
save_prediction(prediction)                  # Save prediction
save_validation_report(report, details)      # Save validation report
```

---

### 11. fetch_historical_prices.py
**Purpose**: Fetch historical copper price data

**Usage**:
- Initial setup to get historical data for training
- Supplement price_history.csv

---

## Data Files

### current_price.csv
Current copper price snapshot, overwritten each run.

### price_history.csv
Historical price records, append mode.

### latest_news.csv
Latest news with AI sentiment analysis results.

### macro_data.csv
Raw macro data values.

### macro_ai_analysis.json
AI analysis results for macro factors.

### predictions.csv
Prediction history for future validation.

### latest_prediction.csv
Latest prediction results.

### learning_log.csv
Learning log, recording detailed validation results:
| Field | Description |
|-------|-------------|
| date | Record date |
| prediction_date | Prediction date |
| period | Prediction period |
| predicted_direction | Predicted direction |
| actual_direction | Actual direction |
| direction_correct | Is correct |
| error_analysis | AI error analysis |
| factor_attribution | Error attribution (sentiment/technical/macro) |
| weight_adjustment_suggestion | Weight adjustment suggestion |

### weight_history.csv
Weight change history:
| Field | Description |
|-------|-------------|
| date | Change date |
| old_sentiment_weight | Old sentiment weight |
| new_sentiment_weight | New sentiment weight |
| change_reason | Change reason |
| triggered_by | Trigger condition |
| approved_by | Approver |
| auto_adjusted | Is auto-adjusted |

---

## API Descriptions

### 1. akshare (Python Library)
**Purpose**: Fetch domestic futures data
**Install**: `pip install akshare`
**Main Function**:
```python
ak.futures_main_sina(symbol="CU0", start_date, end_date)
```

### 2. Tavily Search API
**Purpose**: Search copper-related news
**Source**: moochmaniac-tavily-search skill
**Usage**:
```python
from search import search_tavily
search_tavily(query, max_results=3, search_depth="advanced")
```

### 3. OpenClaw AI Agent
**Purpose**: AI sentiment and macro analysis
**Usage**:
```bash
openclaw agent --agent main --message "prompt" --json --local --timeout 30
```

### 4. web_fetch
**Purpose**: Fetch web page content (macro data)
**Usage**:
```python
from skills import web_fetch
web_fetch(url="https://example.com")
```

---

## Workflow

### Complete Flow

```
┌─────────────────┐
│   run_mvp.py    │
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬─────────────────┬──────────────┐
    ▼         ▼             ▼                 ▼              ▼
┌────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐
│fetch_  │ │fetch_    │ │search_       │ │analyze_and_ │ │generate_ │
│copper_ │ │macro_    │ │copper_       │ │predict.py   │ │report.py │
│price   │ │data.py   │ │news.py       │ │             │ │          │
└────┬───┘ └────┬─────┘ └──────┬───────┘ └──────┬──────┘ └────┬─────┘
     │          │              │                │             │
     ▼          ▼              ▼                ▼             ▼
┌────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐
│current_│ │macro_    │ │latest_       │ │predictions. │ │reports/  │
│price.  │ │data.csv  │ │news.csv      │ │csv          │ │YYYY-MM-  │
│csv     │ │macro_ai_ │ │              │ │latest_pred  │ │DD_分析   │
│price_  │ │analysis. │ │              │ │iction.csv   │ │报告.txt  │
│history.│ │json      │ │              │ │             │ │          │
│csv     │ │          │ │              │ │             │ │          │
└────────┘ └──────────┘ └──────────────┘ └─────────────┘ └──────────┘
```

### Data Flow

```
Price Data ──┐
             ├──→ analyze_and_predict.py ──→ predictions.csv
News Data ───┤      ↑
             │      └──── config/prediction_model.json (weights)
Macro Data ──┘
```

### Validation & Learning Loop Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Learning Loop                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  predictions.csv ──┐                                        │
│                    ├──→ validate_predictions.py              │
│  price_history.csv─┘         │                              │
│                              ▼                              │
│                    ┌─────────────────┐                      │
│                    │ 1. Calculate accuracy                  │
│                    │ 2. AI error attribution                │
│                    │ 3. Save learning log  │──→ learning_log.csv │
│                    └────────┬────────┘                      │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │ Generate weight suggestion              │
│                    │ (code rule-based)                      │
│                    └────────┬────────┘                      │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │ Notify user for confirmation            │
│                    │ Wait for manual approval                │
│                    └────────┬────────┘                      │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │ update_weights.py│                     │
│                    │ --auto / --suggest│                    │
│                    └────────┬────────┘                      │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │ Update config    │──→ weight_history.csv│
│                    │ prediction_model │                     │
│                    └─────────────────┘                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### prediction_model.json

```json
{
  "scoring_weights": {
    "sentiment": {"weight": 0.40, "description": "Sentiment"},
    "technical": {"weight": 0.35, "description": "Technical"},
    "macro": {"weight": 0.25, "description": "Macro"}
  },
  "confidence_levels": {
    "5_days": {"default": 0.6},
    "1_week": {"default": 0.5},
    "1_month": {"default": 0.4}
  }
}
```

---

## Usage

### First Run
```bash
# 1. Fetch historical data
python3 scripts/fetch_historical_prices.py

# 2. Run complete MVP workflow
python3 scripts/run_mvp.py
```

### Daily Run
```bash
# Run complete workflow
python3 scripts/run_mvp.py
```

### Run Individual Steps
```bash
# Only fetch price
python3 scripts/fetch_copper_price_v2.py

# Only search news
python3 scripts/search_copper_news.py

# Only generate prediction (requires previous steps)
python3 scripts/analyze_and_predict.py
```

### Validate Predictions
```bash
# Run after accumulating sufficient data
python3 scripts/validate_predictions.py
```

### View Learning Log and Weight Suggestions
```bash
# View current status
python3 scripts/update_weights.py --status

# Generate weight adjustment suggestion (no modification)
python3 scripts/update_weights.py --suggest

# View weight change history
python3 scripts/update_weights.py --history

# Auto-adjust weights (requires conditions)
python3 scripts/update_weights.py --auto

# Preview auto-adjustment (no actual modification)
python3 scripts/update_weights.py --auto --dry-run
```

---

## Notes

1. **API Limits**: Tavily search and OpenClaw AI have rate limits
2. **Runtime**: Full workflow takes ~10-15 minutes (mainly AI analysis)
3. **Validation Delay**: Predictions can only be validated after time window ends
4. **Data Quality**: News search uses English queries, ensure network access to international sites
5. **Learning Loop**: Weight adjustment suggestions are code rule-based, AI is only used for error attribution analysis
6. **Auto-Adjustment**: Weight adjustment is not applied automatically by default, requires manual confirmation
