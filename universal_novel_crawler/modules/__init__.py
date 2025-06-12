from __future__ import annotations

# 新的模块包，汇聚拆分后的子模块
from .utils import (
    detect_encoding, 
    sanitize_filename, 
    is_blocked_response,
    get_downloaded_chapters,
    parse_chapter_range,
)
from .catalog import (
    find_next_catalog_page, 
    fetch_and_parse_catalog,
    filter_valid_chapters,
)
from .content import extract_content, find_next_page, clean_content, fetch_full_chapter_content
from .merger import merge_chapters_to_txt
from .downloader import (
    download_chapters_with_progress,
    download_chapters_simple,
    show_completion_stats,
)
from .processor import process_and_save_chapter
from .title_extractor import get_novel_title
from .site_detector import SiteDetector
from .login_manager import LoginManager

__all__ = [
    'detect_encoding',
    'sanitize_filename',
    'is_blocked_response',
    'get_downloaded_chapters',
    'parse_chapter_range',
    
    'find_next_catalog_page',
    'fetch_and_parse_catalog',
    'filter_valid_chapters',
    
    'extract_content',
    'find_next_page',
    'clean_content',
    'fetch_full_chapter_content',
    
    'merge_chapters_to_txt',
    
    'download_chapters_with_progress',
    'download_chapters_simple',
    'show_completion_stats',
    
    'process_and_save_chapter',
    
    'get_novel_title',
    
    'SiteDetector',
    'LoginManager',
] 