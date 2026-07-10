#!/usr/bin/env python3
"""
测试 AI 情感分析 - 单条测试
"""

import sys
sys.path.insert(0, '/Users/yang/.openclaw/workspace/skills/copper-price-predictor/scripts')

from analyze_sentiment_ai import analyze_sentiment_ai, score_to_label, score_to_emoji

# 测试用例
test_cases = [
    {
        'title': '铜价暴涨！需求强劲推动价格创历史新高',
        'content': '今日铜价大幅上涨，受新能源需求爆发和供应短缺影响，LME铜价突破10000美元/吨。'
    },
    {
        'title': '铜价不会上涨，市场预计继续走弱',
        'content': '分析师表示，由于全球经济放缓，铜价短期内不会上涨，预计将继续在低位震荡。'
    },
    {
        'title': '美联储维持利率不变',
        'content': '美联储今日宣布维持基准利率不变，符合市场预期。'
    },
    {
        'title': '库存6连增消费疲软 现货升水走低',
        'content': '【SMM华南铜现货】库存连续6周增加，消费端疲软，现货升水持续走低。'
    }
]

print("=== AI 情感分析测试 ===\n")

for i, news in enumerate(test_cases, 1):
    print(f"{i}. 分析: {news['title'][:50]}...")
    score = analyze_sentiment_ai(news['title'], news['content'])
    
    if score is not None:
        label = score_to_label(score)
        emoji = score_to_emoji(score)
        print(f"   {emoji} 得分: {score:.2f} ({label})")
    else:
        print(f"   ❌ 分析失败")
    print()

print("测试完成!")
