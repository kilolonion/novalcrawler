"""目录页相关工具/逻辑"""
from __future__ import annotations

import re
import urllib.parse
from typing import Optional, List
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from ..models import ChapterInfo
from .site_detector import SiteDetector
from ..utils import console, safe_print
from .utils import is_blocked_response as utils_is_blocked_response


__all__ = [
    'find_next_catalog_page',
    'fetch_and_parse_catalog',
    'filter_valid_chapters',
]


def filter_valid_chapters(chapters: List[ChapterInfo]) -> List[ChapterInfo]:
    """过滤掉标题看起来像说明或广告的无效章节"""
    
    # 关键字黑名单，匹配到任何一个词则认为可能是无效章节
    BLACKLIST_KEYWORDS = [
        '公告', '通知', '说明', '必看', '必读', '重要', '最新',
        '作品相关', '设定', '人物', '地图', '年表', '附录',
        '上架感言', '完本感言', '感谢', '求票', '推荐',
        'review', 'notice', 'announcement', 'author'
    ]
    
    # 正则表达式，匹配纯数字、乱码或过短的标题
    INVALID_TITLE_PATTERN = re.compile(
        r"^\d+$|"  # 纯数字
        r"^[a-zA-Z0-9\s\W]{1,5}$|"  # 英文乱码或过短标题
        r"^第?[一二三四五六七八九十百千万\d]+[章回节]$"  # 只有章节号，没有标题
    )

    valid_chapters = []
    for chapter in chapters:
        title = chapter.title.lower().strip()
        if any(keyword in title for keyword in BLACKLIST_KEYWORDS):
            continue
        if INVALID_TITLE_PATTERN.match(title):
            continue
        valid_chapters.append(chapter)
            
    if len(valid_chapters) < len(chapters):
        safe_print(f"ℹ️ 已自动过滤 {len(chapters) - len(valid_chapters)} 个非正文章节（如公告、感言等）。")
        
    return valid_chapters


def find_next_catalog_page(soup: BeautifulSoup, detector: SiteDetector, base_url: str) -> Optional[str]:
    """根据 HTML soup 查找目录页的『下一页』链接。
    逻辑从原 `crawler.py` 中抽离，保持原有行为不变。"""
    # 先找典型的"下一页"按钮/链接
    link = soup.find('a', string=re.compile(r'下一[页頁]|下页|next', re.I))
    if link and link.get('href'):
        href = link['href']
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{href}"
        else:
            return urllib.parse.urljoin(base_url, href)

    # 针对海外书包等使用<select id="indexselect">
    select = soup.find('select', id=re.compile(r'indexselect', re.I))
    if select:
        options = select.find_all('option')
        next_flag = False
        for opt in options:
            if opt.has_attr('selected'):
                next_flag = True
                continue
            if next_flag:
                val = opt.get('value')
                if val:
                    if val.startswith('http'):
                        return val
                    elif val.startswith('/'):
                        parsed = urlparse(base_url)
                        return f"{parsed.scheme}://{parsed.netloc}{val}"
                    else:
                        return urllib.parse.urljoin(base_url, val)
    return None


def fetch_and_parse_catalog(
    catalog_url: str,
    session: requests.Session,
    detector: SiteDetector,
    headers: dict,
) -> List[ChapterInfo]:
    """
    获取并解析目录页，支持翻页，返回完整的章节列表。
    """
    # 检测网站并获取配置
    site_config = detector.detect_site(catalog_url)
    if not site_config:
        safe_print("❌ [bold red]错误: 无法检测网站类型。[/bold red]")
        return []
    
    chapters: List[ChapterInfo] = []
    visited_urls = {catalog_url}
    current_url: Optional[str] = catalog_url
    page_num = 1

    with console.status("[bold green]正在解析目录...", spinner="dots") as status:
        while current_url:
            status.update(f"[bold green]正在解析目录 第 {page_num} 页: {current_url}")
            try:
                response = session.get(current_url, headers=headers, timeout=15)
                response.raise_for_status()

                if utils_is_blocked_response(response):
                    safe_print(f"❌ [bold red]错误: 访问 {current_url} 被目标网站的反爬虫机制阻止。[/bold red]")
                    break

                soup = BeautifulSoup(response.content, 'html.parser')
                page_chapters: List[ChapterInfo] = []

                # 尝试使用配置的选择器直接找链接
                found_links = []
                for selector in site_config.catalog_selectors:
                    links = soup.select(selector)
                    if links:
                        # 如果选择器直接选中了a标签，直接使用
                        if links[0].name == 'a':
                            found_links = links
                            break
                        # 否则在选中的容器内找a标签
                        else:
                            for container in links:
                                found_links.extend(container.find_all('a', href=True))
                            if found_links:
                                break

                for link in found_links:
                    href = link.get('href', '')
                    title = link.get_text(strip=True)
                    if title and href and not href.startswith(('javascript:', '#')):
                        absolute_url = urljoin(current_url, href)
                        page_chapters.append(ChapterInfo(title=title, url=absolute_url))

                if not page_chapters:
                    safe_print(f"⚠️ [yellow]警告: 在目录页 {current_url} 未找到任何章节链接。[/yellow]")

                chapters.extend(page_chapters)

                next_page_url = find_next_catalog_page(soup, detector, current_url)

                if next_page_url and next_page_url in visited_urls:
                    safe_print(f"⚠️ [yellow]警告: 检测到目录页循环，已在 {next_page_url} 停止。[/yellow]")
                    break

                current_url = next_page_url
                if current_url:
                    visited_urls.add(current_url)
                    page_num += 1

            except requests.RequestException as e:
                safe_print(f"❌ [bold red]错误: 获取目录页面 {current_url} 失败: {e}[/bold red]")
                break

    unique_chapters_map = {chapter.url: chapter for chapter in reversed(chapters)}
    unique_chapters = list(reversed(unique_chapters_map.values()))

    if not unique_chapters:
        safe_print("❌ [bold red]错误: 未能从目录页获取到任何有效章节。请检查URL和网站配置。[/bold red]")
    else:
        safe_print(f"✅ [green]目录解析完成，共找到 {len(unique_chapters)} 个章节。[/green]")

    return unique_chapters