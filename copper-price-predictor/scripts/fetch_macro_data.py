#!/usr/bin/env python3
"""
获取宏观数据 - 美元指数、PMI、库存等
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/skills/moochmaniac-tavily-search/scripts"))
# 添加当前目录以导入 analyze_macro_ai
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from search import search_tavily
except ImportError:
    print("错误：无法导入 Tavily 搜索模块")
    sys.exit(1)

# 导入 AI 宏观分析
try:
    from analyze_macro_ai import analyze_all_macro_factors, calculate_macro_composite_score
    AI_MACRO_AVAILABLE = True
    print("✅ AI 宏观分析模块已加载")
except ImportError as e:
    AI_MACRO_AVAILABLE = False
    print(f"⚠️  AI 宏观分析模块不可用: {e}")


def fetch_usd_index():
    """获取美元指数"""
    print("🔍 搜索美元指数...")
    result = search_tavily(
        query="美元指数 DXY 今日行情",
        max_results=2,
        search_depth="advanced"
    )
    
    if "error" in result:
        return None
    
    for item in result.get("results", []):
        content = item.get("content", "")
        # 尝试提取美元指数数值
        import re
        # 匹配各种格式的美元指数数值
        # 格式1: "美元指数：XX.XX" 或 "DXY: XX.XX"
        # 格式2: 直接出现的 "101.28" 前后有美元/指数相关关键词
        matches = re.findall(r'美元指数[:\s]+(\d+\.?\d*)', content)
        if not matches:
            matches = re.findall(r'DXY[:\s]+(\d+\.?\d*)', content)
        if not matches:
            # 更宽松的匹配：查找 "US Dollar Index" 或 "美元指数" 附近的数字
            matches = re.findall(r'(?:US Dollar Index|美元指数|DXY)[^\d]{0,30}(\d{2,3}\.\d{2})', content, re.IGNORECASE)
        if not matches:
            # 再尝试：查找 "101.28 +0.17" 这种格式
            matches = re.findall(r'(\d{2,3}\.\d{2})\s*[+-]\d+\.\d+', content)
        
        if matches:
            return {
                'indicator': 'USD_INDEX',
                'value': float(matches[0]),
                'source': item.get("url", ""),
                'timestamp': datetime.now().isoformat()
            }
    
    return None


def fetch_us_pmi():
    """获取美国 ISM 制造业 PMI"""
    print("🔍 搜索美国 ISM 制造业 PMI...")
    result = search_tavily(
        query="美国 ISM制造业PMI 最新数据",
        max_results=2,
        search_depth="advanced"
    )
    
    if "error" in result:
        return None
    
    for item in result.get("results", []):
        content = item.get("content", "")
        import re
        # 匹配 PMI 数值（多种格式）
        matches = re.findall(r'PMI[:\s]+(\d+\.?\d*)', content)
        if not matches:
            matches = re.findall(r'制造业指数[:\s]+(\d+\.?\d*)', content)
        if not matches:
            # 更宽松的匹配：查找 "PMI" 附近的数字
            matches = re.findall(r'(?:PMI|制造业指数)[^\d]{0,30}(\d{2,3}\.\d{1,2})', content, re.IGNORECASE)
        if not matches:
            # 尝试匹配表格格式："54.4" 单独出现的数字
            matches = re.findall(r'\b(\d{2,3}\.\d)\b', content)
        
        if matches:
            pmi_value = float(matches[0])
            # PMI > 50 表示扩张，< 50 表示收缩
            status = "expansion" if pmi_value > 50 else "contraction"
            return {
                'indicator': 'US_ISM_PMI',
                'value': pmi_value,
                'status': status,
                'source': item.get("url", ""),
                'timestamp': datetime.now().isoformat()
            }
    
    return None


def fetch_copper_inventory():
    """获取铜库存数据"""
    print("🔍 搜索铜库存数据...")
    
    inventories = []
    
    # LME 库存
    result = search_tavily(
        query="LME铜库存 今日",
        max_results=1,
        search_depth="advanced"
    )
    if "error" not in result:
        for item in result.get("results", []):
            content = item.get("content", "")
            import re
            matches = re.findall(r'LME铜库存[:\s]+(\d+,?\d*)', content)
            if not matches:
                # 更宽松的匹配
                matches = re.findall(r'(?:LME|伦敦金属交易所)[^\d]{0,20}(\d{3,6},?\d{0,3})\s*(?:吨|吨)', content)
            if not matches:
                # 尝试匹配纯数字（假设是库存）
                matches = re.findall(r'\b(\d{5,6})\b', content)
            if matches:
                inventories.append({
                    'exchange': 'LME',
                    'inventory': int(matches[0].replace(',', '')),
                    'source': item.get("url", "")
                })
    
    # COMEX 库存
    result = search_tavily(
        query="COMEX铜库存 今日",
        max_results=1,
        search_depth="advanced"
    )
    if "error" not in result:
        for item in result.get("results", []):
            content = item.get("content", "")
            import re
            matches = re.findall(r'COMEX铜库存[:\s]+(\d+,?\d*)', content)
            if not matches:
                # 更宽松的匹配
                matches = re.findall(r'(?:COMEX|纽约商品交易所)[^\d]{0,20}(\d{3,6},?\d{0,3})\s*(?:吨|吨)', content)
            if not matches:
                # 尝试匹配纯数字
                matches = re.findall(r'\b(\d{5,6})\b', content)
            if matches:
                inventories.append({
                    'exchange': 'COMEX',
                    'inventory': int(matches[0].replace(',', '')),
                    'source': item.get("url", "")
                })
    
    return {
        'indicator': 'COPPER_INVENTORY',
        'data': inventories,
        'timestamp': datetime.now().isoformat()
    } if inventories else None


def fetch_fed_policy():
    """获取美联储政策预期"""
    print("🔍 搜索美联储政策...")
    result = search_tavily(
        query="美联储 利率决议 最新 2026",
        max_results=2,
        search_depth="advanced"
    )
    
    if "error" in result:
        return None
    
    # 分析新闻情感
    sentiment_text = ""
    for item in result.get("results", []):
        sentiment_text += item.get("title", "") + " " + item.get("content", "")[:500]
    
    # 简单判断
    if "降息" in sentiment_text or "宽松" in sentiment_text:
        policy = "dovish"  # 鸽派/宽松 - 利好铜价
        impact = "positive"
    elif "加息" in sentiment_text or "紧缩" in sentiment_text:
        policy = "hawkish"  # 鹰派/紧缩 - 利空铜价
        impact = "negative"
    else:
        policy = "neutral"
        impact = "neutral"
    
    return {
        'indicator': 'FED_POLICY',
        'policy_stance': policy,
        'impact_on_copper': impact,
        'source': result.get("results", [{}])[0].get("url", ""),
        'timestamp': datetime.now().isoformat()
    }


def is_weekend():
    """检查今天是否是周末（周六=5, 周日=6）"""
    return datetime.now().weekday() >= 5


def fetch_all_macro_data():
    """获取所有宏观数据并进行AI分析"""
    print("="*60)
    print("📊 开始获取宏观数据...")
    print("="*60)
    
    # 周末检测：周六周日跳过
    if is_weekend():
        print("📅 今天是周末，宏观数据无更新")
        print("⏭️  跳过宏观数据获取，使用周五数据")
        print("="*60)
        return {'timestamp': datetime.now().isoformat(), 'data': [], 'weekend_skip': True}, None
    
    macro_data = {
        'timestamp': datetime.now().isoformat(),
        'data': []
    }
    
    # 美元指数
    usd = fetch_usd_index()
    if usd:
        macro_data['data'].append(usd)
        print(f"✅ 美元指数: {usd['value']}")
    
    # PMI
    pmi = fetch_us_pmi()
    if pmi:
        macro_data['data'].append(pmi)
        status_cn = "扩张" if pmi['status'] == 'expansion' else "收缩"
        print(f"✅ 美国PMI: {pmi['value']} ({status_cn})")
    
    # 库存
    inv = fetch_copper_inventory()
    if inv:
        macro_data['data'].append(inv)
        for item in inv['data']:
            print(f"✅ {item['exchange']}库存: {item['inventory']:,} 吨")
    
    # 美联储政策
    fed = fetch_fed_policy()
    if fed:
        macro_data['data'].append(fed)
        policy_cn = {"dovish": "鸽派/宽松", "hawkish": "鹰派/紧缩", "neutral": "中性"}
        impact_cn = {"positive": "利好铜价", "negative": "利空铜价", "neutral": "中性"}
        print(f"✅ 美联储政策: {policy_cn.get(fed['policy_stance'], fed['policy_stance'])} ({impact_cn.get(fed['impact_on_copper'], '')})")
    
    # AI 分析
    ai_results = None
    if AI_MACRO_AVAILABLE and macro_data['data']:
        print("\n🤖 开始 AI 宏观因子分析...")
        factor_results = analyze_all_macro_factors(macro_data)
        if factor_results:
            composite = calculate_macro_composite_score(factor_results)
            ai_results = {
                'timestamp': datetime.now().isoformat(),
                'factors': factor_results,
                'composite': composite
            }
            print(f"\n📊 宏观综合得分: {composite['composite_score']}")
            print("因子分解:")
            for b in composite['factor_breakdown']:
                emoji = "📈" if b['score'] > 0 else "📉" if b['score'] < 0 else "➡️"
                print(f"  {emoji} {b['indicator']}: {b['score']} × {b['weight']} = {b['weighted_contribution']}")
    
    return macro_data, ai_results


def save_macro_data(macro_data, ai_analysis_results=None):
    """保存宏观数据到CSV"""
    from data_storage import save_macro_data as save_macro_csv
    
    # 保存原始宏观数据到CSV
    filepath = save_macro_csv(macro_data)
    print(f"\n💾 宏观数据已保存CSV: {filepath}")
    
    # 如果有AI分析结果，也保存
    if ai_analysis_results:
        data_dir = Path(__file__).parent.parent / "data"
        ai_file = data_dir / "macro_ai_analysis.json"
        with open(ai_file, 'w', encoding='utf-8') as f:
            json.dump(ai_analysis_results, f, ensure_ascii=False, indent=2)
        print(f"💾 AI分析结果已保存: {ai_file}")
    
    return filepath


if __name__ == '__main__':
    macro_data, ai_results = fetch_all_macro_data()
    
    # 周末跳过时不保存
    if macro_data.get('weekend_skip'):
        print("\n" + "="*60)
        print("📊 宏观数据摘要")
        print("="*60)
        print("周末跳过，未获取新数据")
        sys.exit(0)
    
    save_macro_data(macro_data, ai_results)
    
    print("\n" + "="*60)
    print("📊 宏观数据摘要")
    print("="*60)
    print(f"数据项: {len(macro_data['data'])} 个")
    if ai_results:
        print(f"AI综合得分: {ai_results['composite']['composite_score']}")
    else:
        print("AI分析: 未执行")
