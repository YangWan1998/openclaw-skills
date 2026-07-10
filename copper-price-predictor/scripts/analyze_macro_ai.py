#!/usr/bin/env python3
"""
使用 OpenClaw AI 进行宏观因子分析
对每个宏观因子打分（-10 到 +10），并给出对铜价的综合影响评估
"""

import json
import subprocess
import re
from pathlib import Path


def analyze_macro_factor_ai(indicator_name, indicator_value, context_text=""):
    """
    使用 OpenClaw AI 分析单个宏观因子对铜价的影响
    
    Args:
        indicator_name: 指标名称（如"美元指数", "美国PMI"）
        indicator_value: 指标数值
        context_text: 相关上下文文本（新闻内容等）
    
    Returns:
        dict: {
            'score': -10 到 +10 的整数,
            'impact': 'strong_positive'/'positive'/'neutral'/'negative'/'strong_negative',
            'reasoning': '分析理由'
        }
    """
    
    prompt = f"""你是一位专业的宏观经济学家和铜市场分析师。请分析以下宏观指标对铜价的影响，并给出评分。

【指标名称】: {indicator_name}
【指标数值】: {indicator_value}
【相关背景】: {context_text[:800] if context_text else "无额外背景信息"}

评分标准（-10 到 +10）：
-10: 极度利空铜价（如：美元暴涨+经济崩盘+库存暴增同时发生）
 -7: 明显利空（如：美元大幅走强、PMI跌破40、库存创历史高位）
 -5: 利空（如：美元走强、PMI低于50、库存上升）
 -2: 轻微利空（如：美元小幅上涨、PMI略低于预期）
  0: 中性（如：数据符合预期、无明显影响）
 +2: 轻微利好（如：美元小幅走弱、PMI略高于预期）
 +5: 利好（如：美元走弱、PMI高于50、库存下降）
 +7: 明显利好（如：美元大幅走弱、PMI强劲、库存创历史低位）
+10: 极度利好铜价（如：美元暴跌+经济过热+库存枯竭同时发生）

判断规则：
1. 美元指数与铜价通常负相关（美元涨→铜跌，美元跌→铜涨）
2. PMI > 50 表示制造业扩张，利好铜需求
3. 库存下降通常利好铜价，库存上升通常利空
4. 美联储鸽派/宽松政策利好铜价，鹰派/紧缩政策利空

请返回 JSON 格式：
{{
  "score": 整数（-10到+10）,
  "impact": "strong_positive/positive/neutral/negative/strong_negative",
  "reasoning": "简要分析理由（50字以内）"
}}

只返回 JSON，不要其他内容。"""

    try:
        result = subprocess.run(
            ['openclaw', 'agent', '--agent', 'main', '--message', prompt, '--json', '--local', '--timeout', '30'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"OpenClaw 调用失败: {result.stderr}")
            return None
        
        # 解析 JSON 输出
        try:
            response = json.loads(result.stdout)
            text_response = ''
            if 'payloads' in response and len(response['payloads']) > 0:
                text_response = response['payloads'][0].get('text', '')
            else:
                text_response = response.get('text', '') or response.get('content', '') or response.get('message', '')
            
            # 从文本中提取 JSON
            json_match = re.search(r'\{[^}]*"score"[^}]*\}', text_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    'score': int(analysis.get('score', 0)),
                    'impact': analysis.get('impact', 'neutral'),
                    'reasoning': analysis.get('reasoning', '')
                }
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"解析 AI 响应失败: {e}")
            return None
        
        return None
        
    except Exception as e:
        print(f"AI 宏观分析失败: {e}")
        return None


def analyze_all_macro_factors(macro_data):
    """
    批量分析所有宏观因子
    
    Args:
        macro_data: fetch_macro_data.py 返回的宏观数据字典
    
    Returns:
        list: 每个因子的分析结果，包含 score/impact/reasoning
    """
    results = []
    
    print("\n🤖 开始 AI 宏观因子分析...")
    
    for item in macro_data.get('data', []):
        indicator = item.get('indicator', '')
        value = item.get('value', '')
        
        # 跳过库存数据（单独处理）
        if indicator == 'COPPER_INVENTORY':
            continue
        
        # 构建上下文
        context = ""
        if 'status' in item:
            context += f"状态: {item['status']}. "
        if 'policy_stance' in item:
            context += f"政策立场: {item['policy_stance']}. "
        
        print(f"  分析 {indicator}: {value}...")
        
        analysis = analyze_macro_factor_ai(indicator, value, context)
        
        if analysis:
            results.append({
                'indicator': indicator,
                'value': value,
                **analysis
            })
            emoji = "📈" if analysis['score'] > 0 else "📉" if analysis['score'] < 0 else "➡️"
            print(f"    {emoji} 得分: {analysis['score']} ({analysis['impact']}) - {analysis['reasoning']}")
        else:
            # AI 失败，使用简单规则
            score = simple_macro_score(indicator, value, item)
            results.append({
                'indicator': indicator,
                'value': value,
                'score': score,
                'impact': score_to_impact(score),
                'reasoning': 'AI分析失败，使用规则评分'
            })
            print(f"    ⚠️  AI失败，规则评分: {score}")
    
    # 处理库存数据
    for item in macro_data.get('data', []):
        if item.get('indicator') == 'COPPER_INVENTORY':
            for inv in item.get('data', []):
                exchange = inv.get('exchange', '')
                inventory = inv.get('inventory', 0)
                print(f"  分析 {exchange}库存: {inventory:,} 吨...")
                
                # 库存分析：需要历史对比，这里简化处理
                score = analyze_inventory_simple(exchange, inventory)
                results.append({
                    'indicator': f'INVENTORY_{exchange}',
                    'value': inventory,
                    'score': score,
                    'impact': score_to_impact(score),
                    'reasoning': f'{exchange}库存水平分析'
                })
                print(f"    {'📈' if score > 0 else '📉'} 得分: {score}")
    
    return results


def simple_macro_score(indicator, value, item):
    """简单规则评分（AI失败时的备用）"""
    try:
        if indicator == 'USD_INDEX':
            # 美元指数：>100 偏强（利空铜），<95 偏弱（利好铜）
            v = float(value)
            if v > 105: return -7
            elif v > 100: return -4
            elif v > 95: return -1
            elif v > 90: return 3
            else: return 6
            
        elif indicator == 'US_ISM_PMI':
            # PMI: >50 扩张，<50 收缩
            v = float(value)
            if v > 55: return 6
            elif v > 50: return 3
            elif v > 45: return -3
            else: return -6
            
        elif indicator == 'FED_POLICY':
            # 美联储政策
            stance = item.get('policy_stance', 'neutral')
            if stance == 'dovish': return 5
            elif stance == 'hawkish': return -5
            else: return 0
            
    except (ValueError, TypeError):
        pass
    
    return 0


def analyze_inventory_simple(exchange, inventory):
    """简化库存分析（需要历史数据才能准确判断）"""
    # 这里简化处理，实际应该对比历史均值
    # 假设 LME 库存 > 20万吨为高位，< 5万吨为低位
    # COMEX 库存 > 5万吨为高位，< 1万吨为低位
    
    if exchange == 'LME':
        if inventory > 200000: return -5  # 高位
        elif inventory < 50000: return 5   # 低位
        else: return 0
    elif exchange == 'COMEX':
        if inventory > 50000: return -5
        elif inventory < 10000: return 5
        else: return 0
    
    return 0


def score_to_impact(score):
    """分数转影响等级"""
    if score >= 7: return 'strong_positive'
    elif score >= 3: return 'positive'
    elif score <= -7: return 'strong_negative'
    elif score <= -3: return 'negative'
    else: return 'neutral'


def calculate_macro_composite_score(factor_results):
    """
    计算宏观因子综合得分
    
    Args:
        factor_results: analyze_all_macro_factors 的返回结果
    
    Returns:
        dict: {
            'composite_score': 综合得分（-10到+10）,
            'weighted_score': 加权得分,
            'factor_breakdown': 各因子得分明细
        }
    """
    if not factor_results:
        return {'composite_score': 0, 'weighted_score': 0, 'factor_breakdown': []}
    
    # 权重配置
    weights = {
        'USD_INDEX': 0.30,
        'US_ISM_PMI': 0.25,
        'FED_POLICY': 0.25,
        'INVENTORY_LME': 0.10,
        'INVENTORY_COMEX': 0.10
    }
    
    total_weight = 0
    weighted_sum = 0
    breakdown = []
    
    for factor in factor_results:
        indicator = factor['indicator']
        score = factor['score']
        weight = weights.get(indicator, 0.1)  # 默认权重 0.1
        
        weighted_sum += score * weight
        total_weight += weight
        
        breakdown.append({
            'indicator': indicator,
            'score': score,
            'weight': weight,
            'weighted_contribution': round(score * weight, 2)
        })
    
    # 归一化到 -10 到 +10
    if total_weight > 0:
        composite = weighted_sum / total_weight
    else:
        composite = 0
    
    return {
        'composite_score': round(composite, 1),
        'weighted_score': round(weighted_sum, 2),
        'factor_breakdown': breakdown
    }


if __name__ == '__main__':
    # 测试
    test_data = {
        'data': [
            {'indicator': 'USD_INDEX', 'value': 102.5},
            {'indicator': 'US_ISM_PMI', 'value': 48.5, 'status': 'contraction'},
            {'indicator': 'FED_POLICY', 'policy_stance': 'hawkish', 'impact_on_copper': 'negative'}
        ]
    }
    
    print("=== AI 宏观因子分析测试 ===\n")
    results = analyze_all_macro_factors(test_data)
    composite = calculate_macro_composite_score(results)
    
    print(f"\n综合得分: {composite['composite_score']}")
    print("因子分解:")
    for b in composite['factor_breakdown']:
        print(f"  {b['indicator']}: {b['score']} × {b['weight']} = {b['weighted_contribution']}")
