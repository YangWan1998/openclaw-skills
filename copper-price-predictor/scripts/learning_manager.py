#!/usr/bin/env python3
"""
学习日志管理模块 - 记录预测验证结果、错误归因和权重调整历史
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path


def get_data_dir():
    """获取数据目录"""
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_config_dir():
    """获取配置目录"""
    config_dir = Path(__file__).parent.parent / 'config'
    config_dir.mkdir(exist_ok=True)
    return config_dir


# ==================== 学习日志 ====================

LEARNING_LOG_FIELDS = [
    'date', 'prediction_date', 'period', 'predicted_direction', 'actual_direction',
    'direction_correct', 'predicted_price', 'actual_price', 'price_error',
    'sentiment_score', 'technical_score', 'macro_score', 'composite_score',
    'error_analysis', 'factor_attribution', 'weight_adjustment_suggestion',
    'validated', 'validation_date'
]


def append_learning_log(record):
    """
    追加学习日志记录
    
    Args:
        record: 学习记录字典
    
    Returns:
        文件路径
    """
    data_dir = get_data_dir()
    filepath = data_dir / 'learning_log.csv'
    
    # 确保记录包含所有字段
    full_record = {field: record.get(field, '') for field in LEARNING_LOG_FIELDS}
    full_record['validation_date'] = datetime.now().strftime('%Y-%m-%d')
    
    file_exists = filepath.exists()
    
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=LEARNING_LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(full_record)
    
    return filepath


def load_learning_log(days=None):
    """
    加载学习日志
    
    Args:
        days: 可选，加载最近N天的记录
    
    Returns:
        记录列表
    """
    data_dir = get_data_dir()
    filepath = data_dir / 'learning_log.csv'
    
    records = []
    if not filepath.exists():
        return records
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        records = [r for r in records if r.get('validation_date', '') >= cutoff]
    
    return records


def get_error_statistics(days=30):
    """
    获取错误归因统计
    
    Args:
        days: 统计最近N天
    
    Returns:
        dict: 统计结果
    """
    records = load_learning_log(days=days)
    
    if not records:
        return {
            'total_validated': 0,
            'total_errors': 0,
            'error_rate': 0,
            'attribution_counts': {},
            'period': days
        }
    
    # 只统计已验证的记录
    validated = [r for r in records if r.get('validated') == 'True' or r.get('validated') == 'true']
    errors = [r for r in validated if r.get('direction_correct') == 'False' or r.get('direction_correct') == 'false']
    
    # 归因统计
    attribution_counts = {}
    for record in errors:
        attr = record.get('factor_attribution', '未知')
        attribution_counts[attr] = attribution_counts.get(attr, 0) + 1
    
    return {
        'total_validated': len(validated),
        'total_errors': len(errors),
        'error_rate': round(len(errors) / len(validated), 4) if validated else 0,
        'attribution_counts': attribution_counts,
        'period': days
    }


def generate_weekly_summary():
    """
    生成本周错误归因统计报告
    
    Returns:
        str: 报告文本
    """
    stats = get_error_statistics(days=7)
    
    if stats['total_validated'] == 0:
        return "本周暂无验证记录"
    
    report = f"""📊 本周错误归因统计 ({datetime.now().strftime('%Y-%m-%d')})

验证记录: {stats['total_validated']} 条
错误次数: {stats['total_errors']} 次
错误率: {stats['error_rate']*100:.1f}%

错误归因分布:
"""
    
    for attr, count in sorted(stats['attribution_counts'].items(), key=lambda x: -x[1]):
        percentage = (count / stats['total_errors'] * 100) if stats['total_errors'] > 0 else 0
        report += f"  • {attr}: {count}次 ({percentage:.0f}%)\n"
    
    # 找出主要问题因子
    if stats['attribution_counts']:
        main_factor = max(stats['attribution_counts'], key=stats['attribution_counts'].get)
        report += f"\n⚠️ 主要问题因子: {main_factor}\n"
        
        # 给出权重调整建议
        if main_factor == '舆情因子':
            report += "💡 建议: 考虑降低舆情权重 0.02-0.05，增加技术或宏观权重\n"
        elif main_factor == '技术因子':
            report += "💡 建议: 考虑降低技术权重 0.02-0.05，增加舆情或宏观权重\n"
        elif main_factor == '宏观因子':
            report += "💡 建议: 考虑降低宏观权重 0.02-0.05，增加舆情或技术权重\n"
    
    return report


# ==================== 权重调整历史 ====================

WEIGHT_HISTORY_FIELDS = [
    'date', 'old_sentiment_weight', 'old_technical_weight', 'old_macro_weight',
    'new_sentiment_weight', 'new_technical_weight', 'new_macro_weight',
    'change_reason', 'triggered_by', 'error_statistics_before',
    'approved_by', 'auto_adjusted'
]


def record_weight_change(old_weights, new_weights, reason, triggered_by, 
                         error_stats=None, approved_by='system', auto_adjusted=False):
    """
    记录权重变更历史
    
    Args:
        old_weights: 旧权重字典 {'sentiment': 0.4, ...}
        new_weights: 新权重字典
        reason: 变更原因
        triggered_by: 触发条件描述
        error_stats: 变更前的错误统计
        approved_by: 批准人
        auto_adjusted: 是否自动调整
    
    Returns:
        文件路径
    """
    data_dir = get_data_dir()
    filepath = data_dir / 'weight_history.csv'
    
    record = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'old_sentiment_weight': old_weights.get('sentiment', ''),
        'old_technical_weight': old_weights.get('technical', ''),
        'old_macro_weight': old_weights.get('macro', ''),
        'new_sentiment_weight': new_weights.get('sentiment', ''),
        'new_technical_weight': new_weights.get('technical', ''),
        'new_macro_weight': new_weights.get('macro', ''),
        'change_reason': reason,
        'triggered_by': triggered_by,
        'error_statistics_before': json.dumps(error_stats) if error_stats else '',
        'approved_by': approved_by,
        'auto_adjusted': 'True' if auto_adjusted else 'False'
    }
    
    file_exists = filepath.exists()
    
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=WEIGHT_HISTORY_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)
    
    return filepath


def load_weight_history():
    """
    加载权重变更历史
    
    Returns:
        记录列表
    """
    data_dir = get_data_dir()
    filepath = data_dir / 'weight_history.csv'
    
    records = []
    if not filepath.exists():
        return records
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    
    return records


def get_current_weights():
    """
    从配置文件获取当前权重
    
    Returns:
        dict: 当前权重
    """
    config_path = get_config_dir() / 'prediction_model.json'
    
    if not config_path.exists():
        return {'sentiment': 0.40, 'technical': 0.35, 'macro': 0.25}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    weights = config.get('scoring_weights', {})
    return {
        'sentiment': weights.get('sentiment', {}).get('weight', 0.40),
        'technical': weights.get('technical', {}).get('weight', 0.35),
        'macro': weights.get('macro', {}).get('weight', 0.25)
    }


def update_weights(new_weights, reason, triggered_by, approved_by='system', auto_adjusted=False):
    """
    更新权重配置并记录历史
    
    Args:
        new_weights: 新权重字典
        reason: 变更原因
        triggered_by: 触发条件
        approved_by: 批准人
        auto_adjusted: 是否自动调整
    
    Returns:
        bool: 是否成功
    """
    config_path = get_config_dir() / 'prediction_model.json'
    
    # 获取当前权重
    old_weights = get_current_weights()
    
    # 记录变更历史
    error_stats = get_error_statistics(days=30)
    record_weight_change(
        old_weights=old_weights,
        new_weights=new_weights,
        reason=reason,
        triggered_by=triggered_by,
        error_stats=error_stats,
        approved_by=approved_by,
        auto_adjusted=auto_adjusted
    )
    
    # 更新配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    config['scoring_weights']['sentiment']['weight'] = new_weights['sentiment']
    config['scoring_weights']['technical']['weight'] = new_weights['technical']
    config['scoring_weights']['macro']['weight'] = new_weights['macro']
    
    # 更新公式描述
    config['formula'] = f"综合评分 = 舆情评分 × {new_weights['sentiment']:.2f} + 技术指标 × {new_weights['technical']:.2f} + 宏观因素 × {new_weights['macro']:.2f}"
    
    # 添加调整记录
    if 'adjustment_history' not in config:
        config['adjustment_history'] = []
    
    config['adjustment_history'].append({
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'change': f"sentiment:{old_weights['sentiment']:.2f}->{new_weights['sentiment']:.2f}, "
                  f"technical:{old_weights['technical']:.2f}->{new_weights['technical']:.2f}, "
                  f"macro:{old_weights['macro']:.2f}->{new_weights['macro']:.2f}",
        'reason': reason,
        'triggered_by': triggered_by,
        'adjusted_by': approved_by,
        'auto_adjusted': auto_adjusted
    })
    
    config['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    return True


# ==================== 权重调整建议生成 ====================

def generate_weight_adjustment_suggestion():
    """
    基于学习日志生成权重调整建议
    
    Returns:
        dict: 建议内容
    """
    stats_7d = get_error_statistics(days=7)
    stats_30d = get_error_statistics(days=30)
    current_weights = get_current_weights()
    
    suggestion = {
        'current_weights': current_weights,
        'statistics_7d': stats_7d,
        'statistics_30d': stats_30d,
        'recommendation': None,
        'confidence': 'low',
        'reason': ''
    }
    
    # 如果数据不足，不给出建议
    if stats_7d['total_validated'] < 3:
        suggestion['reason'] = '验证数据不足（需要至少3条），建议继续积累数据'
        return suggestion
    
    # 分析主要错误因子
    main_factor_7d = None
    if stats_7d['attribution_counts']:
        main_factor_7d = max(stats_7d['attribution_counts'], key=stats_7d['attribution_counts'].get)
    
    main_factor_30d = None
    if stats_30d['attribution_counts']:
        main_factor_30d = max(stats_30d['attribution_counts'], key=stats_30d['attribution_counts'].get)
    
    # 如果7天和30天的主要问题因子一致，信心度更高
    if main_factor_7d and main_factor_7d == main_factor_30d:
        suggestion['confidence'] = 'medium'
        
        # 计算建议的新权重
        adjustment = 0.03  # 调整幅度
        new_weights = current_weights.copy()
        
        if main_factor_7d == '舆情因子':
            new_weights['sentiment'] = max(0.30, current_weights['sentiment'] - adjustment)
            # 将减少的部分分配给其他因子
            remaining = current_weights['sentiment'] - new_weights['sentiment']
            new_weights['technical'] += remaining * 0.6
            new_weights['macro'] += remaining * 0.4
            suggestion['recommendation'] = new_weights
            suggestion['reason'] = f"最近7天和30天的主要错误因子均为'舆情因子'，建议降低舆情权重 {adjustment:.0%}"
            
        elif main_factor_7d == '技术因子':
            new_weights['technical'] = max(0.25, current_weights['technical'] - adjustment)
            remaining = current_weights['technical'] - new_weights['technical']
            new_weights['sentiment'] += remaining * 0.6
            new_weights['macro'] += remaining * 0.4
            suggestion['recommendation'] = new_weights
            suggestion['reason'] = f"最近7天和30天的主要错误因子均为'技术因子'，建议降低技术权重 {adjustment:.0%}"
            
        elif main_factor_7d == '宏观因子':
            new_weights['macro'] = max(0.15, current_weights['macro'] - adjustment)
            remaining = current_weights['macro'] - new_weights['macro']
            new_weights['sentiment'] += remaining * 0.6
            new_weights['technical'] += remaining * 0.4
            suggestion['recommendation'] = new_weights
            suggestion['reason'] = f"最近7天和30天的主要错误因子均为'宏观因子'，建议降低宏观权重 {adjustment:.0%}"
    else:
        suggestion['reason'] = '短期和长期错误模式不一致，建议继续观察'
    
    # 归一化权重确保总和为1
    if suggestion['recommendation']:
        total = sum(suggestion['recommendation'].values())
        suggestion['recommendation'] = {
            k: round(v / total, 2) for k, v in suggestion['recommendation'].items()
        }
    
    return suggestion


if __name__ == '__main__':
    # 测试
    print(generate_weekly_summary())
    print("\n" + "="*60 + "\n")
    suggestion = generate_weight_adjustment_suggestion()
    print("权重调整建议:")
    print(json.dumps(suggestion, ensure_ascii=False, indent=2))
