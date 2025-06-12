"""并发下载、进度显示等相关逻辑"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List

from ..models import ChapterInfo
from ..utils import RICH_AVAILABLE, console, safe_print

if RICH_AVAILABLE:
    from rich.progress import (BarColumn, Progress, TextColumn,
                               TimeElapsedColumn, TimeRemainingColumn)
    from rich.panel import Panel
    from rich.table import Table

__all__ = [
    'download_chapters_with_progress',
    'download_chapters_simple',
    'show_completion_stats',
]


def download_chapters_with_progress(
    chapters: List[ChapterInfo],
    output_dir: str,
    max_workers: int,
    total_chapters: int,
    initial_advance: int,
    crawl_func: Callable,
) -> int:
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
        transient=False,
        console=console
    )

    success_count = 0
    error_messages: List[str] = []

    with progress:
        task = progress.add_task("下载中...", total=total_chapters)
        progress.advance(task, advance=initial_advance)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chapter = {
                executor.submit(crawl_func, chapter, output_dir, silent=True): chapter
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

    if error_messages:
        safe_print("\n" + "\n".join(error_messages[:5]))
        if len(error_messages) > 5:
            safe_print(f"... 还有 {len(error_messages) - 5} 个错误未显示")

    return success_count


def download_chapters_simple(
    chapters: List[ChapterInfo],
    output_dir: str,
    max_workers: int,
    crawl_func: Callable,
) -> int:
    """不使用rich进度条的简单下载模式"""
    success_count = 0
    total_count = len(chapters)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chapter = {
            executor.submit(crawl_func, chapter, output_dir): chapter
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


def show_completion_stats(
    success_count: int,
    total_count: int,
    skipped_count: int,
    output_dir: str,
    get_downloaded_chapters_func: Callable,
):
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

    stats_table = Table(title="📊 下载统计", show_header=False, box=None)
    stats_table.add_column(style="green")
    stats_table.add_column(style="bold magenta")

    stats_table.add_row("✅ 成功下载:", f"{success_count} 章")
    if failure_count > 0:
        stats_table.add_row("❌ 下载失败:", f"[red]{failure_count} 章[/red]")
    if skipped_count > 0:
        stats_table.add_row("🔄 已跳过:", f"{skipped_count} 章")

    stats_table.add_row("💾 保存位置:", f"[cyan]{output_dir}[/cyan]")

    total_chapters_in_dir = len(get_downloaded_chapters_func(output_dir))
    stats_table.add_row("📁 目录总数:", f"{total_chapters_in_dir} 章")

    panel = Panel(
        stats_table,
        title="🎉 [bold green]下载完成[/bold green] 🎉",
        expand=False,
        border_style="green"
    )
    console.print(panel) 