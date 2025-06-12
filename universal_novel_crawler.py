#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重要免责声明 IMPORTANT DISCLAIMER:
    本软件仅供学习交流使用，严禁用于任何违法违规活动
    使用者需遵守所在地区法律法规及网站服务条款
    软件作者不承担因使用本软件产生的任何法律责任
    所有后果由使用者自行承担，与作者无关
    禁止爬取政府/军事/敏感机构网站
    使用本软件即表示同意此免责声明
"""

def main():
    """主入口点 - 启动CLI界面"""
    from universal_novel_crawler.cli import main as cli_main
    cli_main()

if __name__ == "__main__":
    main() 