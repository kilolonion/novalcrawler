import json
import os
import random
import re
import time
import urllib.parse
import chardet
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from .modules.login_manager import LoginManager
from .models import ChapterInfo, SiteConfig
from .modules.site_detector import SiteDetector
from .modules.security_checker import SecurityChecker, get_security_checker
from .utils import (RICH_AVAILABLE, console, file_lock, print_chapter_summary,
                    print_status_table, safe_print)

# 引入工具模块
from .modules import (
    detect_encoding as utils_detect_encoding,
    sanitize_filename as utils_sanitize_filename,
    is_blocked_response as utils_is_blocked_response,
    merge_chapters_to_txt as merger_merge_chapters,
    download_chapters_with_progress as downloader_progress,
    download_chapters_simple as downloader_simple,
    show_completion_stats as downloader_stats,
    fetch_and_parse_catalog as catalog_fetch,
    fetch_full_chapter_content as content_fetch_full,
    process_and_save_chapter as chapter_process_and_save,
    get_novel_title as title_get,
    get_downloaded_chapters as utils_get_downloaded,
    parse_chapter_range as utils_parse_range,
    filter_valid_chapters as catalog_filter_chapters,
)
from .modules.catalog import find_next_catalog_page as catalog_next_page

if RICH_AVAILABLE:
    from rich.progress import (BarColumn, Progress, TextColumn,
                               TimeElapsedColumn, TimeRemainingColumn)


class UniversalNovelCrawler:
    """通用小说爬虫"""
    
    def __init__(self, login_manager: LoginManager, detector: SiteDetector):
        self.login_manager = login_manager
        self.detector = detector
        self.session = self.login_manager.session
        self.novel_title = None
        self.security_checker = get_security_checker()
    
    def check_robots_txt(self, url: str) -> bool:
        """检查robots.txt是否允许访问"""
        # 首先进行安全检查，阻止访问敏感网站
        if not self.security_checker.validate_crawl_request(url):
            return False
            
        # 如果配置要求跳过 robots.txt 检查，直接允许
        if getattr(self, 'skip_robots', False):
            safe_print("⚠️ 已根据参数跳过 robots.txt 检查")
            return True
        
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            robots_url = urljoin(base_url, '/robots.txt')
            
            safe_print(f"🤖 检查 robots.txt: {robots_url}")
            
            # 首先直接获取robots.txt内容检查是否被Cloudflare拦截
            try:
                response = self.session.get(robots_url, timeout=10)
                if self._is_blocked_response(response):
                    safe_print("⚠️ robots.txt 被反爬虫保护拦截，无法读取")
                    safe_print("   按照HTTP协议，默认允许访问")
                    return True
            except Exception:
                pass
            
            # 创建机器人解析器
            rp = RobotFileParser()
            rp.set_url(robots_url)
            
            try:
                rp.read()
                # 检查我们的User-Agent是否被允许访问
                user_agent = self.session.headers.get('User-Agent', '*')
                can_fetch = rp.can_fetch(user_agent, url)
                
                if can_fetch:
                    safe_print("✅ robots.txt 允许访问")
                else:
                    safe_print("⚠️ robots.txt 不允许访问此URL")
                    safe_print("   建议联系网站管理员或选择其他网站")
                    
                    # 给用户选择是否继续的机会
                    if RICH_AVAILABLE:
                        from rich.prompt import Confirm
                        continue_anyway = Confirm.ask(
                            "🤔 [yellow]是否忽略robots.txt限制继续访问？[/yellow]", 
                            default=False
                        )
                    else:
                        continue_anyway = input("🤔 是否忽略robots.txt限制继续访问？(y/n, 默认n): ").strip().lower() in ['y', 'yes']
                    
                    if continue_anyway:
                        safe_print("⚠️ 用户选择忽略robots.txt限制")
                        return True
                
                return can_fetch
                
            except Exception as e:
                safe_print(f"❓ 无法读取 robots.txt (可能不存在): {e}")
                safe_print("   根据HTTP协议，默认允许访问")
                return True
                
        except Exception as e:
            safe_print(f"❌ 检查 robots.txt 时出错: {e}")
            return True  # 出错时默认允许
    
    def _detect_encoding(self, response) -> str:
        """代理到 modules.utils.detect_encoding"""
        return utils_detect_encoding(response)
    
    def _sanitize_filename(self, text: str) -> str:
        """代理到 modules.utils.sanitize_filename"""
        return utils_sanitize_filename(text)
    
    def _is_blocked_response(self, response) -> bool:
        """代理到 modules.utils.is_blocked_response"""
        return utils_is_blocked_response(response)
    
    def save_chapter_list(self, chapters: List[ChapterInfo], catalog_url: str):
        """保存章节列表到JSON文件"""
        parsed_url = urlparse(catalog_url)
        site_name = parsed_url.netloc.replace('www.', '').replace('.', '_')
        filename = f"chapters_{site_name}.json"
        
        chapter_data = []
        for chapter in chapters:
            chapter_data.append({
                "title": chapter.title,
                "url": chapter.url
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "catalog_url": catalog_url,
                "total_chapters": len(chapters),
                "created_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "chapters": chapter_data
            }, f, ensure_ascii=False, indent=2)
        
        safe_print(f"💾 章节列表已保存到: {filename}")
        return filename
    
    def load_chapter_list(self, catalog_url: str) -> Optional[List[ChapterInfo]]:
        """从JSON文件加载章节列表"""
        parsed_url = urlparse(catalog_url)
        site_name = parsed_url.netloc.replace('www.', '').replace('.', '_')
        filename = f"chapters_{site_name}.json"
        
        if not os.path.exists(filename):
            return None
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            safe_print(f"📁 找到缓存文件: {filename}")
            safe_print(f"📚 缓存包含 {data['total_chapters']} 个章节")
            safe_print(f"🕐 创建时间: {data['created_time']}")
            
            chapters = []
            for chapter_data in data['chapters']:
                chapters.append(ChapterInfo(
                    title=chapter_data['title'],
                    url=chapter_data['url']
                ))
            
            return chapters
            
        except Exception as e:
            safe_print(f"❌ 读取缓存文件失败: {str(e)}")
            return None
    
    def get_cache_filename(self, catalog_url: str) -> str:
        """生成缓存文件名"""
        parsed_url = urlparse(catalog_url)
        site_name = parsed_url.netloc.replace('www.', '').replace('.', '_')
        return f"chapters_{site_name}.json"
    
    def detect_and_fix_chapter_order(self, chapters: List[ChapterInfo]) -> List[ChapterInfo]:
        """检测并修正章节顺序"""
        if len(chapters) < 2:
            return chapters
        
        # 提取前几个章节的数字
        first_nums = []
        for i in range(min(5, len(chapters))):
            title = chapters[i].title
            numbers = re.findall(r'第(\d+)章', title)
            if numbers:
                first_nums.append((i, int(numbers[0])))
        
        if len(first_nums) >= 2:
            # 检查是否为倒序
            first_chapter_num = first_nums[0][1]
            second_chapter_num = first_nums[1][1]
            
            if first_chapter_num > second_chapter_num:
                safe_print("🔄 检测到章节列表为倒序，正在修正...")
                chapters.reverse()
                
                # 重新提取修正后的章节号
                first_title = chapters[0].title
                last_title = chapters[-1].title
                first_num = re.findall(r'第(\d+)章', first_title)
                last_num = re.findall(r'第(\d+)章', last_title)
                
                first_str = first_num[0] if first_num else '?'
                last_str = last_num[0] if last_num else '?'
                
                safe_print(f"✅ 章节顺序已修正：第{first_str}章 -> 第{last_str}章")
            else:
                # 显示当前章节范围
                first_title = chapters[0].title
                last_title = chapters[-1].title
                first_num = re.findall(r'第(\d+)章', first_title)
                last_num = re.findall(r'第(\d+)章', last_title)
                
                if first_num and last_num:
                    safe_print(f"📊 章节范围：第{first_num[0]}章 - 第{last_num[0]}章")
        
        return chapters
    
    def get_chapter_list_from_url(self, catalog_url: str) -> List[ChapterInfo]:
        """从URL获取章节列表并缓存"""
        # 针对特定网站的URL转换
        original_url = catalog_url
        if 'huanqixiaoshuo.com' in catalog_url and not catalog_url.endswith('/all.html'):
            # 转换为目录页面URL
            if catalog_url.endswith('/'):
                catalog_url = catalog_url + 'all.html'
            else:
                catalog_url = catalog_url + '/all.html'
            safe_print(f"🔄 自动转换为目录页: {catalog_url}")
        
        safe_print(f"🔍 正在分析目录页面: {catalog_url}")
        
        # 检查缓存 - 使用转换后的URL
        cache_file = self.get_cache_filename(catalog_url)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                chapters = [ChapterInfo(title=item['title'], url=item['url']) for item in data['chapters']]
                safe_print(f"📁 从缓存加载 {len(chapters)} 个章节")
                return chapters
            except Exception as e:
                safe_print(f"⚠️  缓存文件读取失败: {e}")
        
        # 获取新的章节列表
        chapters = self.get_chapter_list(catalog_url)
        
        # 检测并修正章节顺序
        if chapters:
            chapters = self.detect_and_fix_chapter_order(chapters)
        
        # 应用改进的章节过滤
        if chapters:
            filtered_chapters = self.filter_valid_chapters(chapters)
            
            if filtered_chapters:
                safe_print(f"🔍 过滤后保留 {len(filtered_chapters)} 个有效章节")
                chapters = filtered_chapters
        
        # 保存到缓存
        if chapters:
            try:
                cache_data = {
                    'url': catalog_url,
                    'timestamp': time.time(),
                    'chapters': [{'title': chapter.title, 'url': chapter.url} for chapter in chapters]
                }
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                safe_print(f"💾 章节列表已保存到: {cache_file}")
            except Exception as e:
                safe_print(f"⚠️  缓存保存失败: {e}")
        
        return chapters
    
    def get_chapter_list(self, catalog_url: str) -> List[ChapterInfo]:
        """
        获取小说章节列表的入口点。
        该方法会调用模块化的目录获取与解析函数。
        """
        # 首先进行安全检查和robots.txt验证
        if not self.check_robots_txt(catalog_url):
            safe_print("❌ 安全检查或robots.txt验证失败，拒绝访问")
            return []
            
        return catalog_fetch(
            catalog_url=catalog_url,
            session=self.session,
            detector=self.detector,
            headers=self.headers
        )

    def filter_chapters_by_range(self, chapters: List[ChapterInfo], range_input: str) -> List[ChapterInfo]:
        """
        根据用户输入的范围过滤章节列表
        """
        start, end = utils_parse_range(range_input, len(chapters))
        return chapters[start-1:end]  

    def crawl_single_chapter(self, chapter: ChapterInfo, output_dir: str, silent: bool = False) -> Optional[str]:
        """
        抓取并保存单个章节的入口点。
        该方法调用模块化的章节处理函数。
        """
        return chapter_process_and_save(
            chapter=chapter,
            output_dir=output_dir,
            detector=self.detector,
            session=self.session,
            headers=self.headers,
            silent=silent
        )

    def _fetch_chapter_content(self, chapter_url: str) -> str:
        """获取并拼接单章节所有分页的HTML内容。"""
        return content_fetch_full(
            chapter_url=chapter_url,
            session=self.session,
            detector=self.detector,
            headers=self.headers,
        )

    def crawl_novel(self, catalog_url: str, max_workers: int = 3, chapters: List[ChapterInfo] = None, output_dir: str = None, auto_merge: bool = False, chapter_range: str = None):
        """爬取小说并保存"""
        if not chapters:
            chapters = self.get_chapter_list(catalog_url)
        
        if not chapters:
            return

        # 过滤无效章节
        chapters = catalog_filter_chapters(chapters)

        # 处理用户指定的章节范围
        if chapter_range:
            try:
                start, end = utils_parse_range(chapter_range, len(chapters))
                chapters = chapters[start-1:end]
                safe_print(f"📖 已选择章节范围: {start} 到 {end} (共 {len(chapters)} 章)")
            except ValueError as e:
                safe_print(f"❌ [red]章节范围错误: {e}[/red]")
                return

        original_chapter_count = len(chapters)

        # 获取小说标题，用于生成默认目录名和合并文件名
        self.novel_title = title_get(
            url=catalog_url,
            session=self.session,
            headers=self.headers,
        )
        if not self.novel_title:
            # 如果无法获取标题，则使用URL中的一部分作为后备
            self.novel_title = urlparse(catalog_url).netloc.replace('.', '_')

        if not output_dir:
            output_dir = self._sanitize_filename(self.novel_title)
        os.makedirs(output_dir, exist_ok=True)
        safe_print(f"📁 输出目录: {output_dir}")

        # --- 断点续传核心逻辑 ---
        # 获取已下载章节列表
        downloaded_chapters = utils_get_downloaded(output_dir)
        
        if downloaded_chapters:
            safe_print(f"🔎 检测到 {len(downloaded_chapters)} 个已下载章节，将进行断点续传。")
            chapters_to_download = [
                ch for ch in chapters if self._sanitize_filename(ch.title) not in downloaded_chapters
            ]
            skipped_count = len(chapters) - len(chapters_to_download)
        else:
            chapters_to_download = chapters
            skipped_count = 0

        if not chapters_to_download:
            downloader_stats(0, 0, skipped_count, output_dir, lambda o: utils_get_downloaded(o))
            if auto_merge or self._ask_merge_chapters():
                merger_merge_chapters(
                    output_dir,
                    getattr(self, 'novel_title', None),
                    self._sanitize_filename
                )
            return
        # --- 断点续传核心逻辑结束 ---

        if RICH_AVAILABLE:
            success_count = downloader_progress(
                chapters_to_download, 
                output_dir, 
                max_workers,
                total_chapters=original_chapter_count,
                initial_advance=skipped_count,
                crawl_func=self.crawl_single_chapter
            )
        else:
            success_count = downloader_simple(
                chapters_to_download,
                output_dir,
                max_workers,
                crawl_func=self.crawl_single_chapter
            )

        downloader_stats(
            success_count, 
            len(chapters_to_download), 
            skipped_count, 
            output_dir, 
            lambda o: utils_get_downloaded(o)
        )

        if auto_merge or self._ask_merge_chapters():
            merger_merge_chapters(
                output_dir,
                getattr(self, 'novel_title', None),
                self._sanitize_filename
            )

    def _should_continue_download(self) -> bool:
        """询问用户是否继续下载"""
        if RICH_AVAILABLE:
            from rich.prompt import Confirm
            return Confirm.ask("🤔 是否继续下载剩余章节？[bold green](y/n, 默认y)[/bold green]: ", default=True)
        else:
            return input("🤔 是否继续下载剩余章节？(y/n, 默认y): ").strip().lower() in ['', 'y', 'yes']
    
    def _ask_merge_chapters(self) -> bool:
        """询问用户是否合并章节"""
        if RICH_AVAILABLE and console:
            from rich.panel import Panel
            from rich import box
            from rich.prompt import Confirm
            
            merge_help_text = (
                "将所有下载的章节合并成一个 .txt 文件。\n"
                "• 章节标题将自动格式化\n"
                "• 正文内容将自动缩进\n"
                "• 分页标记和无关内容将被移除"
            )
            
            panel = Panel(
                merge_help_text,
                title="[bold cyan]📚 章节合并功能[/bold cyan]",
                border_style="cyan",
                expand=False
            )
            console.print(panel)
            
            return Confirm.ask("📖 [bold green]是否执行合并？[/bold green]", default=True)
        else:
            print("\n📚 章节合并功能:")
            print("  • 将所有.md章节文件合并为一个.txt文件")
            return input("🤔 是否合并所有章节为一个txt文件？(y/n, 默认n): ").strip().lower() in ['y', 'yes']
    
    @property
    def headers(self) -> dict:
        """获取请求头"""
        return self.session.headers

   