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

from .login_manager import LoginManager
from .models import ChapterInfo, SiteConfig
from .site_detector import SiteDetector
from .utils import (RICH_AVAILABLE, console, file_lock, print_chapter_summary,
                    print_status_table, safe_print)

if RICH_AVAILABLE:
    from rich.progress import (BarColumn, Progress, TextColumn,
                               TimeElapsedColumn, TimeRemainingColumn)


class UniversalNovelCrawler:
    """通用小说爬虫"""
    
    def __init__(self, login_manager: LoginManager, detector: SiteDetector):
        self.login_manager = login_manager
        self.detector = detector
        self.session = self.login_manager.session
    
    def check_robots_txt(self, url: str) -> bool:
        """检查robots.txt是否允许访问"""
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
        """智能检测网页编码"""
        # 1. 尝试从HTTP头获取编码
        content_type = response.headers.get('content-type', '').lower()
        if 'charset=' in content_type:
            charset = content_type.split('charset=')[1].split(';')[0].strip()
            if charset:
                return charset
        
        # 2. 尝试从HTML meta标签获取编码
        content_preview = response.content[:2048]  # 只检查前2KB
        try:
            soup = BeautifulSoup(content_preview, 'html.parser')
            
            # 查找 <meta charset="...">
            meta_charset = soup.find('meta', attrs={'charset': True})
            if meta_charset:
                return meta_charset.get('charset')
            
            # 查找 <meta http-equiv="content-type" content="...">
            meta_content_type = soup.find('meta', attrs={'http-equiv': lambda x: x and x.lower() == 'content-type'})
            if meta_content_type:
                content = meta_content_type.get('content', '').lower()
                if 'charset=' in content:
                    charset = content.split('charset=')[1].split(';')[0].strip()
                    if charset:
                        return charset
        except:
            pass
        
        # 3. 使用chardet自动检测
        try:
            detected = chardet.detect(response.content[:10240])  # 检查前10KB
            if detected and detected['encoding'] and detected['confidence'] > 0.7:
                return detected['encoding']
        except:
            pass
        
        # 4. 默认回退到UTF-8
        return 'utf-8'
    
    def _sanitize_filename(self, text: str) -> str:
        """清理文本作为安全的文件名"""
        return re.sub(r'[\\/*?:"<>|]', "", text).strip()
    
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
    
    def get_downloaded_chapters(self, output_dir: str) -> set:
        """获取已下载的章节标题"""
        if not os.path.exists(output_dir):
            return set()
        
        downloaded = set()
        for filename in os.listdir(output_dir):
            if filename.endswith('.md'):
                # 移除.md后缀，得到章节标题
                title = filename[:-3]
                downloaded.add(title)
        
        return downloaded
    
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
        """获取章节列表的核心逻辑"""
        # 首先检查robots.txt
        if not self.check_robots_txt(catalog_url):
            safe_print("❌ robots.txt 不允许访问，程序退出")
            return []
        
        config = self.detector.detect_site(catalog_url)
        if not config:
            safe_print("❌ 无法识别网站类型")
            return []
        
        try:
            response = self.session.get(catalog_url, timeout=10)
            
            # 智能检测编码
            detected_encoding = self._detect_encoding(response)
            response.encoding = detected_encoding
            safe_print(f"🔍 检测到网页编码: {detected_encoding}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取并保存小说标题（供后续合并使用）
            novel_title = self._extract_novel_title(soup, catalog_url)
            if novel_title:
                self.novel_title = novel_title
            
            chapters = []
            
            # 特殊处理：huanqixiaoshuo.com网站
            if 'huanqixiaoshuo.com' in catalog_url:
                # 查找所有链接
                all_links = soup.find_all("a", href=True)
                for link in all_links:
                    href = link.get("href")
                    text = link.get_text(strip=True)
                    
                    if not text or not href:
                        continue
                    
                    # 处理JavaScript链接
                    if href.startswith("javascript:"):
                        js_match = re.search(r"javascript:gobook\(['\"](\d+)['\"],\s*['\"](\d+)['\"],\s*['\"](\d+)['\"]\)", href)
                        if js_match:
                            book_id = js_match.group(1)  # 通常是 "2"
                            novel_id = js_match.group(2)  # 小说ID
                            chapter_id = js_match.group(3)  # 章节ID
                            chapter_url = f"https://www.huanqixiaoshuo.com/{book_id}_{novel_id}/{chapter_id}.html"
                            chapters.append(ChapterInfo(title=text, url=chapter_url))
                    
                    # 处理普通链接
                    elif "/2_" in href and ".html" in href:
                        if href.startswith("/"):
                            chapter_url = f"https://www.huanqixiaoshuo.com{href}"
                        else:
                            chapter_url = href
                        chapters.append(ChapterInfo(title=text, url=chapter_url))
                
                safe_print(f"✅ 特殊处理huanqixiaoshuo.com找到 {len(chapters)} 个链接")
                
            else:
                # 通用处理逻辑
                # 尝试不同的选择器
                for selector in config.catalog_selectors:
                    try:
                        links = soup.select(selector)
                        if links:
                            safe_print(f"✅ 使用选择器 '{selector}' 找到 {len(links)} 个链接")
                            break
                    except Exception as e:
                        continue
                else:
                    safe_print("❌ 未找到章节链接")
                    return []
                
                base_url = f"{urlparse(catalog_url).scheme}://{urlparse(catalog_url).netloc}"
                
                for link in links:
                    try:
                        title = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        if not title or not href:
                            continue
                        
                        # 构造完整URL
                        if href.startswith('http'):
                            chapter_url = href
                        elif href.startswith('/'):
                            chapter_url = base_url + href
                        else:
                            chapter_url = catalog_url.rstrip('/') + '/' + href.lstrip('/')
                        
                        chapters.append(ChapterInfo(title=title, url=chapter_url))
                        
                    except Exception as e:
                        continue
            
            # 去重和排序
            seen_urls = set()
            unique_chapters = []
            for chapter in chapters:
                if chapter.url not in seen_urls:
                    seen_urls.add(chapter.url)
                    unique_chapters.append(chapter)
            
            safe_print(f"📚 初步获取 {len(unique_chapters)} 个章节链接")
            return unique_chapters
            
        except Exception as e:
            safe_print(f"❌ 获取章节列表失败: {str(e)}")
            return []
    
    def crawl_single_chapter(self, chapter: ChapterInfo, output_dir: str, silent: bool = False) -> Optional[str]:
        """下载并保存单个章节
        
        Args:
            chapter: 章节信息
            output_dir: 输出目录
            silent: 是否静默模式（不输出调试信息）
        """
        
        # 清理标题作为文件名
        safe_title = self._sanitize_filename(chapter.title)
        filename = f"{safe_title}.md"
        filepath = os.path.join(output_dir, filename)
        
        # 使用文件锁确保线程安全
        lock_path = f"{filepath}.lock"
        with file_lock(lock_path):
            # 检查文件是否已存在
            if os.path.exists(filepath):
                return "skipped"
            
            # 获取章节内容
            content = self._fetch_chapter_content(chapter.url, chapter.title, silent=silent)
            if not content:
                return None
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存文件
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# {chapter.title}\n\n{content}")
                return filepath
            except Exception as e:
                if not silent:
                    safe_print(f"❌ 保存文件失败: {e}")
                return None

    def _fetch_chapter_content(self, url: str, chapter_title: str, silent: bool = False) -> Optional[str]:
        """获取章节内容
        
        Args:
            url: 章节URL
            chapter_title: 章节标题
            silent: 是否静默模式（不输出调试信息）
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 检测反爬虫保护
            if self._is_blocked_response(response):
                if not silent:
                    safe_print(f"❌ 网站启用了反爬虫保护 (Cloudflare/其他)")
                return None
            
            # 智能检测编码
            detected_encoding = self._detect_encoding(response)
            response.encoding = detected_encoding
            
            if not silent:
                safe_print(f"🔍 检测到网页编码: {detected_encoding}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检测网站配置
            config = self.detector.detect_site(url)
            if not silent:
                safe_print(f"🎯 检测到网站类型: {config.name}")
            
            all_content = []
            current_url = url
            page_num = 1
            max_pages = 20  # 防止无限循环
            
            while current_url and page_num <= max_pages:
                if page_num > 1:
                    try:
                        response = self.session.get(current_url, timeout=30)
                        response.raise_for_status()
                        
                        # 再次检测反爬虫保护
                        if self._is_blocked_response(response):
                            if not silent:
                                safe_print(f"❌ 第{page_num}页被反爬虫保护拦截")
                            break
                            
                        response.encoding = detected_encoding
                        soup = BeautifulSoup(response.text, 'html.parser')
                    except Exception as e:
                        if not silent:
                            safe_print(f"❌ 获取第{page_num}页失败: {e}")
                        break
                
                # 提取当前页内容
                content = self._extract_content(soup, config)
                if content:
                    all_content.extend(content)
                    if not silent:
                        safe_print(f"    📄 第{page_num}页: 提取了 {len(content)} 个段落")
                else:
                    if not silent:
                        safe_print(f"    ⚠️ 第{page_num}页: 未找到内容")
                    break
                
                # 查找下一页
                next_url = self._find_next_page(soup, current_url, config)
                if not next_url or next_url == current_url:
                    break
                    
                current_url = next_url
                page_num += 1
                
                # 延迟避免请求过快
                time.sleep(random.uniform(0.5, 1.5))
            
            if all_content:
                # 清理内容
                cleaned_content = self._clean_content(all_content, config)
                return '\n\n'.join(cleaned_content)
            else:
                if not silent:
                    safe_print(f"❌ 章节 '{chapter_title}' 内容为空")
                return None
                
        except Exception as e:
            if not silent:
                safe_print(f"❌ 获取章节内容失败: {e}")
            return None
    
    def _is_blocked_response(self, response) -> bool:
        """检测是否被反爬虫保护拦截"""
        # 检测Cloudflare验证页面
        if response.status_code == 403:
            return True
        
        # 检测Cloudflare特征
        content_lower = response.text.lower()
        cloudflare_indicators = [
            "just a moment",
            "checking your browser",
            "cloudflare",
            "ddos protection",
            "security check",
            "human verification"
        ]
        
        if any(indicator in content_lower for indicator in cloudflare_indicators):
            return True
        
        # 检测其他反爬虫保护
        if len(response.text) < 500 and ("blocked" in content_lower or "forbidden" in content_lower):
            return True
            
        return False
    
    def _extract_content(self, soup: BeautifulSoup, config: SiteConfig) -> List[str]:
        """提取页面内容"""
        content_paragraphs = []
        
        # 特殊处理
        if hasattr(self, '_current_url') and 'huanqixiaoshuo.com' in self._current_url:
            # 查找所有无class和id属性的div，收集其中的段落内容
            all_divs = soup.find_all("div")
            for div in all_divs:
                # 只处理无特定class或id的div
                if div.get('class') or div.get('id'):
                    continue
                
                # 查找div中的段落
                paragraphs = div.find_all('p')
                for p in paragraphs:
                    p_text = p.get_text(separator='\n', strip=True)
                    # 跳过导航相关的段落
                    if any(nav_text in p_text for nav_text in ['上一章', '目录', '下一页', '上一页', '下一章']):
                        continue
                    # 跳过提示性文字
                    if any(tip_text in p_text for tip_text in ['本章尚未完结', '请点击下一页', '本章已阅读完毕', '关闭']):
                        continue
                    # 跳过太短的段落（可能是导航或广告）
                    if len(p_text) < 10:
                        continue
                    
                    content_paragraphs.append(p_text)
            
            return content_paragraphs
        
        # 通用处理逻辑
        # 尝试不同的内容选择器
        for selector in config.content_selectors:
            try:
                if selector == 'div:not([id]):not([class])':
                    # 查找无id/class的div
                    all_divs = soup.find_all("div")
                    for div in all_divs:
                        if div.get('class') or div.get('id'):
                            continue
                        paragraphs = div.find_all('p')
                        if len(paragraphs) > 3:  # 内容区域通常有多个段落
                            for p in paragraphs:
                                p_text = p.get_text(separator='\n', strip=True)
                                if p_text and not any(filter_text in p_text for filter_text in config.filters):
                                    content_paragraphs.append(p_text)
                            if content_paragraphs:
                                break
                else:
                    # 使用CSS选择器
                    content_div = soup.select_one(selector)
                    if content_div:
                        # 提取文本段落
                        for elem in content_div.find_all(['p', 'div', 'br']):
                            text = elem.get_text(separator='\n', strip=True)
                            if text and not any(filter_text in text for filter_text in config.filters):
                                content_paragraphs.append(text)
                        if content_div.get_text(separator='\n', strip=True):
                            # 如果没有子元素，直接获取文本
                            lines = content_div.get_text(separator='\n').split('\n')
                            for line in lines:
                                line = line.strip()
                                if line and not any(filter_text in line for filter_text in config.filters):
                                    content_paragraphs.append(line)
                
                if content_paragraphs:
                    break
                    
            except Exception:
                continue
        
        return content_paragraphs
    
    def _find_next_page(self, soup: BeautifulSoup, current_url: str, config: SiteConfig) -> Optional[str]:
        """查找下一页URL"""
        # 特殊处理：huanqixiaoshuo.com网站 - 使用老版本完全相同的逻辑
        if 'huanqixiaoshuo.com' in current_url:
            # 方法1：从页面标题中获取页码信息并构造下一页URL
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.string or ""
                # 查找(当前页/总页数)格式，如(1/3)
                page_match = re.search(r'\((\d+)/(\d+)\)', title_text)
                if page_match:
                    current_page = int(page_match.group(1))
                    total_pages = int(page_match.group(2))
                    
                    safe_print(f"    页面标题显示：第{current_page}页，共{total_pages}页")
                    
                    if current_page < total_pages:
                        # 构造下一页URL
                        next_page = current_page + 1
                        # 从current_url中去掉.html后缀
                        base_url_no_ext = current_url.replace('.html', '')
                        next_page_url = f"{base_url_no_ext}_{next_page}.html"
                        safe_print(f"    构造下一页URL: {next_page_url}")
                        return next_page_url

            # 方法2：如果方法1失败，查找"下一页"链接
            for link in soup.find_all("a", href=True):
                link_text = link.get_text(strip=True)
                if "下一页" in link_text:
                    href = link.get("href")
                    if href.startswith("/"):
                        next_page_url = f"https://www.huanqixiaoshuo.com{href}"
                    else:
                        next_page_url = urllib.parse.urljoin(current_url, href)
                    return next_page_url
            
            return None
        
        # 通用处理逻辑（保持原有逻辑）
        # 方法1: 从标题获取页码信息
        title_tag = soup.find('title')
        if title_tag and config.page_info_pattern:
            title_text = title_tag.string or ""
            page_match = re.search(config.page_info_pattern, title_text)
            if page_match:
                current_page = int(page_match.group(1))
                total_pages = int(page_match.group(2))
                
                if current_page < total_pages:
                    # 构造下一页URL
                    next_page = current_page + 1
                    for pattern in config.next_page_patterns:
                        try:
                            base_url_no_ext = re.sub(r'\.html$', '', current_url)
                            if '_' in pattern:
                                next_page_url = f"{base_url_no_ext}_{next_page}.html"
                            else:
                                next_page_url = f"{base_url_no_ext}/{next_page}.html"
                            return next_page_url
                        except:
                            continue
        
        # 方法2: 查找"下一页"链接
        next_links = soup.find_all('a', string=re.compile(r'下一页|下页|next', re.I))
        for link in next_links:
            href = link.get('href')
            if href:
                if href.startswith('http'):
                    return href
                elif href.startswith('/'):
                    parsed_url = urlparse(current_url)
                    return f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                else:
                    return urllib.parse.urljoin(current_url, href)
        
        return None
    
    def _clean_content(self, content_list: List[str], config: SiteConfig) -> List[str]:
        """清理内容"""
        cleaned = []
        for line in content_list:
            # 清理HTML标签和特殊字符
            line = re.sub(r'<[^>]+>', '', line)
            line = re.sub(r'&nbsp;|&lt;|&gt;|&amp;', ' ', line)
            # 只压缩空格和制表符，保留换行符
            line = re.sub(r'[ \t]+', ' ', line)
            line = line.strip()
            
            # 过滤无效内容
            if (line and 
                len(line) > 5 and  # 太短的行
                not any(filter_text in line for filter_text in config.filters) and
                not re.match(r'^[\d\s\-_]+$', line)):  # 纯数字或符号
                cleaned.append(line)
        
        return cleaned
    
    def parse_chapter_range(self, range_input: str, total_chapters: int) -> Tuple[int, int]:
        """解析章节范围输入"""
        if not range_input.strip():
            return 0, total_chapters
        
        range_input = range_input.strip()
        
        try:
            # 格式1: "100-200" 或 "100:200"
            if '-' in range_input or ':' in range_input:
                separator = '-' if '-' in range_input else ':'
                parts = range_input.split(separator)
                
                if len(parts) == 2:
                    start_str, end_str = parts
                    
                    # 处理起始位置
                    if start_str.strip():
                        start = int(start_str.strip())
                        start = max(1, start)  # 最小为1
                    else:
                        start = 1
                    
                    # 处理结束位置
                    if end_str.strip():
                        end = int(end_str.strip())
                        end = min(end, total_chapters)  # 最大为总章节数
                    else:
                        end = total_chapters
                    
                    # 转换为0基索引
                    return start - 1, end
            
            # 格式2: "100+" 表示从第100章开始
            elif range_input.endswith('+'):
                start = int(range_input[:-1].strip())
                start = max(1, start)
                return start - 1, total_chapters
            
            # 格式3: 单个数字，表示只下载这一章
            else:
                chapter_num = int(range_input)
                chapter_num = max(1, min(chapter_num, total_chapters))
                return chapter_num - 1, chapter_num
                
        except ValueError:
            safe_print(f"❌ 无法解析章节范围: {range_input}")
            return 0, total_chapters
    
    def filter_chapters_by_range(self, chapters: List[ChapterInfo], range_input: str) -> List[ChapterInfo]:
        """根据用户输入过滤章节"""
        if not range_input.strip():
            return chapters
        
        total_chapters = len(chapters)
        start_idx, end_idx = self.parse_chapter_range(range_input, total_chapters)
        
        # 验证范围
        if start_idx >= end_idx or start_idx >= total_chapters:
            safe_print(f"❌ 无效的章节范围，总共有 {total_chapters} 章")
            return chapters
        
        filtered_chapters = chapters[start_idx:end_idx]
        safe_print(f"📖 选择章节范围: 第{start_idx + 1}-{end_idx}章 (共{len(filtered_chapters)}章)")
        
        return filtered_chapters
    
    def crawl_novel(self, catalog_url: str, max_workers: int = 3, chapters: List[ChapterInfo] = None, output_dir: str = None, auto_merge: bool = False):
        """爬取小说并保存"""
        if not chapters:
            safe_print("❌ 未提供章节列表，无法继续。")
            return

        original_chapter_count = len(chapters)

        if not output_dir:
            parsed_url = urlparse(catalog_url)
            site_name = parsed_url.netloc.replace('www.', '').replace('.', '_')
            output_dir = f"novels_{site_name}"
        
        Path(output_dir).mkdir(exist_ok=True)
        safe_print(f"📁 输出目录: {output_dir}")

        # --- 断点续传核心逻辑 ---
        # 如果跳过文件检查，直接下载所有章节
        if getattr(self, 'skip_check_files', False):
            safe_print("⚠️ 已跳过文件检查，将重新下载所有章节")
            chapters_to_download = chapters
            skipped_count = 0
        else:
            downloaded_titles = self.get_downloaded_chapters(output_dir)
            chapters_to_download = [
                ch for ch in chapters if self._sanitize_filename(ch.title) not in downloaded_titles
            ]
            skipped_count = original_chapter_count - len(chapters_to_download)

            if skipped_count > 0:
                safe_print(f"🔄 检测到 {skipped_count} 个已下载章节，将自动跳过。")

            if not chapters_to_download:
                safe_print("✅ 所有章节均已在本地，无需下载。")
                self._show_completion_stats(0, 0, skipped_count, output_dir)
                if auto_merge or self._ask_merge_chapters():
                    self.merge_chapters_to_txt(output_dir)
                return
        # --- 断点续传核心逻辑结束 ---

        if RICH_AVAILABLE:
            success_count = self._download_chapters_with_progress(
                chapters_to_download, 
                output_dir, 
                max_workers,
                total_chapters=original_chapter_count,
                initial_advance=skipped_count
            )
        else:
            success_count = self._download_chapters_simple(chapters_to_download, output_dir, max_workers)

        self._show_completion_stats(success_count, len(chapters_to_download), skipped_count, output_dir)

        if auto_merge or self._ask_merge_chapters():
            self.merge_chapters_to_txt(output_dir)

    def _should_continue_download(self) -> bool:
        """询问用户是否继续下载"""
        if RICH_AVAILABLE:
            from rich.prompt import Confirm
            return Confirm.ask("🤔 是否继续下载剩余章节？[bold green](y/n, 默认y)[/bold green]: ", default=True)
        else:
            return input("🤔 是否继续下载剩余章节？(y/n, 默认y): ").strip().lower() in ['', 'y', 'yes']
    
    def _ask_merge_chapters(self) -> bool:
        """询问是否合并章节"""
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
    
    def _download_chapters_with_progress(self, chapters: List[ChapterInfo], output_dir: str, max_workers: int, total_chapters: int, initial_advance: int) -> int:
        """使用rich进度条下载章节"""
        progress = Progress(
            TextColumn("[bold blue]下载进度", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TextColumn("[green]{task.completed} of {task.total}"),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
            transient=False,  # Keep progress bar after completion
            console=console
        )

        success_count = 0
        error_messages = []  # 收集错误信息，最后统一显示
        
        with progress:
            task = progress.add_task("下载中...", total=total_chapters)
            progress.advance(task, advance=initial_advance)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_chapter = {
                    executor.submit(self.crawl_single_chapter, chapter, output_dir, silent=True): chapter
                    for chapter in chapters
                }

                for future in as_completed(future_to_chapter):
                    chapter = future_to_chapter[future]
                    try:
                        result = future.result()
                        if result and result != "skipped":
                            success_count += 1
                    except Exception as e:
                        error_messages.append(f"❌ 下载章节 '{chapter.title}' 时发生错误: {e}")
                    finally:
                        progress.advance(task, advance=1)
        
        # 下载完成后显示错误信息
        if error_messages:
            safe_print("\n" + "\n".join(error_messages[:5]))  # 只显示前5个错误
            if len(error_messages) > 5:
                safe_print(f"... 还有 {len(error_messages) - 5} 个错误未显示")
                
        return success_count

    def _download_chapters_simple(self, chapters: List[ChapterInfo], output_dir: str, max_workers: int) -> int:
        """不使用rich进度条的简单下载模式"""
        success_count = 0
        total_count = len(chapters)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chapter = {
                executor.submit(self.crawl_single_chapter, chapter, output_dir): chapter
                for chapter in chapters
            }

            for i, future in enumerate(as_completed(future_to_chapter)):
                chapter = future_to_chapter[future]
                try:
                    result = future.result()
                    if result and result != "skipped":
                        success_count += 1
                    safe_print(f"[{i + 1}/{total_count}] {'✅' if result else '❌'} 下载: {chapter.title}")
                except Exception as e:
                    safe_print(f"[{i + 1}/{total_count}] ❌ 下载章节 '{chapter.title}' 失败: {e}")
        
        return success_count

    def _show_completion_stats(self, success_count: int, total_count: int, skipped_count: int, output_dir: str):
        """显示下载完成后的统计信息"""
        failure_count = total_count - success_count
        
        if not RICH_AVAILABLE:
            safe_print("\n" + "="*20)
            safe_print("下载完成!")
            safe_print(f"成功: {success_count}")
            if failure_count > 0:
                safe_print(f"失败: {failure_count}")
            if skipped_count > 0:
                safe_print(f"跳过: {skipped_count}")
            safe_print(f"总计: {success_count + failure_count + skipped_count}")
            safe_print(f"文件保存在: {output_dir}")
            safe_print("="*20)
            return
            
        from rich.table import Table
        from rich.panel import Panel

        stats_table = Table(title="📊 下载统计", show_header=False, box=None)
        stats_table.add_column(style="green")
        stats_table.add_column(style="bold magenta")
        
        stats_table.add_row("✅ 成功下载:", f"{success_count} 章")
        if failure_count > 0:
            stats_table.add_row("❌ 下载失败:", f"[red]{failure_count} 章[/red]")
        if skipped_count > 0:
            stats_table.add_row("🔄 已跳过:", f"{skipped_count} 章")

        stats_table.add_row("💾 保存位置:", f"[cyan]{output_dir}[/cyan]")
        
        total_chapters_in_dir = len(self.get_downloaded_chapters(output_dir))
        stats_table.add_row("📁 目录总数:", f"{total_chapters_in_dir} 章")

        panel = Panel(
            stats_table,
            title="🎉 [bold green]下载完成[/bold green] 🎉",
            expand=False,
            border_style="green"
        )
        console.print(panel)

    def filter_valid_chapters(self, chapters: List[ChapterInfo]) -> List[ChapterInfo]:
        """过滤有效的章节链接."""
        filtered_chapters = []

        exclude_keywords = [
            '书架', '推荐', '排行', '书单', '登录', '注册', '充值',
            '签到', '作者', '简介', '目录', '设置', '关于'
        ]
        
        chapter_patterns = [
            r'第\s*[一二三四五六七八九十百千万\d]+\s*[章章节卷]',
            r'^\d+$' # 纯数字标题
        ]

        for chapter in chapters:
            title = chapter.title.strip()
            
            if not title or any(keyword in title for keyword in exclude_keywords):
                continue
            
            if len(title) > 50: # 标题过长
                continue

            # 必须包含章节标识或为短数字标题
            if any(re.search(p, title) for p in chapter_patterns) or len(title) < 5:
                 filtered_chapters.append(chapter)

        return filtered_chapters
        
    def extract_chapter_number(self, filename: str):
        """从文件名中提取章节号用于排序"""
        # 匹配 "第123章", "章123", "123"
        matches = re.findall(r'(\d+)', filename)
        if matches:
            return int(matches[0])
        return 99999 # 无法解析的排在后面

    def _normalize_title(self, raw_title: str) -> str:
        """标准化章节标题为『第xx章 章节名』格式"""
        raw_title = raw_title.strip()
        m = re.match(r'(第[\u4e00-\u9fa5\d]+[章节卷])\s*[:：_-]*\s*(.*)', raw_title)
        if m:
            number_part = m.group(1)
            name_part = m.group(2).strip()
            return f"{number_part} {name_part}" if name_part else number_part
        # 若无法解析则直接返回原标题
        return raw_title

    def clean_merge_content(self, content: str) -> str:
        """清理用于合并的单章内容，保留段落空行，并规范标题格式"""
        # 拆分行，保留空行信息
        lines = content.split('\n')

        # 处理标题
        title = ""
        if lines and lines[0].startswith('# '):
            title = self._normalize_title(lines[0][2:].strip())
            lines = lines[1:]  # 去掉标题行

        output_lines = []
        if title:
            output_lines.append(title)
            output_lines.append("")  # 标题后空行

        previous_blank = False
        for raw in lines:
            line = raw.rstrip()  # 保留段内空格左侧剔除右侧\n
            if not line.strip():
                # 空行: 保证段落之间只有一个空行
                if not previous_blank and output_lines:
                    output_lines.append("")
                    previous_blank = True
                continue

            previous_blank = False
            output_lines.append(line.strip())

        return '\n'.join(output_lines)

    def merge_chapters_to_txt(self, output_dir: str) -> bool:
        """将所有章节文件合并成一个txt文件"""
        chapters_dir = Path(output_dir)
        novel_name = getattr(self, 'novel_title', None)
        if not novel_name:
            novel_name = chapters_dir.name.replace('novels_', '')

        # 生成安全文件名
        safe_novel_name = self._sanitize_filename(novel_name)
        output_file = chapters_dir.parent / f"{safe_novel_name}.txt"
        
        md_files = sorted(list(chapters_dir.glob("*.md")), key=lambda f: self.extract_chapter_number(f.name))

        if not md_files:
            safe_print(f"❌ 在 '{output_dir}' 中未找到章节文件。", style="bold red")
            return False

        safe_print(f"🔄 开始合并 {len(md_files)} 个章节到 '{output_file.name}'...")
        
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        cleaned_content = self.clean_merge_content(content)
                        outfile.write(cleaned_content)
                        outfile.write('\n\n')
                except Exception as e:
                    safe_print(f"⚠️ 读取或处理文件 '{md_file.name}' 失败: {e}", style="yellow")
        
        safe_print(f"✅ 合并完成！", style="bold green")
        return True

    def _extract_novel_title(self, soup: BeautifulSoup, catalog_url: str) -> Optional[str]:
        """尝试从目录页提取小说标题

        优先级:
        1. OpenGraph 元数据 og:novel:book_name
        2. 常见的 <h1> 标签 (id 或 class 含有 title / book / name)
        3. <title> 标签 — 去掉网站名等多余信息
        """
        # 1) og:novel:book_name
        meta_book = soup.find('meta', attrs={'property': 'og:novel:book_name'})
        if meta_book and meta_book.get('content'):
            return meta_book.get('content').strip()

        # 2) 常见的 <h1> 标签
        h1_candidates = soup.find_all('h1')
        for h1 in h1_candidates:
            h1_text = h1.get_text(strip=True)
            if 0 < len(h1_text) < 50:  # 简单限定长度
                if any(keyword in h1_text for keyword in ['最新章节', '章节', '>>']):
                    # 过滤可能的说明性文字
                    continue
                return h1_text

        # 3) <title> 标题 — 去掉分隔符后的站点信息
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            raw_title = title_tag.string.strip()
            # 常见分隔符
            for sep in ['_', '-', '|', '－', '—']:
                if sep in raw_title:
                    raw_title = raw_title.split(sep)[0].strip()
                    break
            if raw_title:
                return raw_title

        return None

   