#!/usr/bin/env python3
"""
数据存储模块 - 统一CSV读写操作，JSON仅作为备用功能保留
提供统一的数据持久化接口
"""

import json
import csv
from datetime import datetime
from pathlib import Path


def get_data_dir():
    """获取数据目录"""
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_reports_dir():
    """获取报告目录"""
    reports_dir = Path(__file__).parent.parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    return reports_dir


# ==================== JSON 备用功能（保留但不主动使用）====================

def save_json(filename, data, subdir=None):
    """
    【备用】保存数据到JSON文件
    仅在需要人类可读备份或调试时使用
    """
    data_dir = get_data_dir()
    if subdir:
        data_dir = data_dir / subdir
        data_dir.mkdir(exist_ok=True)
    
    filepath = data_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath


def load_json(filename, default=None, subdir=None):
    """
    【备用】从JSON文件加载数据
    """
    data_dir = get_data_dir()
    if subdir:
        data_dir = data_dir / subdir
    
    filepath = data_dir / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}


# ==================== CSV 核心功能 ====================

def save_csv(filename, records, fieldnames, subdir=None, mode='overwrite'):
    """
    保存数据到CSV文件
    
    Args:
        filename: CSV文件名
        records: 要保存的记录（字典列表或单个字典）
        fieldnames: CSV表头字段列表
        subdir: 可选子目录
        mode: 'overwrite' 覆盖写入 / 'append' 追加模式
    
    Returns:
        文件路径
    """
    data_dir = get_data_dir()
    if subdir:
        data_dir = data_dir / subdir
        data_dir.mkdir(exist_ok=True)
    
    filepath = data_dir / filename
    
    # 确保 records 是列表
    if isinstance(records, dict):
        records = [records]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    return filepath


def append_csv(filename, record, fieldnames, date_field='date', subdir=None):
    """
    追加记录到CSV文件，自动处理表头和去重（按日期）
    
    Args:
        filename: CSV文件名
        record: 要追加的记录（字典）
        fieldnames: CSV表头字段列表
        date_field: 用于去重的日期字段名
        subdir: 可选子目录
    
    Returns:
        tuple: (操作类型, 文件路径)
               操作类型: 'created', 'appended', 'updated'
    """
    data_dir = get_data_dir()
    if subdir:
        data_dir = data_dir / subdir
        data_dir.mkdir(exist_ok=True)
    
    filepath = data_dir / filename
    today = record.get(date_field, datetime.now().strftime('%Y-%m-%d'))
    
    # 检查文件状态
    file_exists = filepath.exists()
    has_valid_data = False
    today_exists = False
    
    if file_exists:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) >= 2:  # 表头 + 至少一行数据
                    has_valid_data = True
                    for line in lines[1:]:
                        if line.startswith(today + ','):
                            today_exists = True
                            break
        except Exception:
            pass
    
    if not file_exists or not has_valid_data:
        # 首次创建
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(record)
        return 'created', filepath
    
    elif today_exists:
        # 更新今天的记录
        all_records = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get(date_field) == today:
                    all_records.append(record)
                else:
                    all_records.append(row)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)
        return 'updated', filepath
    
    else:
        # 追加新记录
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(record)
        return 'appended', filepath


def load_csv(filename, subdir=None):
    """
    从CSV文件加载所有记录
    
    Args:
        filename: CSV文件名
        subdir: 可选子目录
    
    Returns:
        记录列表（字典列表）
    """
    data_dir = get_data_dir()
    if subdir:
        data_dir = data_dir / subdir
    
    filepath = data_dir / filename
    records = []
    
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
    
    return records


# ==================== 业务数据存储接口 ====================

def save_price_history(price_data):
    """
    保存铜价历史数据到CSV
    
    Args:
        price_data: 价格数据字典
    
    Returns:
        tuple: (操作类型, 文件路径)
    """
    fieldnames = ['date', 'price', 'change', 'change_percent', 'open', 'high', 
                  'low', 'volume', 'hold', 'source', 'unit', 'exchange', 'contract']
    
    # 使用数据本身的日期（交易所数据日期），如果没有则使用今天
    data_date = price_data.get('data_date', '')
    if not data_date:
        data_date = datetime.now().strftime('%Y-%m-%d')
    
    record = {
        'date': data_date,
        'price': price_data.get('current_price', ''),
        'change': price_data.get('change', ''),
        'change_percent': price_data.get('change_percent', ''),
        'open': price_data.get('open', ''),
        'high': price_data.get('high', ''),
        'low': price_data.get('low', ''),
        'volume': price_data.get('volume', ''),
        'hold': price_data.get('hold', ''),
        'source': price_data.get('source', 'unknown'),
        'unit': price_data.get('unit', '元/吨'),
        'exchange': price_data.get('exchange', 'unknown'),
        'contract': price_data.get('contract', '')
    }
    
    return append_csv('price_history.csv', record, fieldnames)


def save_current_price(price_data):
    """
    保存当前价格到CSV（单条记录，覆盖模式）
    
    Returns:
        文件路径
    """
    fieldnames = ['date', 'price', 'change', 'change_percent', 'open', 'high',
                  'low', 'volume', 'hold', 'source', 'unit', 'exchange', 'contract']
    
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'price': price_data.get('current_price', ''),
        'change': price_data.get('change', ''),
        'change_percent': price_data.get('change_percent', ''),
        'open': price_data.get('open', ''),
        'high': price_data.get('high', ''),
        'low': price_data.get('low', ''),
        'volume': price_data.get('volume', ''),
        'hold': price_data.get('hold', ''),
        'source': price_data.get('source', 'unknown'),
        'unit': price_data.get('unit', '元/吨'),
        'exchange': price_data.get('exchange', 'unknown'),
        'contract': price_data.get('contract', '')
    }
    
    return save_csv('current_price.csv', record, fieldnames)


def save_news_data(news_data):
    """
    保存新闻数据到CSV
    
    Args:
        news_data: 新闻数据字典，包含 news 列表
    
    Returns:
        文件路径
    """
    fieldnames = ['date', 'title', 'source', 'url', 'summary', 'score', 
                  'sentiment', 'sentiment_score', 'is_recent', 'days_old', 'time_weight']
    
    records = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    for news in news_data.get('news', []):
        records.append({
            'date': news.get('date', today),
            'title': news.get('title', ''),
            'source': news.get('source', ''),
            'url': news.get('url', ''),
            'summary': news.get('summary', ''),
            'score': news.get('score', 0),
            'sentiment': news.get('sentiment', ''),
            'sentiment_score': news.get('sentiment_score', 0),
            'is_recent': news.get('is_recent', False),
            'days_old': news.get('days_old', 0),
            'time_weight': news.get('time_weight', 1.0)
        })
    
    return save_csv('latest_news.csv', records, fieldnames)


def save_prediction(prediction_data):
    """
    保存预测数据到CSV，并追加到历史记录
    
    Args:
        prediction_data: 预测数据字典
    
    Returns:
        tuple: (最新预测文件路径, 历史预测文件路径)
    """
    # 扁平化预测数据为CSV记录
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 基础字段
    base_record = {
        'date': today,
        'timestamp': prediction_data.get('timestamp', ''),
        'current_price': prediction_data.get('current_price', ''),
        'sentiment_score': prediction_data.get('sentiment_score', ''),
        'technical_score': prediction_data.get('technical_score', ''),
        'macro_score': prediction_data.get('macro_score', ''),
        'composite_score': prediction_data.get('composite_score', ''),
        'overall_direction': prediction_data.get('overall_direction', ''),
        'confidence': prediction_data.get('confidence', '')
    }
    
    # 添加各时间窗口预测
    predictions = prediction_data.get('predictions', {})
    for period in ['5d', '1w', '1m']:
        pred = predictions.get(period, {})
        base_record[f'{period}_direction'] = pred.get('direction', '')
        base_record[f'{period}_confidence'] = pred.get('confidence', '')
        base_record[f'{period}_target_price'] = pred.get('target_price', '')
    
    fieldnames = [
        'date', 'timestamp', 'current_price',
        'sentiment_score', 'technical_score', 'macro_score', 'composite_score',
        'overall_direction', 'confidence',
        '5d_direction', '5d_confidence', '5d_target_price',
        '1w_direction', '1w_confidence', '1w_target_price',
        '1m_direction', '1m_confidence', '1m_target_price'
    ]
    
    # 保存最新预测（覆盖）
    latest_path = save_csv('latest_prediction.csv', base_record, fieldnames)
    
    # 追加到历史记录
    history_path = (get_data_dir() / 'predictions.csv')
    append_csv('predictions.csv', base_record, fieldnames, date_field='date')
    
    return latest_path, history_path


def save_macro_data(macro_data):
    """
    保存宏观数据到CSV
    
    Args:
        macro_data: 宏观数据字典
    
    Returns:
        文件路径
    """
    fieldnames = ['date', 'indicator', 'value', 'status', 'policy_stance', 
                  'impact_on_copper', 'source', 'timestamp']
    
    records = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    for item in macro_data.get('data', []):
        # 处理库存数据（嵌套结构）
        if item.get('indicator') == 'COPPER_INVENTORY' and 'data' in item:
            for inv in item.get('data', []):
                records.append({
                    'date': today,
                    'indicator': f"INVENTORY_{inv.get('exchange', '')}",
                    'value': inv.get('inventory', ''),
                    'status': '',
                    'policy_stance': '',
                    'impact_on_copper': '',
                    'source': inv.get('source', ''),
                    'timestamp': item.get('timestamp', '')
                })
        else:
            records.append({
                'date': today,
                'indicator': item.get('indicator', ''),
                'value': item.get('value', ''),
                'status': item.get('status', ''),
                'policy_stance': item.get('policy_stance', ''),
                'impact_on_copper': item.get('impact_on_copper', ''),
                'source': item.get('source', ''),
                'timestamp': item.get('timestamp', '')
            })
    
    return save_csv('macro_data.csv', records, fieldnames)


def save_validation_report(report_data, detailed_records=None):
    """
    保存验证报告到CSV
    
    Args:
        report_data: 汇总数据字典
        detailed_records: 详细记录列表（可选）
    
    Returns:
        tuple: (汇总报告路径, 详细报告路径)
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 汇总报告
    summary_fieldnames = [
        'date', 'total_predictions', 'validated_predictions',
        'direction_accuracy_5d', 'direction_accuracy_1w', 'direction_accuracy_1m',
        'mae_5d', 'mae_1w', 'mae_1m',
        'rmse_5d', 'rmse_1w', 'rmse_1m',
        'avg_confidence', 'confidence_calibration'
    ]
    
    summary_path = save_csv(
        f'validation_summary_{today}.csv',
        report_data,
        summary_fieldnames,
        subdir='validation'
    )
    
    # 详细报告
    detail_path = None
    if detailed_records:
        detail_fieldnames = [
            'date', 'predicted_direction', 'actual_direction', 'direction_correct',
            'predicted_price', 'actual_price', 'price_error',
            'sentiment_score', 'technical_score', 'macro_score',
            'error_analysis', 'factor_attribution'
        ]
        detail_path = save_csv(
            f'validation_detailed_{today}.csv',
            detailed_records,
            detail_fieldnames,
            subdir='validation'
        )
    
    return summary_path, detail_path
