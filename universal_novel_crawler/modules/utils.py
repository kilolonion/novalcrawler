"""crawler 专用工具函数"""
from __future__ import annotations

import os
import re
from typing import Optional, List, Tuple
from urllib.parse import urlparse

import chardet
from bs4 import BeautifulSoup

__all__ = [
    'sanitize_filename',
    'detect_encoding',
    'is_blocked_response',
    'get_downloaded_chapters',
    'parse_chapter_range',
]


def sanitize_filename(text: str) -> str:
    """清理文本作为安全的文件名 (跨平台字符过滤)"""
    return re.sub(r'[\\/*?:"<>|]', "", text).strip()


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


def detect_encoding(response) -> str:  # type: ignore[Any]
    """智能检测网页编码。
    复制自原 `_detect_encoding`，保持完全兼容。"""
    # 1. HTTP 头
    content_type = response.headers.get('content-type', '').lower()
    if 'charset=' in content_type:
        charset = content_type.split('charset=')[1].split(';')[0].strip()
        if charset:
            return charset

    # 2. meta 标签
    content_preview = response.content[:2048]
    try:
        soup = BeautifulSoup(content_preview, 'html.parser')
        meta_charset = soup.find('meta', attrs={'charset': True})
        if meta_charset:
            return meta_charset.get('charset')  # type: ignore[return-value]
        meta_content_type = soup.find('meta', attrs={'http-equiv': lambda x: x and x.lower() == 'content-type'})
        if meta_content_type:
            content = meta_content_type.get('content', '').lower()
            if 'charset=' in content:
                charset = content.split('charset=')[1].split(';')[0].strip()
                if charset:
                    return charset
    except Exception:
        pass

    # 3. chardet
    try:
        detected = chardet.detect(response.content[:10240])
        if detected and detected['encoding'] and detected['confidence'] > 0.7:
            return detected['encoding']  # type: ignore[return-value]
    except Exception:
        pass

    # 4. 默认 UTF-8
    return 'utf-8'


def is_blocked_response(response) -> bool:  # type: ignore[Any]
    """检测是否被常见反爬虫(Cloudflare等)拦截"""
    if response.status_code == 403:
        return True

    content_lower = response.text.lower()
    cloudflare_indicators = [
        "just a moment",
        "checking your browser",
        "cloudflare",
        "ddos protection",
        "security check",
        "human verification",
    ]
    if any(ind in content_lower for ind in cloudflare_indicators):
        return True

    # 简易长度 + 关键词
    if len(response.text) < 500 and ("blocked" in content_lower or "forbidden" in content_lower):
        return True

    return False 