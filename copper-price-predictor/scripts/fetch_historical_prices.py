#!/usr/bin/env python3
"""
补齐历史铜价数据 - 使用akshare获取2026年6-7月数据
"""

import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_storage import save_csv, load_csv, get_data_dir


def fetch_historical_prices():
    """使用akshare获取历史铜价数据"""
    try:
        import akshare as ak
        
        print("🔍 从akshare获取铜主力连续合约历史数据...")
        
        # 获取2026年6月1日至今的数据
        df = ak.futures_main_sina(symbol="CU0", start_date="20250601", end_date="20260702")
        
        if df.empty:
            print("❌ 未获取到数据")
            return None
        
        print(f"✅ 获取到 {len(df)} 条历史数据")
        
        # 转换为统一格式
        records = []
        for idx, row in df.iterrows():
            date_str = str(row['日期'])
            
            # 计算涨跌（需要前一天数据）
            current_close = float(row['收盘价'])
            
            record = {
                'date': date_str,
                'price': current_close,
                'change': '',  # 稍后计算
                'change_percent': '',  # 稍后计算
                'open': float(row['开盘价']),
                'high': float(row['最高价']),
                'low': float(row['最低价']),
                'volume': int(row['成交量']),
                'hold': int(row['持仓量']),
                'source': 'akshare_shfe',
                'unit': '元/吨',
                'exchange': '上海期货交易所',
                'contract': '铜主力连续(CU0)'
            }
            records.append(record)
        
        # 计算涨跌（基于前一天收盘价）
        for i in range(1, len(records)):
            prev_close = records[i-1]['price']
            curr_close = records[i]['price']
            records[i]['change'] = round(curr_close - prev_close, 2)
            records[i]['change_percent'] = round(((curr_close - prev_close) / prev_close) * 100, 2)
        
        # 第一条没有前一天数据，设为0
        if records:
            records[0]['change'] = 0.0
            records[0]['change_percent'] = 0.0
        
        return records
        
    except ImportError:
        print("❌ akshare未安装，无法获取历史数据")
        print("请运行: pip install akshare")
        return None
    except Exception as e:
        print(f"❌ 获取历史数据失败: {e}")
        return None


def merge_with_existing(new_records):
    """合并新数据与现有数据"""
    data_dir = get_data_dir()
    history_file = data_dir / 'price_history.csv'
    
    # 读取现有数据
    existing_records = []
    if history_file.exists():
        existing_records = load_csv('price_history.csv')
        print(f"📂 现有历史记录: {len(existing_records)} 条")
    
    # 合并（去重：基于日期）
    existing_dates = {r['date'] for r in existing_records}
    
    merged = existing_records.copy()
    added_count = 0
    
    for record in new_records:
        if record['date'] not in existing_dates:
            merged.append(record)
            added_count += 1
    
    # 按日期排序
    merged.sort(key=lambda x: x['date'])
    
    print(f"➕ 新增记录: {added_count} 条")
    print(f"📊 合并后总计: {len(merged)} 条")
    
    return merged


def save_merged_history(records):
    """保存合并后的历史数据"""
    fieldnames = ['date', 'price', 'change', 'change_percent', 'open', 'high', 
                  'low', 'volume', 'hold', 'source', 'unit', 'exchange', 'contract']
    
    filepath = save_csv('price_history.csv', records, fieldnames)
    print(f"\n💾 历史数据已保存: {filepath}")
    
    # 同时更新 current_price.csv（最新一天）
    if records:
        latest = records[-1]
        from data_storage import save_current_price
        
        price_data = {
            'current_price': latest['price'],
            'change': latest['change'],
            'change_percent': latest['change_percent'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'volume': latest['volume'],
            'hold': latest['hold'],
            'source': latest['source'],
            'unit': latest['unit'],
            'exchange': latest['exchange'],
            'contract': latest['contract']
        }
        save_current_price(price_data)
        print(f"💾 当前价格已更新: {latest['date']} {latest['price']}元/吨")
    
    return filepath


if __name__ == '__main__':
    print("="*60)
    print("📈 补齐铜价历史数据")
    print("="*60)
    
    # 获取历史数据
    historical_records = fetch_historical_prices()
    
    if historical_records:
        # 合并并保存
        merged_records = merge_with_existing(historical_records)
        save_merged_history(merged_records)
        
        # 显示数据范围
        print(f"\n📅 数据范围: {merged_records[0]['date']} 至 {merged_records[-1]['date']}")
        print(f"📊 共 {len(merged_records)} 个交易日")
    else:
        print("\n❌ 未能获取历史数据")
        sys.exit(1)
