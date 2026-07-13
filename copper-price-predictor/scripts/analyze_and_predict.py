#!/usr/bin/env python3
"""
分析数据并生成铜价预测 - MVP版本
基于新闻情绪和宏观因子生成预测
"""

import json
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 添加当前目录以导入 data_storage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_storage import load_csv, save_prediction, load_json, get_data_dir


def load_config():
    """加载预测模型配置"""
    config_file = Path(__file__).parent.parent / 'config' / 'prediction_model.json'
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_data(news_file=None):
    """加载价格数据和新闻数据"""
    data_dir = Path(__file__).parent.parent / 'data'
    
    price_data = None
    news_data = None
    macro_data = None
    
    # 加载价格数据（CSV）
    price_records = load_csv('current_price.csv')
    if price_records:
        price_data = price_records[0]  # 取最新一条
    
    # 加载新闻数据
    if news_file:
        # 从JSON文件加载（包含AI分析结果）
        print(f"📂 从文件加载新闻数据: {news_file}")
        news_file_path = Path(news_file)
        if news_file_path.exists():
            with open(news_file_path, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
            print(f"   ✅ 加载成功: {news_data.get('news_count', 0)} 条新闻")
            print(f"   📊 加权情感得分: {news_data.get('weighted_sentiment_score', 0):.2f}")
        else:
            print(f"   ⚠️ 文件不存在: {news_file}")
            news_data = None
    else:
        # 从CSV加载（备用）
        print("📂 从CSV加载新闻数据...")
        news_records = load_csv('latest_news.csv')
        if news_records:
            news_data = {'news': news_records}
            print(f"   ✅ 加载成功: {len(news_records)} 条新闻")
    
    # 加载宏观数据（CSV）
    macro_records = load_csv('macro_data.csv')
    if macro_records:
        macro_data = macro_records
    
    return price_data, news_data, macro_data


def analyze_sentiment(news_data):
    """分析新闻情绪（考虑时间权重）"""
    if not news_data or 'news' not in news_data:
        return 0.0
    
    weighted_score = 0
    total_weight = 0
    
    for news in news_data['news']:
        sentiment = news.get('sentiment', 'neutral')
        # 跳过旧闻和未分析的
        if sentiment in ['old_news', 'pending']:
            continue
        
        # 优先使用 sentiment_score 数值（-1.0 到 +1.0）
        try:
            score = float(news.get('sentiment_score', 0))
        except (ValueError, TypeError):
            score = 0.0
        try:
            weight = float(news.get('time_weight', 1.0))
        except (ValueError, TypeError):
            weight = 1.0
        
        weighted_score += score * weight
        total_weight += weight
    
    # 加权平均
    avg_sentiment = weighted_score / total_weight if total_weight > 0 else 0
    return round(avg_sentiment, 2)


def analyze_macro(macro_data):
    """分析宏观因子得分"""
    if not macro_data:
        return 0.0
    
    # 尝试加载AI分析结果
    ai_file = Path(__file__).parent.parent / 'data' / 'macro_ai_analysis.json'
    if ai_file.exists():
        try:
            with open(ai_file, 'r', encoding='utf-8') as f:
                ai_results = json.load(f)
                composite = ai_results.get('composite', {})
                score = composite.get('composite_score', 0)
                return round(score / 10.0, 2)  # 归一化到 -1 到 +1
        except Exception:
            pass
    
    # 备用：简单规则分析
    total_score = 0
    count = 0
    
    for record in macro_data:
        indicator = record.get('indicator', '')
        value = record.get('value', '')
        
        try:
            if indicator == 'USD_INDEX':
                v = float(value)
                if v > 100: total_score -= 0.5
                elif v < 95: total_score += 0.5
                count += 1
            elif indicator == 'US_ISM_PMI':
                v = float(value)
                if v > 50: total_score += 0.5
                else: total_score -= 0.5
                count += 1
            elif indicator == 'FED_POLICY':
                stance = record.get('policy_stance', 'neutral')
                if stance == 'dovish': total_score += 0.5
                elif stance == 'hawkish': total_score -= 0.5
                count += 1
        except (ValueError, TypeError):
            continue
    
    return round(total_score / count, 2) if count > 0 else 0.0


def generate_prediction(price_data, news_data, macro_data):
    """生成价格预测"""
    if not price_data:
        return None
    
    # 加载配置
    config = load_config()
    weights = config.get('scoring_weights', {}) if config else {}
    confidence_levels = config.get('confidence_levels', {}) if config else {}
    
    current_price = float(price_data.get('price', 0))
    sentiment = analyze_sentiment(news_data)
    macro_score = analyze_macro(macro_data)
    
    # 基于配置权重的预测模型（仅舆情和宏观两个因子）
    sentiment_weight = weights.get('sentiment', {}).get('weight', 0.50)
    macro_weight = weights.get('macro', {}).get('weight', 0.50)
    
    # 情绪影响系数（基于权重，归一化到 -10 到 +10）
    sentiment_factor = sentiment * sentiment_weight * 10
    
    # 宏观因素
    macro_factor = macro_score * macro_weight * 10
    
    # 综合评分（-10 到 +10）
    composite_score = sentiment_factor + macro_factor
    composite_score = max(-10, min(10, composite_score))  # 限制范围
    
    # 生成不同时间段的预测
    predictions = {}
    
    # 5天预测
    change_5d = composite_score * 0.005  # 每天0.5%的波动
    predictions['5d'] = {
        'direction': 'up' if change_5d > 0.005 else 'down' if change_5d < -0.005 else 'stable',
        'confidence': confidence_levels.get('5_days', {}).get('default', 0.6),
        'target_price': round(current_price * (1 + change_5d * 5), 2)
    }
    
    # 1周预测
    change_1w = composite_score * 0.004
    predictions['1w'] = {
        'direction': 'up' if change_1w > 0.005 else 'down' if change_1w < -0.005 else 'stable',
        'confidence': confidence_levels.get('1_week', {}).get('default', 0.5),
        'target_price': round(current_price * (1 + change_1w * 7), 2)
    }
    
    # 1个月预测
    change_1m = composite_score * 0.003
    predictions['1m'] = {
        'direction': 'up' if change_1m > 0.005 else 'down' if change_1m < -0.005 else 'stable',
        'confidence': confidence_levels.get('1_month', {}).get('default', 0.4),
        'target_price': round(current_price * (1 + change_1m * 30), 2)
    }
    
    # 整体方向
    overall_direction = 'up' if composite_score > 1 else 'down' if composite_score < -1 else 'neutral'
    avg_confidence = sum(p['confidence'] for p in predictions.values()) / len(predictions)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'current_price': current_price,
        'sentiment_score': round(sentiment, 2),
        'technical_score': 0,
        'macro_score': round(macro_factor, 2),
        'composite_score': round(composite_score, 2),
        'overall_direction': overall_direction,
        'confidence': round(avg_confidence, 2),
        'predictions': predictions,
        'weights_used': {
            'sentiment': sentiment_weight,
            'macro': macro_weight
        }
    }


def save_prediction_result(prediction):
    """保存预测结果到CSV"""
    latest_path, history_path = save_prediction(prediction)
    print(f"\n💾 预测已保存:")
    print(f"   最新预测: {latest_path}")
    print(f"   历史记录: {history_path}")


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='分析数据并生成铜价预测')
    parser.add_argument('--news-file', type=str,
                       help='从JSON文件加载已分析的新闻数据（跳过搜索和AI分析）')
    args = parser.parse_args()
    
    # 加载数据
    price_data, news_data, macro_data = load_data(args.news_file)
    
    if not price_data:
        print("错误: 没有找到价格数据，请先运行 fetch_copper_price_v2.py")
        sys.exit(1)
    
    print("="*60)
    print("📊 开始生成铜价预测...")
    print("="*60)
    
    prediction = generate_prediction(price_data, news_data, macro_data)
    if prediction:
        save_prediction_result(prediction)
        
        print(f"\n{'='*60}")
        print("📈 预测结果")
        print(f"{'='*60}")
        print(f"当前价格: {prediction['current_price']}")
        print(f"综合评分: {prediction['composite_score']}")
        print(f"整体方向: {prediction['overall_direction']}")
        print(f"平均置信度: {prediction['confidence']*100}%")
        print(f"\n各时间窗口预测:")
        for period, pred in prediction['predictions'].items():
            print(f"  {period}: {pred['direction']} (置信度: {pred['confidence']*100}%, 目标价: {pred['target_price']})")
    else:
        sys.exit(1)
