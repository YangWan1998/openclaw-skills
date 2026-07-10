#!/usr/bin/env python3
"""
搜索铜相关新闻 - 使用 Tavily 搜索 API + OpenClaw AI 情感分析
每天自动获取真实的铜相关新闻，并使用 AI 进行专业情感判断
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加 tavily-search skill 路径
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/skills/moochmaniac-tavily-search/scripts"))
# 添加当前目录以导入 analyze_sentiment_ai
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_storage import save_news_data

# 导入 AI 情感分析
try:
    from analyze_sentiment_ai import analyze_sentiment_ai, score_to_label, score_to_emoji
    AI_ANALYSIS_AVAILABLE = True
    print("✅ AI 情感分析模块已加载")
except ImportError as e:
    AI_ANALYSIS_AVAILABLE = False
    print(f"⚠️  AI 情感分析模块不可用: {e}")
    print("   将使用备用关键词分析")

try:
    from search import search_tavily
except ImportError:
    print("错误：无法导入 Tavily 搜索模块")
    print("请确保 moochmaniac-tavily-search skill 已安装")
    sys.exit(1)


def extract_date_from_content(text):
    """从文本中提取真实发布日期"""
    import re
    from datetime import datetime
    
    if not text:
        return None
    
    # 常见日期格式模式
    patterns = [
        # 2026-07-02 或 2026/07/02
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
        # July 2, 2026 或 Jul 2, 2026
        r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\.\s]+(\d{1,2})[,\s]+(\d{4})',
        # 2 July 2026
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[,\s]+(\d{4})',
        # 2026年7月2日
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',
    ]
    
    month_map = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                if len(match) == 3:
                    # 判断是哪种格式
                    if match[0].isdigit() and len(match[0]) == 4:
                        # 2026-07-02 格式
                        year, month, day = int(match[0]), int(match[1]), int(match[2])
                    elif match[0].isdigit():
                        # 2 July 2026 格式
                        day, month_str, year = int(match[0]), match[1].lower(), int(match[2])
                        month = month_map.get(month_str, 0)
                    else:
                        # July 2, 2026 格式
                        month_str, day, year = match[0].lower(), int(match[1]), int(match[2])
                        month = month_map.get(month_str, 0)
                    
                    if month > 0 and 1 <= day <= 31 and year >= 2020:
                        return f"{year:04d}-{month:02d}-{day:02d}"
            except:
                continue
    
    return None


def analyze_sentiment(title, content):
    """分析新闻情感 - 统一使用AI分析
    
    返回: (label, score)
    - label: 'positive', 'negative', 'neutral'
    - score: -1.0 到 +1.0
    """
    if AI_ANALYSIS_AVAILABLE:
        print(f"    🤖 调用 AI 分析...")
        score = analyze_sentiment_ai(title, content)
        if score is not None:
            label = score_to_label(score)
            print(f"    ✅ AI 得分: {score:.2f} ({label})")
            return label, score
        else:
            print(f"    ⚠️  AI 分析失败，使用中性")
    
    # AI 不可用或失败，返回中性
    return 'neutral', 0.0


def search_copper_news():
    """搜索铜相关新闻"""
    
    # 获取最近三天的日期
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    
    # 搜索查询词 - 全部英文，提高搜索质量
    queries = [
        # 铜价核心动态
        f"copper price LME COMEX market news {date_str}",
        f"copper price analysis forecast today",
        f"LME copper price outlook commentary",
        # 供需与库存
        f"copper supply demand deficit inventory",
        f"LME copper warehouse stock level",
        f"copper mine production strike Chile Peru",
        # 宏观影响
        f"Fed interest rate decision copper impact",
        f"US dollar copper price correlation",
        f"China copper demand economy",
        # 行业应用
        f"electric vehicle copper demand EV",
        f"renewable energy copper consumption",
        f"AI data center copper usage",
        # 机构观点
        f"Goldman Sachs copper price forecast",
        f"Citi copper market outlook",
        f"Morgan Stanley copper analysis",
    ]
    
    # 排除的关键词（过滤数据页面和低质量内容）
    exclude_keywords = [
        # 中文数据页面
        '历史数据', '行情中心', '实时行情', '走势图', '行情报价',
        '期货一手保证金', 'k线图', '分时图', '历史行情',
        '行情数据', '价格表', '行情快讯', '行情回顾',
        'futures main sina', '行情中心_东方财富', '行情走势图',
        '铜期货历史数据', '铜- 物价- 图表- 历史数据',
        # 英文数据页面
        'historical data', 'price chart', 'real-time quote',
        'futures main', 'market data', 'price table',
        'k-line', 'intraday chart', 'tradingview',
        'investing.com', 'chart analysis', 'technical indicator',
        'yahoo finance', 'marketwatch', 'bloomberg.com/quote',
    ]
    
    all_news = []
    
    for query in queries:
        print(f"\n🔍 搜索: {query}")
        try:
            result = search_tavily(
                query=query,
                max_results=3,
                search_depth="advanced",
                include_answer=False
            )
            
            if "error" in result:
                print(f"  ❌ 搜索失败: {result['error']}")
                continue
            
            for item in result.get("results", []):
                title = item.get("title", "")
                content = item.get("content", "")
                
                # 尝试提取真实发布日期
                pub_date = extract_date_from_content(title + ' ' + content)
                
                news_item = {
                    'title': title,
                    'source': item.get("url", "").split("/")[2] if item.get("url") else "未知来源",
                    'url': item.get("url", ""),
                    'date': pub_date or datetime.now().strftime('%Y-%m-%d'),
                    'summary': content[:800] + "..." if len(content) > 800 else content,
                    'score': item.get("score", 0),
                    'sentiment': 'pending',  # 待分析
                    'sentiment_score': 0.0
                }
                
                # 过滤：排除数据页面
                is_data_page = any(kw in title for kw in exclude_keywords)
                if is_data_page:
                    print(f"  🚫 过滤数据页面: {title[:50]}...")
                    continue
                
                # 去重：检查是否已存在相同标题
                if not any(n['title'] == news_item['title'] for n in all_news):
                    all_news.append(news_item)
                    print(f"  ⏳ {title[:60]}...")
                
        except Exception as e:
            print(f"  ❌ 搜索出错: {e}")
            continue
    
    # 过滤：基于提取的真实日期，过滤掉3个月以上的旧闻
    from datetime import timedelta
    
    recent_news = []
    old_news = []
    cutoff_date = today - timedelta(days=90)  # 3个月 cutoff
    
    for news in all_news:
        news_date_str = news.get('date', '')
        try:
            news_date = datetime.strptime(news_date_str, '%Y-%m-%d')
            if news_date >= cutoff_date:
                news['news_date'] = news_date  # 保存解析后的日期对象
                news['days_old'] = (today - news_date).days
                recent_news.append(news)
            else:
                news['is_old'] = True
                old_news.append(news)
        except:
            # 日期解析失败，默认保留并当作当天
            news['news_date'] = today
            news['days_old'] = 0
            recent_news.append(news)
    
    # 按日期排序：越新的越靠前
    recent_news.sort(key=lambda x: x.get('news_date', today), reverse=True)
    
    print(f"\n📅 新闻时间分布:")
    print(f"   当天(0天): {sum(1 for n in recent_news if n.get('days_old', 0) == 0)} 条")
    print(f"   1-7天: {sum(1 for n in recent_news if 1 <= n.get('days_old', 0) <= 7)} 条")
    print(f"   8-30天: {sum(1 for n in recent_news if 8 <= n.get('days_old', 0) <= 30)} 条")
    print(f"   31-90天: {sum(1 for n in recent_news if 31 <= n.get('days_old', 0) <= 90)} 条")
    print(f"   旧闻(>90天): {len(old_news)} 条")
    
    # 计算时间衰减权重
    def get_time_weight(days_old):
        """时间衰减权重：当天1.0、1周0.8、1月0.5、3月0.2"""
        if days_old == 0:
            return 1.0
        elif days_old <= 7:
            return 0.8
        elif days_old <= 30:
            return 0.5
        else:
            return 0.2
    
    for news in recent_news:
        news['time_weight'] = get_time_weight(news.get('days_old', 0))
    
    # 分析策略：使用真正的批量AI分析（一次分析多条，减少进程开销）
    news_to_analyze = recent_news
    
    if news_to_analyze:
        print(f"\n🤖 开始 AI 情感分析（批量模式：一次分析多条新闻）...")
        
        if AI_ANALYSIS_AVAILABLE:
            from analyze_sentiment_ai import batch_analyze_sentiment
            # 使用批量分析：一次AI调用分析多条新闻
            analyzed_results = batch_analyze_sentiment(news_to_analyze, max_batch_size=15)
            
            # 显示分析结果
            analyzed_count = 0
            for news in analyzed_results:
                if news.get('sentiment') == 'pending':
                    continue
                emoji = score_to_emoji(news['sentiment_score'])
                weight_info = f"权重{news.get('time_weight', 1.0):.1f}x"
                print(f"  ✅ {emoji} [{weight_info}] {news['title'][:45]}... ({news['sentiment']}: {news['sentiment_score']:.2f})")
                analyzed_count += 1
            
            pending_count = sum(1 for n in analyzed_results if n.get('sentiment') == 'pending')
            if pending_count > 0:
                print(f"  ⏭️  {pending_count} 条新闻未分析（超出限制）")
            print(f"\n📊 批量分析完成：{analyzed_count}条已分析，{pending_count}条待处理")
        else:
            # AI不可用，逐条使用关键词分析
            for i, news in enumerate(news_to_analyze[:10], 1):
                print(f"  {i}/{min(10, len(news_to_analyze))}: {news['title'][:50]}...")
                sentiment, sentiment_score = analyze_sentiment(news['title'], news['summary'])
                
                news['sentiment'] = sentiment
                news['sentiment_score'] = round(sentiment_score, 2)
                
                emoji = {'positive': '📈', 'negative': '📉', 'neutral': '➡️'}.get(sentiment, '➡️')
                print(f"     {emoji} {sentiment} ({sentiment_score:.2f})")
            
            for news in news_to_analyze[10:]:
                news['sentiment'] = 'pending'
                news['sentiment_score'] = 0.0
    else:
        print("⚠️ 没有找到可分析的新闻")
    
    # 旧闻标记
    for news in old_news:
        news['sentiment'] = 'old_news'
        news['sentiment_score'] = 0.0
        news['time_weight'] = 0.0
    
    # 合并：recent_news + old_news
    all_news = recent_news + old_news
    
    return {
        'timestamp': datetime.now().isoformat(),
        'news_count': len(all_news),
        'recent_news_count': len(recent_news),
        'news': all_news
    }


def save_news(news_data):
    """保存新闻数据到CSV（使用data_storage模块）"""
    filepath = save_news_data(news_data)
    print(f"\n💾 新闻数据已保存CSV: {filepath}")
    print(f"   共 {news_data['news_count']} 条新闻")
    
    # 统计情感分布（考虑时间权重）
    sentiments = {'positive': 0, 'negative': 0, 'neutral': 0, 'old_news': 0, 'pending': 0}
    weighted_score = 0
    total_weight = 0
    analyzed_count = 0
    
    for news in news_data['news']:
        sentiment = news['sentiment']
        sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        if sentiment not in ['old_news', 'pending']:
            analyzed_count += 1
            weight = news.get('time_weight', 1.0)
            weighted_score += news.get('sentiment_score', 0) * weight
            total_weight += weight
    
    # 加权平均情感得分
    avg_score = weighted_score / total_weight if total_weight > 0 else 0
    
    print(f"📊 情感分布: 正面{sentiments.get('positive', 0)} 负面{sentiments.get('negative', 0)} 中性{sentiments.get('neutral', 0)} 旧闻{sentiments.get('old_news', 0)} 待分析{sentiments.get('pending', 0)}")
    print(f"📈 加权平均情感得分: {avg_score:.2f}（基于{analyzed_count}条已分析新闻，总权重{total_weight:.1f}）")
    
    if avg_score > 0.2:
        print("💡 整体情绪: 看涨")
    elif avg_score < -0.2:
        print("💡 整体情绪: 看跌")
    else:
        print("💡 整体情绪: 中性")


if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"🚀 开始搜索铜相关新闻... {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    
    news_data = search_copper_news()
    save_news(news_data)
    
    print(f"\n{'='*60}")
    print("📰 新闻列表（前10条）")
    print(f"{'='*60}")
    
    for i, news in enumerate(news_data['news'][:10], 1):
        if AI_ANALYSIS_AVAILABLE:
            emoji = score_to_emoji(news.get('sentiment_score', 0))
        else:
            emoji = {'positive': '📈', 'negative': '📉', 'neutral': '➡️', 'old_news': '📰', 'pending': '⏳'}.get(news['sentiment'], '➡️')
        
        # 显示日期和权重信息
        days_old = news.get('days_old', 0)
        weight = news.get('time_weight', 1.0)
        if news.get('sentiment') == 'old_news':
            date_info = f"📅 {news['date']} (旧闻)"
        elif news.get('sentiment') == 'pending':
            date_info = f"📅 {news['date']} (未分析)"
        else:
            date_info = f"📅 {news['date']} ({days_old}天前, 权重{weight:.1f}x)"
        
        print(f"\n{i}. {emoji} {news['title']}")
        print(f"   📍 来源: {news['source']} | {date_info}")
        print(f"   📊 情感: {news['sentiment']} ({news.get('sentiment_score', 0):.2f})")
        print(f"   📝 摘要: {news['summary'][:100]}...")
    
    print(f"\n{'='*60}")
    print("✅ 新闻搜索和情感分析完成")
    print(f"{'='*60}")
