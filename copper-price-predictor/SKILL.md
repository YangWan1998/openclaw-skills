---
name: copper-price-predictor
description: "铜价预测智能体 - 每日监控铜价，基于新闻和市场分析进行预测，并通过自我学习持续改进预测准确度。"
metadata:
  { "openclaw": { "emoji": "🏭" } }
---

# 铜价预测智能体

## 功能概述

1. **每日数据收集**
   - 获取实时铜价数据（Yahoo Finance API）
   - 搜索铜相关新闻和市场分析（Tavily Search）
   - 收集宏观经济指标

2. **价格预测**
   - 基于新闻情绪分析预测未来走势
   - 生成3个时间段的预测：5天、1周、1个月
   - 输出预测置信度

3. **预测验证**
   - 每日对比预测与实际价格
   - 分析预测正确/错误的原因
   - 记录到学习日志

4. **自我学习**
   - 定期回顾历史预测记录
   - 总结成功和失败的模式
   - 更新预测策略

## 目录结构

```
copper-price-predictor/
├── SKILL.md                 # 本文件
├── scripts/
│   ├── fetch_copper_price.py    # 获取铜价数据
│   ├── search_copper_news.py    # 搜索铜相关新闻
│   ├── analyze_and_predict.py   # 分析并生成预测
│   ├── validate_predictions.py  # 验证历史预测
│   └── generate_report.py       # 生成报告
└── data/
    ├── predictions.json       # 预测记录
    ├── actual_prices.json     # 实际价格记录
    └── learning_log.json      # 学习日志
```

## 使用方法

### 手动运行

```bash
# 1. 获取当前铜价
python3 scripts/fetch_copper_price.py

# 2. 搜索相关新闻
python3 scripts/search_copper_news.py

# 3. 生成预测
python3 scripts/analyze_and_predict.py

# 4. 验证历史预测
python3 scripts/validate_predictions.py

# 5. 生成完整报告
python3 scripts/generate_report.py
```

### 自动运行（Cron）

使用 OpenClaw 的 cron 功能设置每日定时任务。

## 数据来源

- **铜价数据**: Yahoo Finance (HG=F - 铜期货)
- **新闻搜索**: Tavily Search API
- **宏观经济**: 美联储政策、中国制造业PMI、美元汇率等

## 预测模型

当前版本使用基于规则的预测模型：
1. 新闻情绪评分 (-1 到 +1)
2. 技术指标分析（趋势、支撑/阻力位）
3. 宏观经济因素权重

未来可升级为机器学习模型。

## 学习机制

### 第一步：记录与分析（已实现）
1. 每次预测后记录详细上下文
2. 每日验证时分析偏差原因
3. **保存到结构化学习日志** (`data/learning_log.csv`)
4. **生成权重调整建议**（需人工确认后应用）

### 第二步：闭环优化（待确认后启用）
5. 自动/半自动调整权重 (`scripts/update_weights.py`)
6. **记录权重变更历史** (`data/weight_history.csv`)
7. 每月生成策略更新报告

### 权重调整流程

```bash
# 查看当前状态和建议
python3 scripts/update_weights.py --status
python3 scripts/update_weights.py --suggest

# 查看权重调整历史
python3 scripts/update_weights.py --history

# 自动调整（需满足条件：错误率>阈值且样本足够）
python3 scripts/update_weights.py --auto

# 预览自动调整（不实际修改）
python3 scripts/update_weights.py --auto --dry-run
```

### 数据文件

| 文件 | 用途 |
|------|------|
| `data/learning_log.csv` | 预测验证结果、错误归因、AI分析 |
| `data/weight_history.csv` | 权重变更历史、原因、批准人 |
| `config/prediction_model.json` | 当前权重配置（含调整历史） |
