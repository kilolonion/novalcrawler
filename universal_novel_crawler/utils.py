from threading import Lock
from typing import Dict, List, Tuple
import contextlib
import os
import re
import sys
import string
from urllib.parse import urlparse

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

__all__ = [
    'file_lock',
    'safe_print', 
    'print_banner',
    'print_status_table',
    'print_chapter_summary',
    'get_downloaded_chapters',
    'parse_chapter_range',
    'clean_and_validate_url',
]

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

def get_downloaded_chapters(output_dir: str) -> List[str]:
    """获取目录下所有已下载的章节文件名（无扩展名）"""
    if not os.path.exists(output_dir):
        return []
    
    downloaded = []
    for filename in os.listdir(output_dir):
        if filename.endswith('.md'):
            # 移除.md后缀，得到章节标题
            title = filename[:-3]
            downloaded.append(title)
    
    return downloaded


def parse_chapter_range(range_input: str, total_chapters: int) -> Tuple[int, int]:
    """
    解析用户输入的章节范围，如 '1-10', '5:', ':20', '8'。
    返回一个 (start, end) 的元组（基于1的索引）。
    """
    range_input = range_input.strip()
    if not range_input:
        return 1, total_chapters

    if range_input.isdigit():
        val = int(range_input)
        if 1 <= val <= total_chapters:
            return val, val
        else:
            raise ValueError("单个章节号超出范围。")

    if '-' in range_input or ':' in range_input:
        sep = '-' if '-' in range_input else ':'
        parts = range_input.split(sep)
        start_str, end_str = parts[0], parts[1]

        start = int(start_str) if start_str else 1
        end = int(end_str) if end_str else total_chapters
        
        start = max(1, start)
        end = min(total_chapters, end)

        if start > end:
            raise ValueError("开始章节不能大于结束章节。")
        
        return start, end

    raise ValueError("无法识别的范围格式。请使用 '1-10', '5:', ':20', 或 '8' 等格式。")


def clean_and_validate_url(url: str) -> str:
    """
    清理和验证URL，移除异常字符并确保格式正确
    
    Args:
        url: 原始URL字符串
        
    Returns:
        str: 清理后的有效URL
        
    Raises:
        ValueError: 如果URL格式无效
    """
    if not url:
        raise ValueError("URL不能为空")
    
    # 移除首尾空白字符
    url = url.strip()
    
    # 移除常见的异常字符（如中文标点符号等）
    # 这些字符可能在复制粘贴时意外引入
    abnormal_chars = ['】', '【', '」', '「', '》', '《', '）', '（', '｝', '｛', '］', '［']
    for char in abnormal_chars:
        url = url.replace(char, '')
    
    # 移除不可见字符和控制字符
    printable_chars = set(string.printable)
    url = ''.join(char for char in url if char in printable_chars)
    
    # 再次清理首尾空白
    url = url.strip()
    
    # 如果URL不以http://或https://开头，尝试自动添加https://
    if not url.startswith(('http://', 'https://')):
        if url.startswith('www.') or '.' in url:
            url = 'https://' + url
        else:
            raise ValueError(f"无效的URL格式: {url}")
    
    # 验证URL的基本格式
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"URL缺少域名部分: {url}")
        if not parsed.scheme in ('http', 'https'):
            raise ValueError(f"URL协议必须是http或https: {url}")
    except Exception as e:
        raise ValueError(f"URL格式验证失败: {url}, 错误: {str(e)}")
    
    return url