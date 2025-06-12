from threading import Lock
from typing import Dict, List
import contextlib
import os

# 尝试导入rich库用于美化界面
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# 全局锁字典，为每个文件路径创建单独的锁
_file_locks = {}
_locks_lock = Lock()
print_lock = Lock()

@contextlib.contextmanager
def file_lock(filepath):
    """为指定文件路径创建/获取线程锁"""
    with _locks_lock:
        if filepath not in _file_locks:
            _file_locks[filepath] = Lock()
        lock = _file_locks[filepath]
    
    with lock:
        yield

# 全局变量
console = Console() if RICH_AVAILABLE else None

def safe_print(*args, **kwargs):
    """线程安全的打印函数"""
    with print_lock:
        if RICH_AVAILABLE and console:
            # 使用rich的console输出
            message = ' '.join(str(arg) for arg in args)
            console.print(message, **kwargs)
        else:
            # 回退到普通print，移除style等rich特有的参数
            rich_only_kwargs = {'style', 'markup', 'highlight', 'overflow', 'no_wrap', 'emoji', 'justify', 'soft_wrap'}
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in rich_only_kwargs}
            print(*args, **filtered_kwargs)

# 增加 require_confirm 参数；为 False 时跳过"按回车继续"
def print_banner(require_confirm: bool = True):
    """打印美化的标题横幅"""
    if RICH_AVAILABLE and console:
        title = Text("🕷️ 通用小说爬虫 v1.9", style="bold cyan")
        subtitle = Text("智能浏览器登录 & 章节合并 & 多线程下载", style="italic yellow")
        
        banner = Panel(
            Columns([title, subtitle], align="center"),
            box=box.DOUBLE,
            border_style="bright_blue",
            padding=(1, 2)
        )
        console.print(banner)
        
        # 显示免责声明
        disclaimer = Text.from_markup("""
⚖️  [bold yellow]重要免责声明 IMPORTANT DISCLAIMER[/bold yellow]

[red]🛑 本软件仅供学习交流使用，严禁用于任何违法违规活动[/red]
[red]🛑 This software is for learning and communication ONLY[/red]

• 使用者需遵守所在地区法律法规及网站服务条款
• 软件作者不承担因使用本软件产生的任何法律责任
• 所有后果由使用者自行承担，与作者无关
• 禁止爬取政府/军事/敏感机构网站
• 使用本软件即表示同意此免责声明

[dim]按 Enter 键继续，Ctrl+C 退出[/dim]
        """.strip())
        
        disclaimer_panel = Panel(
            disclaimer,
            title="📜 法律声明",
            border_style="red",
            box=box.HEAVY
        )
        console.print(disclaimer_panel)
        
        # 等待用户确认（可选）
        if require_confirm:
            try:
                console.input("")
            except KeyboardInterrupt:
                console.print("\n👋 用户取消，程序退出", style="yellow")
                exit(0)
        
    else:
        print("🕷️  通用小说爬虫 v1.9 - 智能浏览器登录 & 章节合并")
        print("="*50)
        
        # 简单版免责声明
        print("\n" + "="*60)
        print("⚖️  重要免责声明 IMPORTANT DISCLAIMER")
        print("="*60)
        print("🛑 本软件仅供学习交流使用，严禁用于任何违法违规活动")
        print("🛑 This software is for learning and communication ONLY")
        print()
        print("• 使用者需遵守所在地区法律法规及网站服务条款")
        print("• 软件作者不承担因使用本软件产生的任何法律责任")
        print("• 所有后果由使用者自行承担，与作者无关")
        print("• 禁止爬取政府/军事/敏感机构网站")
        print("• 使用本软件即表示同意此免责声明")
        print("="*60)
        
        if require_confirm:
            try:
                input("按 Enter 键继续，Ctrl+C 退出...")
            except KeyboardInterrupt:
                print("\n👋 用户取消，程序退出")
                exit(0)

def print_status_table(info: Dict[str, str]):
    """打印状态信息表格"""
    if RICH_AVAILABLE and console:
        table = Table(box=box.ROUNDED, border_style="green")
        table.add_column("项目", style="cyan", no_wrap=True)
        table.add_column("值", style="magenta")
        
        for key, value in info.items():
            table.add_row(key, value)
            
        console.print(table)
    else:
        for key, value in info.items():
            print(f"{key}: {value}")

def print_chapter_summary(chapters: List, range_info: str = ""):
    """打印章节摘要信息"""
    if RICH_AVAILABLE and console:
        # 创建章节信息面板
        info_text = f"📚 总章节数: [bold green]{len(chapters)}[/bold green]"
        if range_info:
            info_text += f"\n📖 下载范围: [bold yellow]{range_info}[/bold yellow]"
        
        if len(chapters) > 0:
            first_title = chapters[0].title if hasattr(chapters[0], 'title') else str(chapters[0])
            last_title = chapters[-1].title if hasattr(chapters[-1], 'title') else str(chapters[-1])
            info_text += f"\n🔖 首章: [italic]{first_title}[/italic]"
            info_text += f"\n🔖 末章: [italic]{last_title}[/italic]"
        
        panel = Panel(
            info_text,
            title="📋 章节信息",
            border_style="blue",
            box=box.ROUNDED
        )
        console.print(panel)
    else:
        print(f"📚 总章节数: {len(chapters)}")
        if range_info:
            print(f"📖 下载范围: {range_info}")
        if len(chapters) > 0:
            first_title = chapters[0].title if hasattr(chapters[0], 'title') else str(chapters[0])
            last_title = chapters[-1].title if hasattr(chapters[-1], 'title') else str(chapters[-1])
            print(f"🔖 首章: {first_title}")
            print(f"🔖 末章: {last_title}") 