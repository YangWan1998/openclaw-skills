#!/usr/bin/env python3
"""
验证历史预测 - 对比预测价格和实际价格
计算方向准确率、MAE、RMSE，并对错误预测进行AI归因分析
输出CSV格式报告
"""

import json
import csv
import math
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path

# 导入学习日志模块
from learning_manager import (
    append_learning_log,
    generate_weight_adjustment_suggestion,
    generate_weekly_summary,
    get_error_statistics
)


def load_predictions():
    """加载预测历史（CSV格式）"""
    data_dir = Path(__file__).parent.parent / 'data'
    pred_file = data_dir / 'predictions.csv'
    
    predictions = []
    if pred_file.exists():
        with open(pred_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 转换数值字段
                for key in ['current_price', 'sentiment_score', 'technical_score', 
                           'macro_score', 'composite_score', 'confidence']:
                    if row.get(key):
                        try:
                            row[key] = float(row[key])
                        except (ValueError, TypeError):
                            pass
                predictions.append(row)
    return predictions


def load_price_history():
    """加载价格历史（CSV格式）"""
    data_dir = Path(__file__).parent.parent / 'data'
    history_file = data_dir / 'price_history.csv'
    
    history = []
    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 转换数值字段
                for key in ['price', 'change', 'change_percent', 'open', 'high', 'low', 'volume', 'hold']:
                    if row.get(key):
                        try:
                            row[key] = float(row[key]) if key not in ['volume', 'hold'] else int(float(row[key]))
                        except (ValueError, TypeError):
                            pass
                history.append(row)
    return history


def get_actual_price_on_date(price_history, target_date):
    """获取指定日期的实际价格"""
    for record in price_history:
        if record.get('date') == target_date:
            return record.get('price')
    return None


def calculate_direction_accuracy(predictions, price_history, period_days):
    """计算方向准确率"""
    correct = 0
    total = 0
    
    for pred in predictions:
        pred_date = pred.get('date')
        if not pred_date:
            continue
        
        # 计算目标日期
        try:
            pred_dt = datetime.strptime(pred_date, '%Y-%m-%d')
            target_dt = pred_dt + timedelta(days=period_days)
            target_date = target_dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
        
        # 获取预测方向
        direction_key = f'{period_days}d_direction' if period_days <= 5 else f'{period_days//7}w_direction' if period_days <= 7 else '1m_direction'
        predicted_direction = pred.get(direction_key, '')
        
        # 获取实际价格
        pred_price = pred.get('current_price')
        actual_price = get_actual_price_on_date(price_history, target_date)
        
        if pred_price is None or actual_price is None:
            continue
        
        try:
            pred_price = float(pred_price)
            actual_price = float(actual_price)
        except (ValueError, TypeError):
            continue
        
        # 判断实际方向
        actual_direction = 'up' if actual_price > pred_price else 'down' if actual_price < pred_price else 'stable'
        
        # 判断是否一致
        if predicted_direction == actual_direction:
            correct += 1
        total += 1
    
    return round(correct / total, 4) if total > 0 else 0.0, correct, total


def calculate_mae_rmse(predictions, price_history, period_days):
    """计算MAE和RMSE"""
    errors = []
    
    for pred in predictions:
        pred_date = pred.get('date')
        if not pred_date:
            continue
        
        try:
            pred_dt = datetime.strptime(pred_date, '%Y-%m-%d')
            target_dt = pred_dt + timedelta(days=period_days)
            target_date = target_dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
        
        # 获取预测目标价
        target_key = f'{period_days}d_target_price' if period_days <= 5 else f'{period_days//7}w_target_price' if period_days <= 7 else '1m_target_price'
        predicted_price = pred.get(target_key)
        actual_price = get_actual_price_on_date(price_history, target_date)
        
        if predicted_price is None or actual_price is None:
            continue
        
        try:
            predicted_price = float(predicted_price)
            actual_price = float(actual_price)
            error = abs(predicted_price - actual_price)
            errors.append(error)
        except (ValueError, TypeError):
            continue
    
    if not errors:
        return None, None
    
    mae = sum(errors) / len(errors)
    rmse = math.sqrt(sum(e ** 2 for e in errors) / len(errors))
    
    return round(mae, 2), round(rmse, 2)


def ai_error_analysis(prediction, actual_direction, actual_price, price_history):
    """
    使用AI分析预测错误的原因
    
    Args:
        prediction: 预测记录（字典）
        actual_direction: 实际方向
        actual_price: 实际价格
        price_history: 价格历史
    
    Returns:
        dict: {'error_analysis': '分析文本', 'factor_attribution': '因子归因'}
    """
    
    prompt = f"""你是一位专业的铜市场预测分析师。请分析以下预测错误的原因。

【预测信息】
- 预测日期: {prediction.get('date', '未知')}
- 预测时价格: {prediction.get('current_price', '未知')}
- 预测方向: {prediction.get('overall_direction', '未知')}
- 综合评分: {prediction.get('composite_score', '未知')}
- 情绪评分: {prediction.get('sentiment_score', '未知')}
- 技术评分: {prediction.get('technical_score', '未知')}
- 宏观评分: {prediction.get('macro_score', '未知')}
- 权重配置: 舆情{prediction.get('weights_used', {}).get('sentiment', 0.4)} 技术{prediction.get('weights_used', {}).get('technical', 0.35)} 宏观{prediction.get('weights_used', {}).get('macro', 0.25)}

【实际结果】
- 实际方向: {actual_direction}
- 实际价格: {actual_price}

【任务】
1. 分析为什么预测方向错误
2. 指出哪个因子（舆情/技术/宏观）的权重或评分导致了偏差
3. 给出权重调整建议

请用简洁的中文回答（100字以内），格式：
原因：[简要原因]
归因：[哪个因子导致偏差]
建议：[权重调整建议]"""

    try:
        result = subprocess.run(
            ['openclaw', 'agent', '--agent', 'main', '--message', prompt, '--json', '--local', '--timeout', '30'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return {'error_analysis': 'AI分析调用失败', 'factor_attribution': '未知'}
        
        # 解析响应
        try:
            response = json.loads(result.stdout)
            text_response = ''
            if 'payloads' in response and len(response['payloads']) > 0:
                text_response = response['payloads'][0].get('text', '')
            else:
                text_response = response.get('text', '') or response.get('content', '') or response.get('message', '')
            
            # 提取分析结果
            analysis = text_response.strip()
            
            # 提取归因
            attribution = '综合因素'
            if '舆情' in analysis or '情绪' in analysis:
                attribution = '舆情因子'
            elif '技术' in analysis:
                attribution = '技术因子'
            elif '宏观' in analysis:
                attribution = '宏观因子'
            
            return {
                'error_analysis': analysis[:200],  # 限制长度
                'factor_attribution': attribution
            }
            
        except (json.JSONDecodeError, ValueError):
            return {'error_analysis': 'AI响应解析失败', 'factor_attribution': '未知'}
    
    except Exception as e:
        return {'error_analysis': f'AI分析异常: {str(e)}', 'factor_attribution': '未知'}


def generate_validation_report():
    """生成验证报告"""
    predictions = load_predictions()
    price_history = load_price_history()
    
    print("=" * 60)
    print("📊 预测验证报告")
    print("=" * 60)
    
    if not predictions:
        print("\n暂无预测记录")
        return None
    
    if not price_history:
        print("\n暂无价格历史记录，无法验证")
        return None
    
    print(f"\n总预测次数: {len(predictions)}")
    print(f"价格记录数: {len(price_history)}")
    
    # 计算各时间窗口的指标
    results = {}
    detailed_records = []
    
    for period_name, period_days in [('5d', 5), ('1w', 7), ('1m', 30)]:
        print(f"\n{'='*40}")
        print(f"📅 时间窗口: {period_name} ({period_days}天)")
        print(f"{'='*40}")
        
        # 方向准确率
        accuracy, correct, total = calculate_direction_accuracy(predictions, price_history, period_days)
        results[f'direction_accuracy_{period_name}'] = accuracy
        print(f"方向准确率: {accuracy*100:.1f}% ({correct}/{total})")
        
        # MAE和RMSE
        mae, rmse = calculate_mae_rmse(predictions, price_history, period_days)
        results[f'mae_{period_name}'] = mae
        results[f'rmse_{period_name}'] = rmse
        if mae is not None:
            print(f"MAE: {mae}")
            print(f"RMSE: {rmse}")
        else:
            print("MAE/RMSE: 数据不足，无法计算")
    
    # 平均置信度
    total_confidence = 0
    for pred in predictions:
        try:
            total_confidence += float(pred.get('confidence', 0))
        except (ValueError, TypeError):
            pass
    avg_confidence = total_confidence / len(predictions) if predictions else 0
    results['avg_confidence'] = round(avg_confidence, 4)
    print(f"\n平均置信度: {avg_confidence*100:.1f}%")
    
    # 置信度校准（准确率 vs 置信度）
    # 如果置信度高但准确率低，说明模型过度自信
    avg_accuracy = sum(results.get(f'direction_accuracy_{p}', 0) for p in ['5d', '1w', '1m']) / 3
    calibration = avg_accuracy - avg_confidence
    results['confidence_calibration'] = round(calibration, 4)
    print(f"置信度校准: {calibration:+.2f} (正值=模型偏保守, 负值=模型过度自信)")
    
    # AI错误归因分析（对预测错误的记录）
    print(f"\n{'='*40}")
    print("🤖 AI 错误归因分析")
    print(f"{'='*40}")
    
    error_count = 0
    for pred in predictions[-10:]:  # 只分析最近10条
        pred_date = pred.get('date')
        if not pred_date:
            continue
        
        # 检查5天预测
        try:
            pred_dt = datetime.strptime(pred_date, '%Y-%m-%d')
            target_dt = pred_dt + timedelta(days=5)
            target_date = target_dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
        
        pred_price = pred.get('current_price')
        actual_price = get_actual_price_on_date(price_history, target_date)
        predicted_direction = pred.get('5d_direction', '')
        
        if pred_price is None or actual_price is None:
            continue
        
        try:
            pred_price = float(pred_price)
            actual_price = float(actual_price)
        except (ValueError, TypeError):
            continue
        
        actual_direction = 'up' if actual_price > pred_price else 'down' if actual_price < pred_price else 'stable'
        
        # 如果预测错误，进行AI分析
        if predicted_direction != actual_direction and predicted_direction != '':
            error_count += 1
            print(f"\n  错误 #{error_count}: {pred_date} 预测{predicted_direction} 实际{actual_direction}")
            
            analysis = ai_error_analysis(pred, actual_direction, actual_price, price_history)
            print(f"  分析: {analysis['error_analysis'][:80]}...")
            print(f"  归因: {analysis['factor_attribution']}")
            
            detailed_records.append({
                'date': pred_date,
                'predicted_direction': predicted_direction,
                'actual_direction': actual_direction,
                'direction_correct': False,
                'predicted_price': pred.get('5d_target_price', ''),
                'actual_price': actual_price,
                'price_error': round(abs(actual_price - pred_price), 2),
                'sentiment_score': pred.get('sentiment_score', ''),
                'technical_score': pred.get('technical_score', ''),
                'macro_score': pred.get('macro_score', ''),
                'error_analysis': analysis['error_analysis'],
                'factor_attribution': analysis['factor_attribution']
            })
        elif predicted_direction == actual_direction and predicted_direction != '':
            # 预测正确也记录
            detailed_records.append({
                'date': pred_date,
                'predicted_direction': predicted_direction,
                'actual_direction': actual_direction,
                'direction_correct': True,
                'predicted_price': pred.get('5d_target_price', ''),
                'actual_price': actual_price,
                'price_error': round(abs(actual_price - pred_price), 2),
                'sentiment_score': pred.get('sentiment_score', ''),
                'technical_score': pred.get('technical_score', ''),
                'macro_score': pred.get('macro_score', ''),
                'error_analysis': '预测正确',
                'factor_attribution': '无'
            })
    
    if error_count == 0:
        print("\n  ✅ 最近10条预测中未发现明显错误")
    
    # 汇总报告数据
    report_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'total_predictions': len(predictions),
        'validated_predictions': len([r for r in detailed_records if r.get('actual_price')]),
        **results
    }
    
    # 保存CSV报告
    summary_path, detail_path = save_validation_report(report_data, detailed_records)
    
    # 保存到学习日志
    save_to_learning_log(detailed_records)
    
    # 生成权重调整建议
    suggestion = generate_and_print_suggestion()
    
    # 生成本周总结
    print(f"\n{'='*60}")
    print("📊 本周错误归因统计")
    print(f"{'='*60}")
    print(generate_weekly_summary())
    
    return report_data


def save_validation_report(report_data, detailed_records):
    """保存验证报告到CSV"""
    from data_storage import save_validation_report as save_val_csv
    
    summary_path, detail_path = save_val_csv(report_data, detailed_records)
    
    print(f"\n{'='*60}")
    print("💾 验证报告已保存")
    print(f"{'='*60}")
    print(f"汇总报告: {summary_path}")
    if detail_path:
        print(f"详细报告: {detail_path}")
    
    return summary_path, detail_path


def save_to_learning_log(detailed_records):
    """保存验证结果到学习日志"""
    if not detailed_records:
        return
    
    print(f"\n{'='*60}")
    print("📝 保存学习日志")
    print(f"{'='*60}")
    
    saved_count = 0
    for record in detailed_records:
        # 转换为学习日志格式
        log_record = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'prediction_date': record.get('date', ''),
            'period': '5d',  # 当前主要验证5天
            'predicted_direction': record.get('predicted_direction', ''),
            'actual_direction': record.get('actual_direction', ''),
            'direction_correct': 'True' if record.get('direction_correct') else 'False',
            'predicted_price': record.get('predicted_price', ''),
            'actual_price': record.get('actual_price', ''),
            'price_error': record.get('price_error', ''),
            'sentiment_score': record.get('sentiment_score', ''),
            'technical_score': record.get('technical_score', ''),
            'macro_score': record.get('macro_score', ''),
            'composite_score': '',  # 可从predictions.csv补充
            'error_analysis': record.get('error_analysis', ''),
            'factor_attribution': record.get('factor_attribution', ''),
            'weight_adjustment_suggestion': '',  # 后续补充
            'validated': 'True',
            'validation_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        append_learning_log(log_record)
        saved_count += 1
    
    print(f"✅ 已保存 {saved_count} 条学习记录到 data/learning_log.csv")


def generate_and_print_suggestion():
    """生成并打印权重调整建议"""
    print(f"\n{'='*60}")
    print("💡 权重调整建议")
    print(f"{'='*60}")
    
    suggestion = generate_weight_adjustment_suggestion()
    
    print(f"\n当前权重:")
    print(f"  舆情: {suggestion['current_weights']['sentiment']:.2f}")
    print(f"  技术: {suggestion['current_weights']['technical']:.2f}")
    print(f"  宏观: {suggestion['current_weights']['macro']:.2f}")
    
    print(f"\n最近7天统计:")
    stats_7d = suggestion['statistics_7d']
    print(f"  验证记录: {stats_7d['total_validated']} 条")
    print(f"  错误次数: {stats_7d['total_errors']} 次")
    print(f"  错误率: {stats_7d['error_rate']*100:.1f}%")
    
    if stats_7d['attribution_counts']:
        print(f"\n  错误归因:")
        for attr, count in sorted(stats_7d['attribution_counts'].items(), key=lambda x: -x[1]):
            print(f"    • {attr}: {count}次")
    
    print(f"\n建议:")
    print(f"  信心度: {suggestion['confidence']}")
    print(f"  原因: {suggestion['reason']}")
    
    if suggestion['recommendation']:
        print(f"\n  建议新权重:")
        print(f"    舆情: {suggestion['recommendation']['sentiment']:.2f}")
        print(f"    技术: {suggestion['recommendation']['technical']:.2f}")
        print(f"    宏观: {suggestion['recommendation']['macro']:.2f}")
        print(f"\n  ⚠️  如需应用此建议，请运行:")
        print(f"     python3 scripts/update_weights.py --apply")
    else:
        print(f"\n  暂无具体调整建议")
    
    return suggestion


if __name__ == '__main__':
    generate_validation_report()
