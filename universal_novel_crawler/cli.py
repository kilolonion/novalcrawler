#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用小说爬虫 - 命令行接口
Universal Novel Crawler - Command Line Interface
"""

import argparse
import getpass
import sys
from urllib.parse import urlparse

from .crawler import UniversalNovelCrawler
from .modules.login_manager import LoginManager
from .models import LoginConfig
from .modules.site_detector import SiteDetector
from .modules.security_checker import get_security_checker
from .modules.processor import cleanup_lock_files
from .utils import safe_print, print_banner, clean_and_validate_url

try:
    from rich.console import Console
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None

def create_cli_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='🕷️  通用小说爬虫 v1.9 - 智能浏览器登录 & 章节合并',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚖️  重要免责声明 IMPORTANT DISCLAIMER:
🛑 本软件仅供学习交流使用，严禁用于任何违法违规活动
🛑 This software is for learning and communication ONLY
• 使用者需遵守所在地区法律法规及网站服务条款
• 软件作者不承担因使用本软件产生的任何法律责任
• 所有后果由使用者自行承担，与作者无关
• 禁止爬取政府/军事/敏感机构网站
• 使用本软件即表示同意此免责声明

使用示例:
  universal_novel_crawler.py                                    # 交互模式
  universal_novel_crawler.py -u https://example.com/novel/      # 指定URL
  universal_novel_crawler.py -u URL -r 1-100 -t 5              # 下载1-100章，5线程
  universal_novel_crawler.py -u URL --login browser             # 使用浏览器登录
  universal_novel_crawler.py -u URL --no-login                  # 无需登录模式
  universal_novel_crawler.py -u URL --merge                     # 下载后自动合并
  universal_novel_crawler.py --list-sites                       # 显示支持的网站

章节范围格式:
  100-200    下载第100到200章
  50:        从第50章开始下载
  :100       下载前100章
  100+       从第100章开始到结尾
  150        只下载第150章
        """
    )
    
    # 基本参数
    parser.add_argument('-u', '--url', help='小说目录页面URL')
    parser.add_argument('-r', '--range', help='章节范围 (例: 1-100, 50:, :100, 100+, 150)')
    parser.add_argument('-t', '--threads', type=int, default=3, 
                       help='并发线程数 (1-10, 默认: 3)')
    parser.add_argument('-o', '--output', help='输出目录 (默认: novels_网站名)')
    
    # 登录相关
    login_group = parser.add_mutually_exclusive_group()
    login_group.add_argument('--login', choices=['browser', 'cookies', 'password', 'auto'],
                            help='登录方式: browser(浏览器), cookies(Cookie提取), password(用户名密码), auto(自动Cookie)')
    login_group.add_argument('--no-login', action='store_true', help='无需登录模式')
    
    # 登录参数
    parser.add_argument('--username', help='登录用户名')
    parser.add_argument('--password', help='登录密码')
    parser.add_argument('--cookies', help='Cookie字符串')
    parser.add_argument('--browser', choices=['chrome', 'edge', 'auto'], default='auto',
                       help='浏览器选择 (默认: auto)')
    
    # 其他选项
    parser.add_argument('--merge', action='store_true',
                       help='下载完成后自动合并所有章节为一个txt文件')
    parser.add_argument('--skip-robots', action='store_true',
                       help='跳过 robots.txt 验证 (不推荐)')
    parser.add_argument('--skip-check-files', action='store_true',
                       help='跳过已下载文件检查 (禁用断点续传)')
    parser.add_argument('--list-sites', action='store_true',
                       help='显示支持的网站列表')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式')
    parser.add_argument('--version', action='version', version='%(prog)s v1.9')
    # 跳过免责声明
    parser.add_argument('-y', '--yes', action='store_true',
                       help='自动确认免责声明(跳过按回车)')
    
    return parser

def show_supported_sites():
    """显示支持的网站列表"""
    detector = SiteDetector()
    
    print("🌐 支持的网站列表:")
    print("=" * 50)
    
    for site_key, config in detector.site_configs.items():
        print(f"📚 {config.name}")
        print(f"   域名: {site_key}")
        print(f"   选择器: {len(config.catalog_selectors)} 个目录选择器")
        print()
    
    print("💡 提示: 除以上网站外，本工具还支持大多数小说网站的通用解析")

def confirm_terms_of_use(auto_confirm: bool = False) -> bool:
    """确认用户已阅读并同意免责声明和使用条款"""
    if auto_confirm:
        return True
        
    # 显示重要法律声明
    safe_print("\n" + "="*80, style="bold red")
    safe_print("🚨 重要法律声明与风险警告 IMPORTANT LEGAL NOTICE 🚨", style="bold red")
    safe_print("="*80, style="bold red")
    
    safe_print("⚠️  本软件的使用可能涉及以下法律风险:", style="yellow")
    safe_print("   • 违反《网络安全法》、《数据安全法》、《个人信息保护法》", style="red")
    safe_print("   • 侵犯网站版权和知识产权", style="red") 
    safe_print("   • 违反网站用户协议和服务条款", style="red")
    safe_print("   • 触犯《刑法》相关条款", style="red")
    
    safe_print("\n🚫 严禁用于以下用途:", style="yellow")
    safe_print("   ❌ 爬取政府、军事、公安、国安等敏感机构网站", style="red")
    safe_print("   ❌ 爬取金融、医疗、教育等涉及隐私的敏感数据", style="red")
    safe_print("   ❌ 收集个人隐私信息或敏感数据", style="red")
    safe_print("   ❌ 任何形式的商业用途或牟利行为", style="red")
    safe_print("   ❌ 侵犯他人版权和知识产权", style="red")
    
    safe_print("\n📋 使用本软件即表示您:", style="cyan")
    safe_print("   ✅ 已阅读完整的免责声明(DISCLAIMER.md)", style="green")
    safe_print("   ✅ 同意承担所有法律责任和风险", style="green")
    safe_print("   ✅ 承诺仅用于合法的学习研究目的", style="green")
    safe_print("   ✅ 遵守相关法律法规和网站服务条款", style="green")
    
    safe_print("\n⚖️  所有法律后果由使用者自行承担，与软件作者无关！", style="bold red")
    safe_print("="*80, style="bold red")
    
    # 询问用户确认
    if RICH_AVAILABLE and console:
        from rich.prompt import Confirm
        try:
            accepted = Confirm.ask(
                "\n📜 [bold yellow]您是否已阅读并完全理解上述法律风险，并同意继续使用？[/bold yellow]",
                default=False
            )
        except KeyboardInterrupt:
            safe_print("\n❌ 用户取消操作", style="red")
            return False
    else:
        try:
            response = input("\n📜 您是否已阅读并完全理解上述法律风险，并同意继续使用？(y/N): ").strip().lower()
            accepted = response in ['y', 'yes']
        except KeyboardInterrupt:
            safe_print("\n❌ 用户取消操作", style="red")
            return False
    
    if not accepted:
        safe_print("\n❌ 未同意使用条款，程序退出", style="red")
        safe_print("📖 如需了解详细信息，请查看 DISCLAIMER.md 文件", style="yellow")
        return False
    
    safe_print("\n✅ 用户已确认同意使用条款", style="green")
    return True
    
def setup_login_from_args(login_manager: LoginManager, args, site_url: str):
    """根据命令行参数设置登录配置"""
    if args.no_login:
        login_manager.login_config.mode = 'none'
        safe_print("✅ 设置为无需登录模式")
        
    elif args.login:
        if args.login == 'browser':
            login_manager.login_config.mode = 'browser_login'
            login_manager.login_config.browser = args.browser
            safe_print(f"✅ 设置为浏览器登录模式 ({args.browser})")
            
        elif args.login == 'cookies':
            login_manager.login_config.mode = 'browser_cookies'
            login_manager.login_config.browser = args.browser
            safe_print(f"✅ 设置为Cookie自动提取模式 ({args.browser})")
            
        elif args.login == 'password':
            login_manager.login_config.mode = 'credentials'
            if args.username and args.password:
                login_manager.login_config.username = args.username
                login_manager.login_config.password = args.password
            else:
                login_manager.login_config.username = input("请输入用户名: ").strip()
                login_manager.login_config.password = getpass.getpass("请输入密码: ")
            
            # 设置登录URL
            parsed = urlparse(site_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            login_manager.login_config.login_url = base_url + "/login"
            safe_print("✅ 设置为用户名密码登录模式")
            
        elif args.login == 'auto':
            login_manager.login_config.mode = 'browser_cookies'
            login_manager.login_config.browser = args.browser
            safe_print(f"✅ 设置为自动Cookie提取模式 ({args.browser})")
    else:
        # 如果没有指定登录参数，使用交互模式
        login_manager.get_login_config(site_url)

def ask_continue() -> bool:
    """询问用户是否继续爬取其他小说"""
    if RICH_AVAILABLE and console:
        from rich.prompt import Confirm
        return Confirm.ask(
            "\n🔄 [bold green]是否继续爬取其他小说？[/bold green]", 
            default=True
        )
    else:
        print()
        user_input = input("🔄 是否继续爬取其他小说？ (y/n, 默认y): ").strip().lower()
        return user_input in ['', 'y', 'yes']

def run_single_crawl(args) -> bool:
    """执行单次爬取任务，返回是否成功"""
    # 获取URL
    if args.url:
        catalog_url = args.url
    else:
        print("\n" + "="*60)
        safe_print("🆕 开始新的爬取任务", style="bold green")
        print("="*60)
        if RICH_AVAILABLE and console:
            catalog_url = console.input("📖 请输入小说目录页URL: ").strip()
        else:
            catalog_url = input("📖 请输入小说目录页URL: ").strip()
    
    if not catalog_url:
        safe_print("❌ URL不能为空", style="bold red")
        return False
    
    # 清理和验证URL
    try:
        original_url = catalog_url
        catalog_url = clean_and_validate_url(catalog_url)
        if original_url != catalog_url:
            safe_print(f"🧹 URL已自动清理: [blue]{catalog_url}[/blue]", style="cyan")
        else:
            safe_print(f"📖 目标URL: [blue]{catalog_url}[/blue]", style="cyan")
    except ValueError as e:
        safe_print(f"❌ URL格式错误: {e}", style="bold red")
        return False
    
    # 获取线程数
    max_workers = args.threads
    if not args.url:  # 交互模式时询问
        if RICH_AVAILABLE and console:
            workers_input = console.input(f"⚡ 请输入并发线程数 [dim](1-10, 默认{max_workers})[/dim]: ").strip()
        else:
            workers_input = input(f"⚡ 请输入并发线程数 (1-10, 默认{max_workers}): ").strip()
        if workers_input.isdigit():
            max_workers = max(1, min(10, int(workers_input)))
    
    # 获取章节范围
    range_input = args.range
    if not args.url:  # 交互模式时询问
        if RICH_AVAILABLE and console:
            from rich.panel import Panel
            from rich import box
            # 美化的范围选择提示
            range_help = """
📚 章节范围格式:
  • [cyan]100-200[/cyan]  : 下载第100到200章
  • [cyan]50:[/cyan]      : 从第50章开始下载
  • [cyan]:100[/cyan]     : 下载前100章
  • [cyan]100+[/cyan]     : 从第100章开始到结尾
  • [cyan]150[/cyan]      : 只下载第150章
            """.strip()
            
            panel = Panel(
                range_help,
                title="📋 章节范围选择 (留空下载全部)",
                border_style="yellow",
                box=box.ROUNDED
            )
            console.print(panel)
            range_input = console.input("请输入章节范围: ").strip()
        else:
            print("\n📚 章节范围选择 (留空下载全部):")
            print("  格式示例:")
            print("  • 100-200  : 下载第100到200章")
            print("  • 50:      : 从第50章开始下载")
            print("  • :100     : 下载前100章")
            print("  • 100+     : 从第100章开始到结尾")
            print("  • 150      : 只下载第150章")
            range_input = input("请输入章节范围: ").strip()
    
    # 创建爬虫实例
    login_config = LoginConfig()
    login_manager = LoginManager(login_config)
    detector = SiteDetector()
    crawler = UniversalNovelCrawler(login_manager, detector)
    
    # robots.txt 检查可选（必须在首次网络请求前设置）
    if args.skip_robots:
        setattr(crawler, 'skip_robots', True)
    
    # 文件检查可选（断点续传功能）
    if args.skip_check_files:
        setattr(crawler, 'skip_check_files', True)
    
    # 设置登录配置
    if args.url and (args.login or args.no_login):
        # CLI模式：根据参数设置登录
        setup_login_from_args(login_manager, args, catalog_url)
    else:
        # 交互模式：询问用户
        login_manager.get_login_config(catalog_url)
    
    # 执行登录
    crawler.session = login_manager.ensure_login(catalog_url)
    # 只有非无需登录模式才验证登录状态
    if login_manager.login_config.mode != 'none' and not login_manager.verify_login():
        safe_print("❌ 登录失败，程序退出", style="bold red")
        return False
    
    # 询问是否启用robots.txt检查（仅在交互模式且未指定--skip-robots时）
    if not args.url and not args.skip_robots:  # 交互模式
        if RICH_AVAILABLE and console:
            from rich.prompt import Confirm
            enable_robots = Confirm.ask(
                "🤖 [yellow]是否启用 robots.txt 检查？[/yellow]", 
                default=True
            )
        else:
            user_input = input("🤖 是否启用 robots.txt 检查？ (y/n, 默认y): ").strip().lower()
            enable_robots = user_input in ['', 'y', 'yes']
        
        if not enable_robots:
            setattr(crawler, 'skip_robots', True)
            safe_print("⚠️ 已禁用 robots.txt 检查", style="yellow")
        else:
            safe_print("✅ 已启用 robots.txt 检查", style="green")
    
    # 获取章节列表
    safe_print("🔍 正在获取章节列表...", style="yellow")
    chapters = crawler.get_chapter_list(catalog_url)
    if not chapters:
        safe_print("❌ 未找到章节列表", style="bold red")
        return False
    
    # 过滤章节范围
    if range_input:
        try:
            original_count = len(chapters)
            chapters = crawler.filter_chapters_by_range(chapters, range_input)
            if not chapters:
                safe_print("❌ 指定范围内没有找到章节", style="bold red")
                return False
            safe_print(f"📖 已从 {original_count} 章中筛选出 {len(chapters)} 章", style="green")
        except Exception as e:
            safe_print(f"❌ 章节范围解析失败: {str(e)}", style="bold red")
            return False
    
    # 开始爬取
    output_dir = args.output
    auto_merge = args.merge if hasattr(args, 'merge') else False
    crawler.crawl_novel(catalog_url, max_workers, chapters, output_dir, auto_merge)
    
    return True

def main():
    # 解析命令行参数
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # 处理特殊命令
    if args.list_sites:
        show_supported_sites()
        return
    
    # 显示美化的标题（只在开始时显示一次）
    print_banner(require_confirm=not args.yes)
    
    # 用户条款确认（法律合规要求）
    if not confirm_terms_of_use(auto_confirm=args.yes):
        return
    
    # 主循环
    while True:
        try:
            # 执行单次爬取任务
            success = run_single_crawl(args)
            
            # 如果是命令行模式（指定了URL），执行一次后退出
            if args.url:
                break
                
            # 交互模式：询问是否继续
            if not ask_continue():
                break
                
        except KeyboardInterrupt:
            safe_print("\n👋 用户取消，程序退出", style="yellow")
            break
        except Exception as e:
            safe_print(f"❌ 程序执行出错: {e}", style="bold red")
            if not ask_continue():
                break
    
    # 程序结束前清理所有残留的锁文件
    try:
        cleanup_lock_files()
    except Exception as e:
        safe_print(f"⚠️ 清理锁文件时出错: {e}", style="yellow")
    
    safe_print("👋 感谢使用通用小说爬虫！", style="bold cyan")

if __name__ == "__main__":
    main() 