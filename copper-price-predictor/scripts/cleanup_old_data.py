#!/usr/bin/env python3
"""
清理旧数据文件
- 保留最近90天的validation报告
- 清理过期的news_analysis.json（超过7天的）
- 归档旧的历史数据
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def get_data_dir():
    """获取数据目录"""
    return Path(__file__).parent.parent / 'data'


def cleanup_validation_reports(days=90):
    """清理超过90天的validation报告"""
    validation_dir = get_data_dir() / 'validation'
    if not validation_dir.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    removed_count = 0
    
    for file in validation_dir.glob('*.csv'):
        # 从文件名提取日期
        try:
            date_str = file.stem.split('_')[-1]  # validation_summary_2026-07-13
            file_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            if file_date < cutoff_date:
                file.unlink()
                removed_count += 1
                print(f"🗑️  删除旧报告: {file.name}")
        except (ValueError, IndexError):
            continue
    
    print(f"✅ 清理完成: 删除 {removed_count} 个旧报告")


def cleanup_old_news_analysis(days=7):
    """清理超过7天的news_analysis.json"""
    news_file = get_data_dir() / 'news_analysis.json'
    
    if not news_file.exists():
        return
    
    # 检查文件修改时间
    file_mtime = datetime.fromtimestamp(news_file.stat().st_mtime)
    cutoff_date = datetime.now() - timedelta(days=days)
    
    if file_mtime < cutoff_date:
        news_file.unlink()
        print(f"🗑️  删除过期新闻分析: {news_file.name} (修改时间: {file_mtime.date()})")
    else:
        print(f"✅ 新闻分析文件有效: {news_file.name} (修改时间: {file_mtime.date()})")


def archive_old_data():
    """归档旧的历史数据（可选）"""
    data_dir = get_data_dir()
    archive_dir = data_dir / 'archive'
    archive_dir.mkdir(exist_ok=True)
    
    # 可以在这里添加归档逻辑
    # 例如：将去年的数据移动到archive目录
    pass


def main():
    """主函数"""
    print("="*60)
    print("🧹 开始清理旧数据")
    print("="*60)
    
    # 1. 清理旧validation报告（保留90天）
    print("\n📁 清理 validation 报告...")
    cleanup_validation_reports(days=90)
    
    # 2. 清理过期的新闻分析文件
    print("\n📁 清理过期新闻分析...")
    cleanup_old_news_analysis(days=7)
    
    # 3. 显示当前数据目录大小
    print("\n📊 当前数据目录状态:")
    data_dir = get_data_dir()
    total_size = 0
    
    for file in data_dir.rglob('*'):
        if file.is_file():
            size = file.stat().st_size
            total_size += size
            size_str = f"{size/1024:.1f}K" if size < 1024*1024 else f"{size/(1024*1024):.1f}M"
            print(f"   {file.name:40s} {size_str:>8s}")
    
    total_str = f"{total_size/1024:.1f}K" if total_size < 1024*1024 else f"{total_size/(1024*1024):.1f}M"
    print(f"\n   {'总计':40s} {total_str:>8s}")
    
    print("\n✅ 清理完成")


if __name__ == '__main__':
    main()
