#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试服务器启动脚本
快速启动本地测试环境
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def check_flask():
    """检查Flask是否已安装"""
    try:
        import flask
        return True
    except ImportError:
        return False

def install_flask():
    """安装Flask"""
    print("📦 检测到Flask未安装，正在安装...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
        print("✅ Flask安装成功！")
        return True
    except subprocess.CalledProcessError:
        print("❌ Flask安装失败，请手动安装：pip install flask")
        return False

def start_server():
    """启动测试服务器"""
    server_file = Path(__file__).parent / "app.py"
    
    if not server_file.exists():
        print("❌ 找不到服务器文件 app.py")
        return False
    
    print("🚀 正在启动测试服务器...")
    print("📍 服务器地址：http://localhost:8080")
    print("⏳ 请等待服务器启动...")
    print("-" * 50)
    
    try:
        # 启动服务器
        subprocess.Popen([sys.executable, str(server_file)])
        
        # 等待服务器启动
        time.sleep(3)
        
        # 自动打开浏览器
        try:
            webbrowser.open("http://localhost:8080")
            print("🌐 已自动打开浏览器")
        except:
            print("🌐 请手动访问：http://localhost:8080")
        
        print("\n✅ 测试服务器已启动！")
        print("💡 现在可以使用 http://localhost:8080 来测试爬虫功能")
        print("🛑 按 Ctrl+C 停止服务器")
        
        return True
        
    except Exception as e:
        print(f"❌ 服务器启动失败：{e}")
        return False

def main():
    """主函数"""
    print("🧪 本地测试服务器启动器")
    print("=" * 40)
    
    # 检查并安装Flask
    if not check_flask():
        if not install_flask():
            return 1
    
    # 启动服务器
    if start_server():
        try:
            # 保持脚本运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 服务器已停止")
            return 0
    else:
        return 1

if __name__ == "__main__":
 