"""单个章节的处理、保存逻辑"""

from __future__ import annotations
import os
from typing import Optional
import atexit
import signal
import threading

import requests
from filelock import FileLock

from ..models import ChapterInfo
from .site_detector import SiteDetector
from ..utils import safe_print
from .utils import sanitize_filename
from .content import clean_content, fetch_full_chapter_content


__all__ = ['process_and_save_chapter', 'cleanup_lock_files']

# 全局锁文件跟踪
_active_locks = set()
_lock_registry_lock = threading.Lock()

def _register_lock(lock_file: str):
    """注册活跃的锁文件"""
    with _lock_registry_lock:
        _active_locks.add(lock_file)

def _unregister_lock(lock_file: str):
    """注销锁文件"""
    with _lock_registry_lock:
        _active_locks.discard(lock_file)
        # 确保锁文件被删除
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except OSError:
            pass  # 文件可能已被其他进程删除

def cleanup_lock_files():
    """清理所有残留的锁文件"""
    with _lock_registry_lock:
        for lock_file in list(_active_locks):
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                    safe_print(f"🧹 已清理残留锁文件: {lock_file}")
            except OSError as e:
                safe_print(f"⚠️ 无法删除锁文件 {lock_file}: {e}")
        _active_locks.clear()

def _signal_handler(signum, frame):
    """信号处理器，确保程序退出时清理锁文件"""
    cleanup_lock_files()

# 注册清理函数和信号处理器
atexit.register(cleanup_lock_files)
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)

def process_and_save_chapter(
    chapter: ChapterInfo,
    output_dir: str,
    detector: SiteDetector,
    session: requests.Session,
    headers: dict,
    silent: bool = False,
) -> Optional[str]:
    """
    完整的处理单个章节的流程：抓取、清洗、保存。
    返回 "success", "skipped", 或 None (代表失败).
    """
    filename = f"{sanitize_filename(chapter.title)}.md"
    filepath = os.path.join(output_dir, filename)
    lock_file = f"{filepath}.lock"

    try:
        # 注册锁文件
        _register_lock(lock_file)
        
        with FileLock(lock_file, timeout=10):
            if os.path.exists(filepath):
                # 在downloader中已经有了跳过逻辑的打印，这里设为silent时不打印
                # if not silent:
                #     safe_print(f"🔄 [yellow]跳过已下载章节: {chapter.title}[/yellow]")
                return "skipped"

            # 获取章节内容 (HTML)
            content_html = fetch_full_chapter_content(
                chapter_url=chapter.url,
                session=session,
                detector=detector,
                headers=headers
            )
            if not content_html:
                return None  # Fetching failed

            # 清洗内容并转换为最终格式
            cleaned_content = clean_content(content_html, detector, chapter.url)
            if not cleaned_content:
                if not silent:
                    safe_print(f"🧹 [yellow]章节内容清洗后为空: {chapter.title}[/yellow]")
                return None

            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {chapter.title}\n\n")
                f.write(cleaned_content)
            
            # 成功信息由downloader统一处理，这里不再打印
            # if not silent:
            #     safe_print(f"✅ [green]成功下载章节: {chapter.title}[/green]")
            
            return "success"

    except (IOError, OSError) as e:
        safe_print(f"❌ [red]文件写入错误 '{filename}': {e}[/red]")
        return None
    except Exception as e:
        safe_print(f"❌ [red]处理章节 '{chapter.title}' 时发生未知错误: {e}[/red]")
        return None
    finally:
        # 确保锁文件被注销和删除
        _unregister_lock(lock_file) 