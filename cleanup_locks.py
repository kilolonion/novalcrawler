#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用小说爬虫 - 锁文件清理工具
Universal Novel Crawler - Lock Files Cleanup Tool

用于清理爬虫运行过程中可能残留的 .lock 文件
"""

import os
import glob
import argparse
from pathlib import Path

def find_lock_files(directory: str = ".") -> list:
    """在指定目录及其子目录中查找所有 .lock 文件"""
    lock_files = []
    
    # 使用 glob 递归查找所有 .lock 文件
    pattern = os.path.join(directory, "**", "*.lock")
    lock_files.extend(glob.glob(pattern, recursive=True))
    
    return sorted(lock_files)

def cleanup_lock_files(directory: str = ".", dry_run: bool = False) -> tuple:
    """清理锁文件"""
    lock_files = find_lock_files(directory)
    
    if not lock_files:
        print("✅ 未发现任何 .lock 文件")
        return 0, 0
    
    print(f"🔍 发现 {len(lock_files)} 个 .lock 文件:")
    for lock_file in lock_files:
        print(f"   📄 {lock_file}")
    
    if dry_run:
        print("\n🔬 [预览模式] 以上文件将被删除 (使用 --execute 实际执行)")
        return len(lock_files), 0
    
    print(f"\n🧹 开始清理...")
    
    success_count = 0
    error_count = 0
    
    for lock_file in lock_files:
        try:
            os.remove(lock_file)
            print(f"✅ 已删除: {lock_file}")
            success_count += 1
        except OSError as e:
            print(f"❌ 删除失败: {lock_file} - {e}")
            error_count += 1
    
    return success_count, error_count

def main():
    parser = argparse.ArgumentParser(
        description="🧹 通用小说爬虫锁文件清理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python cleanup_locks.py                    # 预览当前目录下的锁文件
  python cleanup_locks.py --execute          # 清理当前目录下的锁文件
  python cleanup_locks.py -d /path/to/novels # 预览指定目录下的锁文件
  python cleanup_locks.py -d /path/to/novels --execute  # 清理指定目录
        """
    )
    
    parser.add_argument(
        '-d', '--directory', 
        default=".",
        help='要清理的目录路径 (默认: 当前目录)'
    )
    
    parser.add_argument(
        '--execute', 
        action='store_true',
        help='实际执行清理操作 (默认: 预览模式)'
    )
    
    parser.add_argument(
        '--version', 
        action='version', 
        version='%(prog)s v1.0'
    )
    
    args = parser.parse_args()
    
    # 验证目录存在
    if not os.path.exists(args.directory):
        print(f"❌ 错误: 目录 '{args.directory}' 不存在")
        return 1
    
    if not os.path.isdir(args.directory):
        print(f"❌ 错误: '{args.directory}' 不是一个目录")
        return 1
    
    print(f"🔍 扫描目录: {os.path.abspath(args.directory)}")
    print("=" * 60)
    
    try:
        success_count, error_count = cleanup_lock_files(
            directory=args.directory,
            dry_run=not args.execute
        )
        
        if args.execute:
            print("\n" + "=" * 60)
            print(f"📊 清理结果:")
            print(f"   ✅ 成功删除: {success_count} 个文件")
            if error_count > 0:
                print(f"   ❌ 删除失败: {error_count} 个文件")
            else:
                print(f"   ❌ 删除失败: 0 个文件")
            
            if success_count > 0:
                print(f"\n🎉 清理完成！")
            else:
                print(f"\n⚠️ 没有文件被删除")
        
        return 0 if error_count == 0 else 1
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 