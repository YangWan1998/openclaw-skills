#!/usr/bin/env python3
"""
权重调整脚本 - 根据学习日志自动/半自动调整预测模型权重
支持：自动调整（带阈值）、手动确认、仅生成建议
"""

import sys
import json
from pathlib import Path
from learning_manager import (
    get_current_weights,
    get_error_statistics,
    generate_weight_adjustment_suggestion,
    update_weights,
    load_weight_history
)


def print_current_status():
    """打印当前状态"""
    current = get_current_weights()
    stats_7d = get_error_statistics(days=7)
    stats_30d = get_error_statistics(days=30)
    
    print("=" * 60)
    print("📊 当前权重配置")
    print("=" * 60)
    print(f"舆情权重: {current['sentiment']:.2f}")
    print(f"技术权重: {current['technical']:.2f}")
    print(f"宏观权重: {current['macro']:.2f}")
    print()
    print("=" * 60)
    print("📈 错误统计")
    print("=" * 60)
    print(f"最近7天: 验证{stats_7d['total_validated']}条, 错误{stats_7d['total_errors']}条, 错误率{stats_7d['error_rate']*100:.1f}%")
    print(f"最近30天: 验证{stats_30d['total_validated']}条, 错误{stats_30d['total_errors']}条, 错误率{stats_30d['error_rate']*100:.1f}%")
    
    if stats_7d['attribution_counts']:
        print("\n最近7天错误归因:")
        for attr, count in sorted(stats_7d['attribution_counts'].items(), key=lambda x: -x[1]):
            print(f"  • {attr}: {count}次")
    
    print()


def suggest_only():
    """仅生成建议，不修改权重"""
    suggestion = generate_weight_adjustment_suggestion()
    
    print("=" * 60)
    print("💡 权重调整建议")
    print("=" * 60)
    print(f"信心度: {suggestion['confidence']}")
    print(f"原因: {suggestion['reason']}")
    
    if suggestion['recommendation']:
        print("\n建议新权重:")
        print(f"  舆情: {suggestion['recommendation']['sentiment']:.2f}")
        print(f"  技术: {suggestion['recommendation']['technical']:.2f}")
        print(f"  宏观: {suggestion['recommendation']['macro']:.2f}")
        print("\n如需应用此建议，请运行:")
        print(f"  python3 scripts/update_weights.py --apply")
    else:
        print("\n暂无具体调整建议")
    
    return suggestion


def auto_adjust(error_threshold=0.6, min_samples=5, dry_run=False):
    """
    自动调整权重
    
    Args:
        error_threshold: 错误率阈值，超过此值才调整
        min_samples: 最小样本数
        dry_run: 是否仅预览不执行
    
    Returns:
        bool: 是否进行了调整
    """
    stats_7d = get_error_statistics(days=7)
    stats_30d = get_error_statistics(days=30)
    
    print("=" * 60)
    print("🤖 自动权重调整")
    print("=" * 60)
    print(f"参数: 错误率阈值={error_threshold}, 最小样本={min_samples}")
    print()
    
    # 检查条件
    if stats_7d['total_validated'] < min_samples:
        print(f"❌ 样本不足: 最近7天只有{stats_7d['total_validated']}条验证记录，需要至少{min_samples}条")
        return False
    
    if stats_7d['error_rate'] < error_threshold:
        print(f"✅ 错误率正常: {stats_7d['error_rate']*100:.1f}% < {error_threshold*100:.0f}%，无需调整")
        return False
    
    # 生成建议
    suggestion = generate_weight_adjustment_suggestion()
    
    if not suggestion['recommendation']:
        print("❌ 无法生成有效建议:", suggestion['reason'])
        return False
    
    print(f"⚠️ 错误率过高: {stats_7d['error_rate']*100:.1f}% >= {error_threshold*100:.0f}%")
    print(f"原因: {suggestion['reason']}")
    print()
    print("建议调整:")
    print(f"  舆情: {get_current_weights()['sentiment']:.2f} -> {suggestion['recommendation']['sentiment']:.2f}")
    print(f"  技术: {get_current_weights()['technical']:.2f} -> {suggestion['recommendation']['technical']:.2f}")
    print(f"  宏观: {get_current_weights()['macro']:.2f} -> {suggestion['recommendation']['macro']:.2f}")
    
    if dry_run:
        print("\n[预览模式] 未实际应用调整")
        return False
    
    # 执行调整
    print("\n正在应用调整...")
    success = update_weights(
        new_weights=suggestion['recommendation'],
        reason=suggestion['reason'],
        triggered_by=f"自动调整: 7天错误率{stats_7d['error_rate']*100:.1f}% >= 阈值{error_threshold*100:.0f}%",
        approved_by='auto',
        auto_adjusted=True
    )
    
    if success:
        print("✅ 权重已更新")
        print(f"\n变更已记录到:")
        print(f"  - data/weight_history.csv")
        print(f"  - config/prediction_model.json")
    else:
        print("❌ 更新失败")
    
    return success


def show_history():
    """显示权重调整历史"""
    history = load_weight_history()
    
    print("=" * 60)
    print("📜 权重调整历史")
    print("=" * 60)
    
    if not history:
        print("暂无调整记录")
        return
    
    for record in history[-10:]:  # 最近10条
        print(f"\n日期: {record.get('date', '未知')}")
        print(f"变更: 舆情 {record.get('old_sentiment_weight', '?')} -> {record.get('new_sentiment_weight', '?')}, "
              f"技术 {record.get('old_technical_weight', '?')} -> {record.get('new_technical_weight', '?')}, "
              f"宏观 {record.get('old_macro_weight', '?')} -> {record.get('new_macro_weight', '?')}")
        print(f"原因: {record.get('change_reason', '未知')}")
        print(f"触发: {record.get('triggered_by', '未知')}")
        print(f"批准: {record.get('approved_by', '未知')} {'(自动)' if record.get('auto_adjusted') == 'True' else '(手动)'}")
        print("-" * 40)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='权重调整工具')
    parser.add_argument('--status', action='store_true', help='显示当前状态')
    parser.add_argument('--suggest', action='store_true', help='仅生成建议')
    parser.add_argument('--auto', action='store_true', help='自动调整（需满足条件）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式（不实际修改）')
    parser.add_argument('--history', action='store_true', help='显示调整历史')
    parser.add_argument('--threshold', type=float, default=0.6, help='错误率阈值（默认0.6）')
    parser.add_argument('--min-samples', type=int, default=5, help='最小样本数（默认5）')
    
    args = parser.parse_args()
    
    if args.status or len(sys.argv) == 1:
        print_current_status()
    elif args.suggest:
        suggest_only()
    elif args.auto:
        auto_adjust(
            error_threshold=args.threshold,
            min_samples=args.min_samples,
            dry_run=args.dry_run
        )
    elif args.history:
        show_history()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
