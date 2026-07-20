---
name: copper-price-predictor
description: "铜价预测智能体 - 每日监控铜价，基于新闻和市场分析进行预测，并通过自我学习持续改进预测准确度。"
metadata:
  { "openclaw": { "emoji": "🏭" } }
---

# 铜价预测智能体

> 📋 **项目上下文**: 查看 `PROJECT_CONTEXT.md` 了解项目演进、当前状态、已知问题和待办事项。
> 本文件聚焦功能说明，项目全景信息在 PROJECT_CONTEXT.md 中维护。

## 功能概述

1. **每日数据收集**
   - 获取实时铜价数据（上海期货交易所 via akshare）
   - 搜索铜相关新闻和市场分析（网络搜索 + AI情感分析）
   - 收集宏观经济指标（美元指数、PMI、库存、美联储政策）

2. **价格预测**
   - 基于三因子加权模型预测未来走势
   - 生成3个时间段的预测：5天、1周、1个月
   - 输出预测置信度

3. **预测验证**
   - 每日对比预测与实际价格
   - 分析预测正确/错误的原因（舆情/技术/宏观归因）
   - 记录到结构化学习日志

4. **自我学习**
   - 定期回顾历史预测记录
   - 生成权重调整建议
   - **人工确认后**应用权重调整（记录完整变更历史）

## 目录结构

```
copper-price-predictor/
├── SKILL.md                    # 本文件（功能说明）
├── PROJECT_CONTEXT.md          # 项目上下文（演进、状态、待办）⚠️ 修改前必读
├── config/
│   └── prediction_model.json   # 当前权重配置
├── scripts/
│   ├── run_mvp.py              # 主运行脚本（编排全流程）
│   ├── fetch_copper_price_v2.py   # 获取铜价（akshare→上期所）
│   ├── fetch_macro_data.py     # 获取宏观数据 + AI分析
│   ├── search_copper_news.py   # 搜索新闻 + AI情感分析
│   ├── analyze_and_predict.py  # 三因子加权预测
│   ├── generate_report.py      # 生成日报
│   ├── validate_predictions.py # 验证历史预测
│   ├── learning_manager.py     # 学习日志管理
│   ├── update_weights.py       # 权重调整工具
│   └── cleanup_old_data.py     # 数据清理
├── data/
│   ├── price_history.csv       # 铜价历史
│   ├── predictions.csv         # 预测记录
│   ├── learning_log.csv        # 验证+归因记录
│   ├── weight_history.csv      # 权重变更历史
│   ├── latest_news.csv         # 新闻数据
│   ├── macro_data.csv          # 宏观数据
│   ├── news_analysis.json      # 新闻AI分析结果
│   ├── macro_ai_analysis.json  # 宏观AI分析结果
│   └── validation/             # 验证报告目录
└── reports/                    # 日报输出目录
```

## 使用方法

### 一键运行完整流程

```bash
cd /Users/yang/.openclaw/workspace/skills/copper-price-predictor
python3 scripts/run_mvp.py
```

### 分步运行

```bash
# 1. 获取铜价数据
python3 scripts/fetch_copper_price_v2.py

# 2. 获取宏观数据
python3 scripts/fetch_macro_data.py

# 3. 搜索相关新闻
python3 scripts/search_copper_news.py

# 4. 生成预测
python3 scripts/analyze_and_predict.py

# 5. 生成报告
python3 scripts/generate_report.py

# 6. 验证历史预测
python3 scripts/validate_predictions.py
```

### 权重管理

```bash
# 查看当前状态和建议
python3 scripts/update_weights.py --status
python3 scripts/update_weights.py --suggest

# 查看权重调整历史
python3 scripts/update_weights.py --history

# 预览自动调整（不实际修改）
python3 scripts/update_weights.py --auto --dry-run

# 应用自动调整（需满足条件：错误率>阈值且样本足够）
python3 scripts/update_weights.py --auto
```

### 自动运行（Cron）

使用 OpenClaw 的 cron 功能设置每日定时任务：

| 任务 | 时间 | 说明 |
|------|------|------|
| 铜价新闻搜索 | 8:30 工作日 | 预存新闻数据，避免日报时搜索超时 |
| 铜价预测日报 | 9:00 工作日 | 生成完整预测报告 |
| 铜价数据清理 | 周日 2:00 | 清理旧数据文件 |

## 数据来源

- **铜价数据**: 上海期货交易所（akshare库，CU0主力连续合约）
- **新闻搜索**: 网络搜索 + AI批量情感分析
- **宏观经济**: 美元指数、美国ISM制造业PMI、LME/COMEX库存、美联储政策立场

## 预测模型

### 三因子加权模型

```
综合评分 = 舆情评分 × 权重 + 技术指标 × 权重 + 宏观因子 × 权重
```

| 因子 | 当前权重 | 说明 |
|------|----------|------|
| 舆情 | 0.50 | 新闻情感分析（-10到+10） |
| 技术 | 0.00 | 5日/10日均线、RSI、成交量（当前禁用） |
| 宏观 | 0.50 | 美元/PMI/库存/政策综合得分 |

### 时间窗口置信度

| 窗口 | 置信度 |
|------|--------|
| 5天 | 60% |
| 1周 | 50% |
| 1月 | 40% |

> ⚠️ 权重配置存储在 `config/prediction_model.json`，调整前请查看 PROJECT_CONTEXT.md 中的决策记录。

## 学习机制

### 第一步：记录与分析（已实现）

1. 每次预测后记录详细上下文
2. 每日验证时分析偏差原因
3. 保存到结构化学习日志 (`data/learning_log.csv`)
4. 生成权重调整建议（**需人工确认后应用**）

### 第二步：闭环优化（待确认后启用）

5. 满足条件时自动调整权重 (`scripts/update_weights.py --auto`)
6. 记录权重变更历史 (`data/weight_history.csv`)
7. 每月生成策略更新报告

> ⚠️ **重要**: 当前策略是"建议+人工确认"，不要擅自自动应用权重调整。启用第二步需万洋大魔王明确同意。

## 关键数据文件

| 文件 | 用途 | 更新频率 |
|------|------|----------|
| `data/price_history.csv` | 铜价历史 | 每日 |
| `data/predictions.csv` | 预测记录 | 每日 |
| `data/learning_log.csv` | 验证结果、错误归因、AI分析 | 每日 |
| `data/weight_history.csv` | 权重变更历史、原因、批准人 | 调权时 |
| `config/prediction_model.json` | 当前权重配置 | 调权时 |

## 注意事项

1. **修改前必读 PROJECT_CONTEXT.md** - 了解当前状态、已知问题和待办事项
2. **权重调整需确认** - 不要自动应用，需万洋大魔王同意
3. **数据源变更需记录** - 任何数据源调整更新到 PROJECT_CONTEXT.md
4. **cron故障排查** - 如遇网络错误，先手动运行 `run_mvp.py` 验证脚本本身正常
