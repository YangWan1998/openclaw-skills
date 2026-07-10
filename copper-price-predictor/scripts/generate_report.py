#!/usr/bin/env python3
"""
生成铜价预测报告 - MVP版本
整合所有数据生成可读报告（TXT格式）
报告保存到 reports/ 目录，文件名格式：YYYY-MM-DD_分析报告.txt
"""

import csv
import json
from datetime import datetime
from pathlib import Path


def load_all_data():
    """加载所有相关数据（从CSV）"""
    data_dir = Path(__file__).parent.parent / 'data'
    
    data = {}
    
    # 加载价格数据（CSV）
    price_file = data_dir / 'current_price.csv'
    if price_file.exists():
        with open(price_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                data['price'] = rows[0]
    
    # 加载新闻数据（CSV）
    news_file = data_dir / 'latest_news.csv'
    if news_file.exists():
        with open(news_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data['news'] = list(reader)
    
    # 加载预测数据（CSV）
    pred_file = data_dir / 'latest_prediction.csv'
    if pred_file.exists():
        with open(pred_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                data['prediction'] = rows[0]
    
    # 加载宏观数据（CSV）
    macro_file = data_dir / 'macro_data.csv'
    if macro_file.exists():
        with open(macro_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data['macro'] = list(reader)
    
    return data


def generate_report(data):
    """生成报告"""
    report = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    report.append("=" * 60)
    report.append("铜价预测日报")
    report.append(f"报告日期: {today}")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)
    
    # 价格信息
    if 'price' in data:
        price = data['price']
        report.append("\n📊 当前价格")
        report.append("-" * 40)
        unit = price.get('unit', '元/吨')
        report.append(f"铜价: {price.get('price', 'N/A')} {unit}")
        report.append(f"涨跌: {price.get('change', 'N/A')} ({price.get('change_percent', 'N/A')}%)")
        report.append(f"最高: {price.get('high', 'N/A')} | 最低: {price.get('low', 'N/A')}")
        report.append(f"成交量: {price.get('volume', 'N/A')} | 持仓: {price.get('hold', 'N/A')}")
        report.append(f"数据来源: {price.get('exchange', '未知')}")
    
    # 宏观因子
    if 'macro' in data and data['macro']:
        report.append("\n🌍 宏观因子")
        report.append("-" * 40)
        for item in data['macro']:
            indicator = item.get('indicator', '')
            value = item.get('value', '')
            status = item.get('status', '')
            policy = item.get('policy_stance', '')
            
            if indicator.startswith('INVENTORY_'):
                exchange = indicator.replace('INVENTORY_', '')
                report.append(f"  {exchange}库存: {value} 吨")
            elif indicator == 'USD_INDEX':
                report.append(f"  美元指数: {value}")
            elif indicator == 'US_ISM_PMI':
                status_cn = "扩张" if status == 'expansion' else "收缩" if status == 'contraction' else ""
                report.append(f"  美国PMI: {value} ({status_cn})")
            elif indicator == 'FED_POLICY':
                policy_cn = {"dovish": "鸽派/宽松", "hawkish": "鹰派/紧缩", "neutral": "中性"}.get(policy, policy)
                report.append(f"  美联储政策: {policy_cn}")
    
    # 新闻摘要
    if 'news' in data and data['news']:
        report.append("\n📰 相关新闻")
        report.append("-" * 40)
        
        # 只显示已分析的新闻
        analyzed_news = [n for n in data['news'] if n.get('sentiment') != 'un analyzed']
        for i, news in enumerate(analyzed_news[:5], 1):
            sentiment_emoji = {'positive': '📈', 'negative': '📉', 'neutral': '➡️'}.get(news.get('sentiment'), '➡️')
            score = news.get('sentiment_score', 0)
            report.append(f"{i}. {sentiment_emoji} {news.get('title', '')}")
            report.append(f"   来源: {news.get('source', '')} | 情感: {news.get('sentiment', '')} ({score})")
            report.append(f"   {news.get('summary', '')[:80]}...")
    
    # 预测结果
    if 'prediction' in data:
        pred = data['prediction']
        report.append("\n🔮 价格预测")
        report.append("-" * 40)
        report.append(f"综合评分: {pred.get('composite_score', 'N/A')}")
        report.append(f"整体方向: {pred.get('overall_direction', 'N/A')}")
        report.append(f"平均置信度: {float(pred.get('confidence', 0))*100:.0f}%")
        report.append(f"\n因子得分:")
        report.append(f"  舆情: {pred.get('sentiment_score', 'N/A')}")
        report.append(f"  技术: {pred.get('technical_score', 'N/A')}")
        report.append(f"  宏观: {pred.get('macro_score', 'N/A')}")
        
        report.append(f"\n各时间窗口预测:")
        for period in ['5d', '1w', '1m']:
            direction = pred.get(f'{period}_direction', '')
            confidence = pred.get(f'{period}_confidence', '')
            target = pred.get(f'{period}_target_price', '')
            
            direction_emoji = {'up': '📈', 'down': '📉', 'stable': '➡️'}.get(direction, '➡️')
            report.append(f"  {period}: {direction_emoji} {direction}")
            report.append(f"    置信度: {float(confidence)*100:.0f}% | 目标价: {target}")
    
    report.append("\n" + "=" * 60)
    report.append("⚠️ 免责声明: 本预测仅供参考，不构成投资建议")
    report.append("=" * 60)
    
    return "\n".join(report)


def save_report(report_text):
    """保存报告到 reports/ 目录，文件名格式：YYYY-MM-DD_分析报告.txt"""
    reports_dir = Path(__file__).parent.parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime('%Y-%m-%d')
    report_file = reports_dir / f'{today}_分析报告.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(f"\n💾 报告已保存: {report_file}")
    return report_file


if __name__ == '__main__':
    data = load_all_data()
    report = generate_report(data)
    save_report(report)
    print(report)
