#!/usr/bin/env python3
"""
获取铜价数据 - MVP版本
使用多个数据源，优先使用akshare获取上海期货交易所数据

注意：此脚本需要 Python 3.11+ 和 akshare
如果当前环境不满足，会自动尝试使用 conda 的 py311 环境
"""

import sys
import subprocess
from pathlib import Path

# 检查 Python 版本，如果不满足则尝试切换环境
if sys.version_info < (3, 11):
    print(f"当前 Python {sys.version_info.major}.{sys.version_info.minor} 版本过低，需要 3.11+")
    print("尝试使用 conda py311 环境...")
    
    # 尝试使用 conda 环境重新运行
    try:
        result = subprocess.run(
            ["conda", "run", "-n", "py311", "python", __file__] + sys.argv[1:],
            capture_output=False,
            text=True
        )
        sys.exit(result.returncode)
    except Exception as e:
        print(f"切换环境失败: {e}")
        print("请手动运行: conda run -n py311 python fetch_copper_price_v2.py")
        sys.exit(1)

# 以下是主逻辑，只在 Python 3.11+ 环境下执行
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

from data_storage import save_current_price, save_price_history


def fetch_from_akshare():
    """使用akshare获取上海期货交易所铜期货数据"""
    try:
        import akshare as ak
        
        # 获取铜主力连续合约日线数据
        end_date = datetime.now().strftime("%Y%m%d")
        df = ak.futures_main_sina(symbol="CU0", start_date="20250101", end_date=end_date)
        
        if df.empty:
            return None
        
        # 获取最新数据
        latest = df.iloc[-1]
        previous = df.iloc[-2] if len(df) > 1 else latest
        
        return {
            'source': 'akshare_shfe',
            'current_price': float(latest['收盘价']),
            'previous_close': float(previous['收盘价']),
            'open': float(latest['开盘价']),
            'high': float(latest['最高价']),
            'low': float(latest['最低价']),
            'volume': int(latest['成交量']),
            'hold': int(latest['持仓量']),
            'settle': float(latest['动态结算价']),
            'unit': '元/吨',
            'exchange': '上海期货交易所',
            'contract': '铜主力连续(CU0)',
            'timestamp': datetime.now().isoformat(),
            'data_date': str(latest['日期'])
        }
    except ImportError:
        print("akshare未安装，跳过")
        return None
    except Exception as e:
        print(f"akshare获取失败: {e}")
        return None


def fetch_from_yahoo():
    """尝试从Yahoo Finance获取"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/HG=F?interval=1d&range=30d"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if data.get('chart', {}).get('error'):
            return None
            
        result = data['chart']['result'][0]
        meta = result['meta']
        
        return {
            'source': 'yahoo',
            'current_price': round(meta.get('regularMarketPrice', 0), 4),
            'previous_close': round(meta.get('previousClose', 0), 4),
            'unit': '美元/磅',
            'exchange': 'COMEX',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Yahoo Finance失败: {e}")
        return None


# def fetch_from_mock():
#     """使用模拟数据（当真实API不可用时）"""
#     import random
#     base_price = 73300  # 基于近期沪铜价格
#     variation = random.uniform(-500, 500)
#     current = round(base_price + variation, 2)
#     previous = round(base_price, 2)
#     
#     return {
#         'source': 'mock',
#         'current_price': current,
#         'previous_close': previous,
#         'unit': '元/吨',
#         'exchange': '模拟数据',
#         'contract': '铜主力连续',
#         'timestamp': datetime.now().isoformat(),
#         'note': '使用模拟数据 - 真实API暂时不可用'
#     }


def fetch_copper_price():
    """获取铜价
    
    优先使用 akshare 获取上海期货交易所数据
    如果失败则尝试 Yahoo Finance
    """
    # 尝试akshare
    print("尝试从akshare获取上海期货交易所数据...")
    data = fetch_from_akshare()
    
    if data:
        data['change'] = round(data['current_price'] - data['previous_close'], 2)
        data['change_percent'] = round(((data['current_price'] - data['previous_close']) / data['previous_close']) * 100, 2)
        print("✅ 成功获取上海期货交易所数据")
        return data
    
    # 尝试Yahoo Finance
    print("尝试从Yahoo Finance获取...")
    data = fetch_from_yahoo()
    
    if data:
        data['change'] = round(data['current_price'] - data['previous_close'], 4)
        data['change_percent'] = round(((data['current_price'] - data['previous_close']) / data['previous_close']) * 100, 2)
        print("✅ 成功获取Yahoo Finance数据")
        return data
    
    # 所有数据源均失败
    print("❌ 所有数据源均不可用")
    return None


def save_price_data(price_data):
    """保存价格数据（使用data_storage模块，全部CSV格式）"""
    # 保存当前价格到CSV（覆盖模式）
    current_path = save_current_price(price_data)
    
    # 保存到CSV历史记录（追加/更新模式）
    action, history_path = save_price_history(price_data)
    
    action_labels = {
        'created': '✅ 首次保存铜价数据，创建CSV文件',
        'appended': '✅ 追加今天的铜价数据',
        'updated': '🔄 更新今天的铜价数据'
    }
    
    print(f"\n{action_labels.get(action, '保存铜价数据')}")
    print(f"  价格: {price_data['current_price']} {price_data.get('unit', '元/吨')}")
    print(f"  涨跌: {price_data.get('change', 0)} ({price_data.get('change_percent', 0)}%)")
    print(f"  来源: {price_data.get('exchange', 'unknown')}")
    if 'note' in price_data:
        print(f"  注意: {price_data['note']}")
    print(f"  当前价格CSV: {current_path}")
    print(f"  历史记录CSV: {history_path}")


def is_weekend():
    """检查今天是否是周末（周六=5, 周日=6）"""
    from datetime import datetime
    return datetime.now().weekday() >= 5


if __name__ == '__main__':
    # 周末检测：周六周日跳过
    if is_weekend():
        print("="*60)
        print("📅 今天是周末，上海期货交易所休市")
        print("⏭️  跳过数据获取，使用周五数据")
        print("="*60)
        sys.exit(0)
    
    price_data = fetch_copper_price()
    if price_data:
        save_price_data(price_data)
        print("\n完整数据:")
        print(json.dumps(price_data, ensure_ascii=False, indent=2))
    else:
        sys.exit(1)

