#!/usr/bin/env python3
"""
MVP主运行脚本
运行完整的铜价预测流程
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def is_weekend():
    """检查今天是否是周末（周六=5, 周日=6）"""
    return datetime.now().weekday() >= 5


def run_script(script_name, extra_args=None):
    """运行子脚本"""
    script_dir = Path(__file__).parent
    script_path = script_dir / script_name
    
    print(f"\n{'='*60}")
    print(f"🚀 运行: {script_name}")
    if extra_args:
        print(f"   参数: {' '.join(extra_args)}")
    print('='*60)
    
    # 检测是否需要使用conda py311环境
    if sys.version_info < (3, 11):
        python_cmd = ['conda', 'run', '-n', 'py311', 'python']
    else:
        python_cmd = [sys.executable]
    
    # 构建命令
    cmd = python_cmd + [str(script_path)]
    if extra_args:
        cmd.extend(extra_args)
    
    result = subprocess.run(
        cmd,
        capture_output=False,
        text=True
    )
    
    return result.returncode == 0


def main():
    """主流程"""
    print("🚀 启动铜价预测MVP流程")
    print(f"{'='*60}")
    
    # 周末检测：周六周日跳过
    if is_weekend():
        print("📅 今天是周末，国内期货市场休市")
        print("⏭️  跳过铜价预测，周一继续")
        print(f"{'='*60}")
        return True
    
    # 检查是否有预存的新闻分析文件
    data_dir = Path(__file__).parent.parent / 'data'
    news_analysis_file = data_dir / 'news_analysis.json'
    has_prebuilt_news = news_analysis_file.exists()
    
    if has_prebuilt_news:
        # 检查文件是否是今天的
        try:
            import json
            with open(news_analysis_file, 'r') as f:
                news_data = json.load(f)
            file_date = news_data.get('timestamp', '')[:10]  # 取前10位日期
            today_str = __import__('datetime').datetime.now().strftime('%Y-%m-%d')
            
            if file_date == today_str:
                print(f"✅ 发现今天的新闻分析文件: {news_analysis_file}")
                print(f"   包含 {news_data.get('news_count', 0)} 条新闻，跳过新闻搜索")
                use_prebuilt_news = True
            else:
                print(f"⚠️ 新闻分析文件日期不匹配: {file_date} != {today_str}")
                print("   将重新搜索新闻")
                use_prebuilt_news = False
        except Exception as e:
            print(f"⚠️ 读取新闻分析文件失败: {e}")
            use_prebuilt_news = False
    else:
        print("ℹ️  没有找到预存的新闻分析文件，将执行完整流程")
        use_prebuilt_news = False
    
    # 构建运行流程
    if use_prebuilt_news:
        # 使用预存的新闻，跳过搜索
        scripts = [
            ('fetch_copper_price_v2.py', '获取铜价数据'),
            ('fetch_macro_data.py', '获取宏观数据'),
            # 跳过 search_copper_news.py
            ('analyze_and_predict.py', '分析并生成预测', ['--news-file', str(news_analysis_file)]),
            ('generate_report.py', '生成预测报告')
        ]
    else:
        # 完整流程
        scripts = [
            ('fetch_copper_price_v2.py', '获取铜价数据', None),
            ('fetch_macro_data.py', '获取宏观数据', None),
            ('search_copper_news.py', '搜索铜相关新闻', None),
            ('analyze_and_predict.py', '分析并生成预测', None),
            ('generate_report.py', '生成预测报告', None)
        ]
    
    success_count = 0
    for item in scripts:
        if len(item) == 3:
            script, desc, extra_args = item
        else:
            script, desc = item
            extra_args = None
        
        print(f"\n📋 步骤: {desc}")
        if run_script(script, extra_args):
            success_count += 1
            print(f"✅ {desc} 完成")
        else:
            print(f"❌ {desc} 失败")
    
    print(f"\n{'='*60}")
    print(f"✅ MVP流程完成: {success_count}/{len(scripts)} 个步骤成功")
    print('='*60)
    
    # 显示报告路径
    today = __import__('datetime').datetime.now().strftime('%Y-%m-%d')
    report_path = Path(__file__).parent.parent / 'reports' / f'{today}_分析报告.txt'
    print(f"\n📄 今日报告: {report_path}")
    
    if report_path.exists():
        print("✅ 报告已生成")
    else:
        print("⚠️ 报告未找到")
    
    # 验证历史预测（如果价格历史足够）
    print(f"\n{'='*60}")
    print("🔍 验证历史预测")
    print('='*60)
    
    price_history_path = Path(__file__).parent.parent / 'data' / 'price_history.csv'
    predictions_path = Path(__file__).parent.parent / 'data' / 'predictions.csv'
    
    if price_history_path.exists() and predictions_path.exists():
        # 检查是否有足够的历史数据进行验证
        import csv
        with open(price_history_path, 'r') as f:
            price_count = sum(1 for _ in csv.DictReader(f))
        with open(predictions_path, 'r') as f:
            pred_count = sum(1 for _ in csv.DictReader(f))
        
        if price_count >= 6 and pred_count >= 1:  # 至少需要6天价格历史和1条预测
            print(f"📊 价格历史: {price_count} 条, 预测记录: {pred_count} 条")
            print("🔄 开始验证历史预测...")
            
            if run_script('validate_predictions.py'):
                print("✅ 验证完成")
                
                # 显示学习日志和权重建议
                print(f"\n{'='*60}")
                print("📝 学习日志已更新")
                print("="*60)
                
                learning_log_path = Path(__file__).parent.parent / 'data' / 'learning_log.csv'
                if learning_log_path.exists():
                    print(f"✅ 学习日志: {learning_log_path}")
                
                weight_history_path = Path(__file__).parent.parent / 'data' / 'weight_history.csv'
                if weight_history_path.exists():
                    print(f"✅ 权重历史: {weight_history_path}")
                
                print(f"\n💡 如需查看权重调整建议，运行:")
                print(f"   python3 scripts/update_weights.py --suggest")
                print(f"\n💡 如需查看权重调整历史，运行:")
                print(f"   python3 scripts/update_weights.py --history")
            else:
                print("❌ 验证失败")
        else:
            print(f"⏳ 数据不足，跳过验证")
            print(f"   需要: 价格历史≥6条, 预测记录≥1条")
            print(f"   当前: 价格历史={price_count}条, 预测记录={pred_count}条")
            print(f"\n💡 继续运行几天后会自动开始验证")
    else:
        print("⏳ 数据文件不存在，跳过验证")
    
    return success_count == len(scripts)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
