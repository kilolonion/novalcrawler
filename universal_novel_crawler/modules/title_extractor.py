"""小说标题提取逻辑"""

from __future__ import annotations
from typing import Optional
import re

import requests
from bs4 import BeautifulSoup

from ..utils import safe_print

__all__ = ['get_novel_title']


def extract_novel_title_from_soup(soup: BeautifulSoup) -> Optional[str]:
    """从BeautifulSoup对象中提取小说标题"""
    # 优先尝试 meta 标签 (og:title)
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title['content'].strip()
        
    # 其次尝试 meta 标签 (og:novel:book_name) - 针对特定网站
    og_book_name = soup.find('meta', property='og:novel:book_name')
    if og_book_name and og_book_name.get('content'):
        return og_book_name['content'].strip()

    # 再次尝试 h1 标签
    h1_title = soup.find('h1')
    if h1_title:
        return h1_title.get_text(strip=True)

    # 最后尝试 title 标签
    if soup.title and soup.title.string:
        # 清理标题，移除网站后缀等常见干扰词
        title_text = soup.title.string.strip()
        # 移除括号及其内容
        title_text = re.sub(r'[\(（].*?[\)）]', '', title_text)
        seps = ['-', '_', '|', '—', '::']
        for sep in seps:
            if sep in title_text:
                # 取最长的一段作为标题，避免取到"最新章节"等词
                parts = [p.strip() for p in title_text.split(sep)]
                title_text = max(parts, key=len)
        return title_text

    return None


def get_novel_title(url: str, session: requests.Session, headers: dict) -> Optional[str]:
    """获取并解析页面以提取小说标题"""
    try:
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        # 使用内置的 html.parser 解析器，确保兼容性
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = extract_novel_title_from_soup(soup)
        if title:
            safe_print(f"✅ 成功提取到小说标题: [bold cyan]{title}[/bold cyan]")
            return title
        else:
            safe_print("⚠️ [yellow]未能自动提取小说标题，将使用默认名称。[/yellow]")
            return None
            
    except requests.RequestException as e:
        safe_print(f"❌ [red]获取标题页面失败: {e}[/red]")
        return None
    except Exception as e:
        safe_print(f"❌ [red]解析标题时发生错误: {e}[/red]")
        return None
