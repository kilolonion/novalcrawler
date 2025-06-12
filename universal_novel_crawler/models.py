from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class ChapterInfo:
    title: str
    url: str

@dataclass
class SiteConfig:
    name: str
    catalog_selectors: List[str]  # 目录页章节链接选择器
    content_selectors: List[str]  # 内容页文本选择器
    title_selector: str  # 标题选择器
    next_page_patterns: List[str]  # 下一页URL模式
    page_info_pattern: str  # 页码信息正则
    filters: List[str]  # 需要过滤的文本

@dataclass
class LoginConfig:
    """登录配置"""
    mode: str = 'none'  # none, credentials, cookies, browser_cookies, browser_login
    username: Optional[str] = None
    password: Optional[str] = None
    cookies: Optional[Dict[str, str]] = None
    browser: str = 'auto'  # auto, chrome, edge
    login_url: str = ""
    verify_url: str = "" 