"""章节正文内容抓取、清洗、分页等相关工具集"""
from __future__ import annotations

import re
import urllib.parse
import time
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from ..models import SiteConfig
from .site_detector import SiteDetector
from ..utils import safe_print
from .utils import is_blocked_response as utils_is_blocked_response, detect_encoding as utils_detect_encoding

__all__ = [
    'extract_content',
    'find_next_page',
    'clean_content',
    'fetch_full_chapter_content',
]


def fetch_full_chapter_content(
    chapter_url: str,
    session: requests.Session,
    detector: SiteDetector,
    headers: dict,
) -> str:
    """
    获取单个章节的完整HTML内容，自动处理并拼接章节内的分页。
    """
    full_content = ""
    current_url = chapter_url
    visited_urls = {chapter_url}
    max_pages = 20  # 单章节最大页数限制，防止无限循环
    page_count = 0

    while current_url and page_count < max_pages:
        page_count += 1
        try:
            time.sleep(0.1)  # 礼貌性延迟
            response = session.get(current_url, headers=headers, timeout=15)
            response.raise_for_status()

            if utils_is_blocked_response(response):
                safe_print(f"❌ 访问 {current_url} 被反爬虫机制阻止。")
                return ""

            encoding = utils_detect_encoding(response)
            response.encoding = encoding
            
            soup = BeautifulSoup(response.content, 'html.parser', from_encoding=encoding)
            
            content_html_obj = extract_content(soup, detector, current_url)
            if content_html_obj:
                full_content += str(content_html_obj)

            next_page_url = find_next_page(soup, detector, current_url)

            if next_page_url and next_page_url in visited_urls:
                break
            
            current_url = next_page_url
            if current_url:
                visited_urls.add(current_url)

        except requests.RequestException as e:
            safe_print(f"❌ 获取章节内容页面 {current_url} 失败: {e}")
            return ""
            
    return full_content


def extract_content(soup: BeautifulSoup, detector: SiteDetector, current_url: str = None) -> Optional[Tag]:
    """从 soup 中提取正文内容，返回包含内容的Tag对象。"""
    # 获取网站配置（静默模式，避免重复打印）
    config = detector.detect_site(current_url, silent=True) if current_url else None
    if not config:
        # 使用通用配置作为后备
        config = SiteConfig(
            name='通用配置',
            catalog_selectors=['#content', '.content', 'div.content', '.main'],
            content_selectors=['#content', '.content', 'div.content', '.main'],
            title_selector='h1',
            next_page_patterns=[],
            page_info_pattern=r'',
            filters=[]
        )
    
    # 特殊处理 huanqixiaoshuo.com
    if current_url and 'huanqixiaoshuo.com' in current_url:
        all_divs = soup.find_all("div")
        for div in all_divs:
            if div.get('class') or div.get('id'):
                continue
            paragraphs = div.find_all('p')
            if len(paragraphs) > 3:  # 找到包含多个段落的div
                return div
        return None

    # 通用处理 - 尝试不同的选择器
    for selector in config.content_selectors:
        try:
            content_element = soup.select_one(selector)
            if content_element and content_element.get_text(strip=True):
                return content_element
        except Exception:
            continue
    
    return None


def find_next_page(soup: BeautifulSoup, detector: SiteDetector, current_url: str) -> Optional[str]:
    """查找章节内的下一页链接。"""
    config = detector.detect_site(current_url, silent=True)
    
    # 特殊处理 huanqixiaoshuo.com
    if 'huanqixiaoshuo.com' in current_url:
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.string or ""
            page_match = re.search(r'\((\d+)/(\d+)\)', title_text)
            if page_match:
                current_page, total_pages = int(page_match.group(1)), int(page_match.group(2))
                if current_page < total_pages:
                    next_page = current_page + 1
                    base_url_no_ext = current_url.replace('.html', '')
                    return f"{base_url_no_ext}_{next_page}.html"
        
        for link in soup.find_all("a", href=True):
            if "下一页" in link.get_text(strip=True):
                href = link.get("href")
                if href.startswith("/"):
                    return f"https://www.huanqixiaoshuo.com{href}"
                else:
                    return urllib.parse.urljoin(current_url, href)
        return None

    # 通用处理 - 标题中的页码信息
    title_tag = soup.find('title')
    if title_tag and hasattr(config, 'page_info_pattern') and config.page_info_pattern:
        title_text = title_tag.string or ""
        page_match = re.search(config.page_info_pattern, title_text)
        if page_match and len(page_match.groups()) >= 2:
            current_page, total_pages = int(page_match.group(1)), int(page_match.group(2))
            if current_page < total_pages:
                next_page = current_page + 1
                if hasattr(config, 'next_page_patterns'):
                    for pattern in config.next_page_patterns:
                        try:
                            base_url_no_ext = re.sub(r'\.html$', '', current_url)
                            if '_' in pattern:
                                return f"{base_url_no_ext}_{next_page}.html"
                            else:
                                return f"{base_url_no_ext}/{next_page}.html"
                        except Exception:
                            continue
    
    # 查找"下一页"链接
    next_links = soup.find_all('a', string=re.compile(r'下一页|下页|next', re.I))
    for link in next_links:
        href = link.get('href')
        if href:
            return urllib.parse.urljoin(current_url, href)
    
    return None


def clean_content(content_html: str, detector: SiteDetector, current_url: str = None) -> str:
    """清理HTML内容，转换为纯文本。"""
    if not content_html:
        return ""
    
    config = detector.detect_site(current_url) if current_url else None
    if not config:
        # 使用通用配置作为后备
        config = SiteConfig(
            name='通用配置',
            catalog_selectors=['#content', '.content', 'div.content', '.main'],
            content_selectors=['#content', '.content', 'div.content', '.main'],
            title_selector='h1',
            next_page_patterns=[],
            page_info_pattern=r'',
            filters=[]
        )
    
    # 解析HTML内容
    soup = BeautifulSoup(content_html, 'html.parser')
    
    # 移除导航相关的链接和元素
    for nav_elem in soup.find_all(['a', 'div', 'span'], string=re.compile(r'上一页|下一页|目录|返回|章节目录')):
        nav_elem.decompose()
    
    # 获取文本，保留段落结构
    text = soup.get_text(separator='\n', strip=True)
    
    # 分行处理
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # 跳过空行和过短的行
        if not line or len(line) < 3:
            continue
            
        # 移除HTML实体
        line = re.sub(r'&nbsp;|&lt;|&gt;|&amp;|&quot;', ' ', line)
        
        # 跳过过滤词
        if any(filter_word in line for filter_word in config.filters):
            continue
            
        # 跳过纯数字或符号行
        if re.match(r'^[\d\s\-_\.]+$', line):
            continue
            
        cleaned_lines.append(line)
    
    return '\n\n'.join(cleaned_lines) 