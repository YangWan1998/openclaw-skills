#!/usr/bin/env python3
"""
使用 OpenClaw AI 进行英文新闻情感分析
调用本地 OpenClaw agent 进行专业金融情感判断
适配英文铜市场新闻
"""

import json
import subprocess
import re
import time
from pathlib import Path


def analyze_sentiment_ai(title, content, max_retries=2):
    """
    使用 OpenClaw AI 分析英文新闻情感
    
    返回: -1.0 到 +1.0 的分数
    -1.0 = 极度利空
     0.0 = 中性
    +1.0 = 极度利好
    """
    
    # 构建英文专业分析提示 - 强制JSON格式返回
    prompt = f"""You are a professional copper market analyst. Analyze the following news and rate its impact on copper prices.

【CRITICAL】Return Format - You MUST return ONLY valid JSON:
{{"score": <integer -10 to +10>, "reason": "<one sentence explanation>"}}

Scoring Criteria (-10 to +10):
-10: Extremely Bearish (crash, collapse, demand destruction, massive oversupply)
 -7: Clearly Bearish (surging inventories, sustained demand decline, strong dollar, recession)
 -5: Bearish (price decline, weak market, soft consumption, oversupply)
 -2: Slightly Bearish (short-term correction, small pullback, profit-taking)
  0: Neutral (pure data release, market consolidation, no clear bias, routine report)
 +2: Slightly Bullish (short-term rebound, small rally, technical recovery)
 +5: Bullish (price increase, improved demand, inventory decline, tight supply)
 +7: Clearly Bullish (supply shortage, strong demand, breakout above key levels, policy stimulus)
+10: Extremely Bullish (new all-time highs, supply crisis, demand explosion, massive infrastructure plans)

Analysis Focus:
- Focus on "opinions", "forecasts", "analysis", and "commentary", NOT just raw data
- Data releases are neutral by themselves; key is the interpretation
- "Analysts forecast/expect/indicate" → judge based on direction of view
- "Strong demand/tight supply" → +5 to +7
- "Weak demand/inventory pressure" → -5 to -7
- "Concern", "caution", "risk" → -2 to -3
- "Expected to", "outlook", "optimistic" → +2 to +4

News Title: {title}
News Content: {content[:1500]}

Return ONLY JSON: {{"score": <integer>, "reason": "<brief>"}}"""

    for attempt in range(max_retries + 1):
        try:
            # 调用 OpenClaw agent
            result = subprocess.run(
                ['openclaw', 'agent', '--agent', 'main', '--message', prompt, '--json', '--local', '--timeout', '30'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"    OpenClaw call failed (attempt {attempt+1}): {result.stderr[:100]}")
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return None
            
            # 解析 JSON 输出
            try:
                response = json.loads(result.stdout)
                text_response = ''
                if 'payloads' in response and len(response['payloads']) > 0:
                    text_response = response['payloads'][0].get('text', '')
                else:
                    text_response = response.get('text', '') or response.get('content', '') or response.get('message', '')
                
                # 尝试从JSON格式提取
                score = extract_score_json(text_response)
                if score is not None:
                    return score / 10.0  # 归一化到 [-1, 1]
                
                # 回退到正则提取
                score = extract_score(text_response)
                if score is not None:
                    return score / 10.0
                
            except json.JSONDecodeError:
                # 如果不是 JSON，直接解析文本
                score = extract_score(result.stdout)
                if score is not None:
                    return score / 10.0
            
            if attempt < max_retries:
                print(f"    Retrying... ({attempt+1}/{max_retries})")
                time.sleep(1)
                continue
            
            return None
            
        except Exception as e:
            print(f"    AI analysis failed (attempt {attempt+1}): {e}")
            if attempt < max_retries:
                time.sleep(1)
                continue
            return None
    
    return None


def extract_score_json(text):
    """从JSON格式响应中提取分数"""
    if not text:
        return None
    
    try:
        # 尝试直接解析JSON
        data = json.loads(text)
        if 'score' in data:
            score = int(data['score'])
            if -10 <= score <= 10:
                return score
    except (json.JSONDecodeError, ValueError):
        pass
    
    # 尝试从文本中提取JSON对象
    json_pattern = r'\{[^}]*"score"[^}]*\}'
    matches = re.findall(json_pattern, text)
    for match in matches:
        try:
            data = json.loads(match)
            if 'score' in data:
                score = int(data['score'])
                if -10 <= score <= 10:
                    return score
        except (json.JSONDecodeError, ValueError):
            continue
    
    return None


def extract_score(text):
    """从 AI 响应中提取分数（正则回退）"""
    if not text:
        return None
    
    # 清理文本
    text = text.strip()
    
    # 尝试匹配 -10 到 +10 的数字（更严格的模式）
    patterns = [
        r'"score"\s*:\s*([-+]?\d+)',  # JSON格式 "score": 5
        r'score\s*[:=]\s*([-+]?\d+)',  # score: 5 或 score=5
        r'rating\s*[:=]\s*([-+]?\d+)',  # rating: 5
        r'(?:^|\s|[:=])([-+]?\d{1,2})(?:\s|$|\.)',  # 独立的1-2位数字
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                score = int(match)
                if -10 <= score <= 10:
                    return score
            except ValueError:
                continue
    
    return None


def batch_analyze_sentiment_ai(news_list, max_batch_size=8):
    """
    真正的批量AI分析 - 一次把多条新闻打包给AI，减少进程启动开销
    
    原理：启动1次AI进程分析多条新闻，而不是每条新闻启动1次
    
    news_list: [{title, content}, ...] (已按日期排序，最新的在前)
    max_batch_size: 最大分析数量（默认8条，控制prompt长度避免LLM截断）
    返回: [{title, content, sentiment_score, sentiment}, ...]
    """
    results = []
    
    # 限制分析数量（优先分析最新的）
    analyze_list = news_list[:max_batch_size]
    pending_list = news_list[max_batch_size:]
    
    print(f"  🚀 批量AI分析 {len(analyze_list)} 条新闻（共{len(news_list)}条，优先分析最新的{max_batch_size}条）...")
    print(f"     💡 一次启动AI进程分析{len(analyze_list)}条，避免重复启动开销")
    
    # 构建批量分析提示 - 清理新闻内容中的特殊字符，避免污染JSON
    def clean_text(text):
        """清理文本中的特殊字符，避免破坏JSON格式"""
        if not text:
            return ""
        # 替换双引号为单引号
        text = text.replace('"', "'")
        # 替换反斜杠
        text = text.replace('\\', '/')
        # 替换换行为空格
        text = text.replace('\n', ' ').replace('\r', ' ')
        # 替换大括号（避免AI混淆）
        text = text.replace('{', '[').replace('}', ']')
        # 压缩多余空格
        text = ' '.join(text.split())
        return text[:250]  # 限制长度，控制总prompt大小
    
    news_text = ""
    for i, news in enumerate(analyze_list, 1):
        title = clean_text(news['title'])
        content = clean_text(news.get('summary', news.get('content', '')))
        news_text += f"\n--- News {i} ---\n"
        news_text += f"Title: {title}\n"
        news_text += f"Content: {content}\n"
    
    prompt = f"""You are a professional copper market analyst. Analyze the following {len(analyze_list)} news items and rate each one's impact on copper prices.

【CRITICAL】Return Format - You MUST return ONLY a valid JSON array. No markdown, no explanation, just raw JSON:
[{{"index": 1, "score": <integer -10 to +10>, "reason": "<brief>"}}, ...]

Scoring Criteria (-10 to +10):
-10: Extremely Bearish (crash, collapse, demand destruction)
 -7: Clearly Bearish (surging inventories, sustained demand decline)
 -5: Bearish (price decline, weak market, oversupply)
 -3: Bearish-Trend (forecast decline, price expected to fall, lower target)
 -1: Slightly Bearish (short-term correction, minor pullback)
  0: Neutral (pure data, no clear bias, routine report)
 +1: Slightly Bullish (short-term rebound, minor recovery)
 +3: Bullish-Trend (forecast raise, price expected to rise, higher target, upgrade)
 +5: Bullish (price increase, improved demand, inventory decline)
 +7: Clearly Bullish (supply shortage, strong demand)
+10: Extremely Bullish (new all-time highs, supply crisis)

Analysis Focus:
- Focus on "opinions", "forecasts", "analysis", NOT just raw data
- Data releases are neutral; key is the interpretation
- KEY RULE: "Raises forecast/upgrade outlook/higher target" → +3 to +5 (bullish)
- KEY RULE: "Decline from highs/lower prices/price fall expected" → -3 to -5 (bearish)
- "Strong demand/tight supply" → +5 to +7
- "Weak demand/inventory pressure" → -5 to -7
- "Supply disruption/strike/mine closure" → +3 to +5
- "Oversupply/glut/inventory build" → -3 to -5

{news_text}

Return ONLY JSON array: [{{"index": 1, "score": <int>, "reason": "<brief>"}}, ...]"""

    # 调用一次AI分析所有新闻
    scores_map = {}
    try:
        print(f"     🤖 启动AI批量分析（{len(analyze_list)}条）...")
        result = subprocess.run(
            ['openclaw', 'agent', '--agent', 'main', '--message', prompt, '--json', '--local', '--timeout', '120'],
            capture_output=True,
            text=True,
            timeout=150
        )
        
        if result.returncode == 0:
            # 解析JSON响应
            try:
                response = json.loads(result.stdout)
                text_response = ''
                if 'payloads' in response and len(response['payloads']) > 0:
                    text_response = response['payloads'][0].get('text', '')
                else:
                    text_response = response.get('text', '') or response.get('content', '') or response.get('message', '')
                
                # 尝试解析JSON数组 - 多层容错
                parsed = False
                
                # 方法1: 直接提取JSON数组
                try:
                    array_match = re.search(r'\[.*\]', text_response, re.DOTALL)
                    if array_match:
                        json_str = array_match.group()
                        # 预处理：修复常见JSON错误
                        json_str = json_str.replace("'", '"')  # 单引号转双引号
                        # 修复reason字段中的未转义双引号（如 "reason": "..."xxx"..."）
                        # 使用更安全的修复：先提取所有 {"index":N,"score":M,"reason":"..."} 对象
                        object_pattern = r'\{\s*"index"\s*:\s*(\d+)\s*,\s*"score"\s*:\s*([-+]?\d+)\s*\}'
                        simple_matches = re.findall(object_pattern, json_str)
                        for idx_str, score_str in simple_matches:
                            idx = int(idx_str)
                            score = int(score_str)
                            if 1 <= idx <= len(analyze_list) and -10 <= score <= 10:
                                scores_map[idx] = score / 10.0
                        if len(scores_map) > 0:
                            parsed = True
                            print(f"     ✅ 方法1成功: AI返回了 {len(scores_map)}/{len(analyze_list)} 条结果")
                        else:
                            # 尝试完整解析（如果简单提取失败）
                            analysis_results = json.loads(json_str)
                            for item in analysis_results:
                                idx = item.get('index', 0)
                                score = item.get('score', 0)
                                if 1 <= idx <= len(analyze_list) and -10 <= score <= 10:
                                    scores_map[idx] = score / 10.0
                            if len(scores_map) > 0:
                                parsed = True
                                print(f"     ✅ 方法1成功: AI返回了 {len(scores_map)}/{len(analyze_list)} 条结果")
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"     ⚠️  方法1(JSON数组)失败: {e}")
                
                # 方法2: 用正则逐条提取 index 和 score
                if not parsed:
                    try:
                        # 匹配 "index":数字 和 "score":数字
                        pattern = r'"index"\s*:\s*(\d+).*?"score"\s*:\s*([-+]?\d+)'
                        matches = re.findall(pattern, text_response, re.DOTALL)
                        for idx_str, score_str in matches:
                            idx = int(idx_str)
                            score = int(score_str)
                            if 1 <= idx <= len(analyze_list) and -10 <= score <= 10:
                                scores_map[idx] = score / 10.0
                        if len(scores_map) > 0:
                            parsed = True
                            print(f"     ✅ 方法2(正则提取)成功: 提取了 {len(scores_map)}/{len(analyze_list)} 条结果")
                    except Exception as e:
                        print(f"     ⚠️  方法2(正则提取)失败: {e}")
                
                # 方法3: 更宽松的模式 - 找数字对
                if not parsed:
                    try:
                        # 找所有类似 "1": -5 或 1: -5 的模式
                        pattern = r'(?:"index"\s*[:=]\s*)?(\d+)\s*[:\n]\s*["\']?([-+]?\d+)'
                        matches = re.findall(pattern, text_response)
                        for idx_str, score_str in matches[:len(analyze_list)]:
                            idx = int(idx_str)
                            score = int(score_str)
                            if 1 <= idx <= len(analyze_list) and -10 <= score <= 10:
                                scores_map[idx] = score / 10.0
                        if len(scores_map) > 0:
                            parsed = True
                            print(f"     ✅ 方法3(宽松匹配)成功: 提取了 {len(scores_map)}/{len(analyze_list)} 条结果")
                    except Exception as e:
                        print(f"     ⚠️  方法3(宽松匹配)失败: {e}")
                
                if not parsed:
                    print(f"     ❌ 所有解析方法均失败，AI原始响应前200字符: {text_response[:200]}")
            except json.JSONDecodeError:
                print(f"     ⚠️  响应解析失败")
        else:
            print(f"     ❌ AI调用失败: {result.stderr[:100]}")
    except Exception as e:
        print(f"     ❌ 批量分析异常: {e}")
    
    # 应用分析结果
    for i, news in enumerate(analyze_list, 1):
        days_old = news.get('days_old', 0)
        date_info = f"今天" if days_old == 0 else f"{days_old}天前"
        
        if i in scores_map:
            score = scores_map[i]
            news['sentiment_score'] = round(score, 2)
            news['sentiment'] = score_to_label(score)
            emoji = score_to_emoji(score)
            print(f"    ✅ {i}/{len(analyze_list)} [{date_info}] {emoji} {news['title'][:40]}... ({news['sentiment']}: {score:.2f})")
        else:
            # AI没返回这条，用中性
            news['sentiment_score'] = 0.0
            news['sentiment'] = 'neutral'
            print(f"    ⚠️  {i}/{len(analyze_list)} [{date_info}] ➡️ {news['title'][:40]}... (AI未返回，设为中性)")
        
        results.append(news)
    
    # 未分析的新闻标记为 pending
    for news in pending_list:
        news['sentiment_score'] = 0.0
        news['sentiment'] = 'pending'
        results.append(news)
    
    return results


def batch_analyze_sentiment(news_list, max_batch_size=15):
    """
    批量分析新闻情感 - 使用真正的批量AI分析
    
    这是对外接口，内部调用 batch_analyze_sentiment_ai 实现一次性批量分析
    """
    return batch_analyze_sentiment_ai(news_list, max_batch_size)


def score_to_label(score):
    """将分数转换为标签"""
    if score is None:
        return 'neutral'
    if score >= 0.1:
        return 'positive'
    elif score <= -0.1:
        return 'negative'
    else:
        return 'neutral'


def score_to_emoji(score):
    """分数转表情"""
    if score >= 0.5:
        return '📈📈'
    elif score >= 0.1:
        return '📈'
    elif score <= -0.5:
        return '📉📉'
    elif score <= -0.1:
        return '📉'
    else:
        return '➡️'


if __name__ == '__main__':
    # 测试英文新闻
    test_cases = [
        {
            'title': 'Copper prices surge to record highs on strong demand from EV sector',
            'content': 'Copper prices hit new all-time highs today as electric vehicle demand continues to outpace supply. Analysts at Goldman Sachs raised their price targets.'
        },
        {
            'title': 'Copper market faces oversupply concerns as Chinese demand weakens',
            'content': 'Analysts warn that copper prices may decline further as Chinese consumption slows down and global inventories build up.'
        },
        {
            'title': 'Fed maintains interest rates, copper market reacts cautiously',
            'content': 'The Federal Reserve announced no change in interest rates today. Copper traders remained cautious ahead of the decision.'
        }
    ]
    
    print("=== AI Sentiment Analysis Test (English) ===\n")
    for news in test_cases:
        score = analyze_sentiment_ai(news['title'], news['content'])
        label = score_to_label(score) if score else 'unknown'
        emoji = score_to_emoji(score) if score is not None else '➡️'
        print(f"{emoji} {news['title']}")
        print(f"   Score: {score:.2f} ({label})\n")
