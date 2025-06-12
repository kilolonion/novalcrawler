"""文件合并、标题规范化等相关逻辑"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, List, Optional

from ..utils import safe_print

__all__ = ['merge_chapters_to_txt']


def _extract_chapter_number(filename: str) -> int:
    """从文件名中提取章节号用于排序，番外和特殊章节保持原顺序"""
    # 处理标准格式：第xx章
    if re.search(r'第(\d+)章', filename):
        matches = re.findall(r'第(\d+)章', filename)
        if matches:
            return int(matches[0])
    
    # 处理数字格式：1、2、3. 等
    if re.search(r'^(\d+)[、．.]', filename):
        matches = re.findall(r'^(\d+)[、．.]', filename)
        if matches:
            return int(matches[0])
    
    # 处理纯数字章节名
    if re.match(r'^(\d+)', filename):
        matches = re.findall(r'^(\d+)', filename)
        if matches:
            return int(matches[0])
    
    # 番外和其他特殊章节使用非常大的数字保持在后面，但按文件名顺序
    if '番外' in filename:
        return 90000 + hash(filename) % 1000  # 使用hash确保稳定排序
    
    return 99999  # 其他无法解析的排在最后


def _normalize_title(raw_title: str) -> str:
    """标准化章节标题为『第xx章 章节名』格式，支持多种格式转换"""
    raw_title = raw_title.strip()
    
    # 标记番外章节，但不立即转换
    if '番外' in raw_title and not re.search(r'第[\d\u4e00-\u9fa5]+章', raw_title):
        return f"__EXTRA__{raw_title}"
    
    # 处理已经是标准格式的章节：第xx章
    m = re.match(r'(第[\u4e00-\u9fa5\d]+[章节卷])\s*[:：_-]*\s*(.*)', raw_title)
    if m:
        number_part = m.group(1)
        name_part = m.group(2).strip()
        return f"{number_part} {name_part}" if name_part else number_part
    
    # 处理数字格式：1、标题名 或 1. 标题名 或 1：标题名
    m = re.match(r'^(\d+)[、．.：:]\s*(.*)', raw_title)
    if m:
        chapter_num = m.group(1)
        title_part = m.group(2).strip()
        return f"__REFORMAT__{chapter_num}__{title_part}"
    
    # 处理纯数字标题：1 或 001
    m = re.match(r'^(\d+)$', raw_title)
    if m:
        chapter_num = m.group(1)
        return f"__REFORMAT__{chapter_num}__"
    
    # 处理中文数字：一、二、三
    chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    m = re.match(r'^([一二三四五六七八九十]+)[、．.：:]\s*(.*)', raw_title)
    if m:
        chinese_num = m.group(1)
        title_part = m.group(2).strip()
        if chinese_num in chinese_nums:
            chapter_num = str(chinese_nums[chinese_num])
            return f"__REFORMAT__{chapter_num}__{title_part}"
    
    # 其他无法识别的标题标记为需要重新编号
    return f"__UNKNOWN__{raw_title}"


def _clean_merge_content(content: str) -> str:
    """清理用于合并的单章内容，保留段落空行，规范标题格式，恢复正文缩进"""
    lines = content.split('\n')
    title = ""
    if lines and lines[0].startswith('# '):
        title = _normalize_title(lines[0][2:].strip())
        lines = lines[1:]

    output_lines = []
    if title:
        output_lines.append(title)
        output_lines.append("")

    previous_blank = False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if not previous_blank and output_lines:
                output_lines.append("")
                previous_blank = True
            continue
        previous_blank = False
        output_lines.append(f"    {line.strip()}")

    return '\n'.join(output_lines)


def merge_chapters_to_txt(
    output_dir: str,
    novel_title: Optional[str],
    sanitize_func: Callable[[str], str],
) -> bool:
    """将所有章节文件合并成一个txt文件"""
    chapters_dir = Path(output_dir)
    book_name = novel_title
    if not book_name:
        book_name = chapters_dir.name.replace('novels_', '')

    safe_novel_name = sanitize_func(book_name)
    output_file = chapters_dir.parent / f"{safe_novel_name}.txt"

    md_files = sorted(
        list(chapters_dir.glob("*.md")),
        key=lambda f: _extract_chapter_number(f.name)
    )

    if not md_files:
        safe_print(f"❌ 在 '{output_dir}' 中未找到章节文件。", style="bold red")
        return False

    safe_print(f"🔄 开始合并 {len(md_files)} 个章节到 '{output_file.name}'...")

    chapter_contents = []
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as infile:
                content = infile.read()
                chapter_contents.append(_clean_merge_content(content))
        except Exception as e:
            safe_print(f"⚠️ 读取文件 '{md_file.name}' 失败: {e}", style="yellow")
            chapter_contents.append("")

    # 分析所有章节，找出正常章节的最大编号
    max_normal_chapter = 0
    normal_contents = []
    special_contents = []  # 包括番外、重新格式化的、未知格式的章节
    
    for content in chapter_contents:
        lines = content.split('\n')
        if not lines or not lines[0].strip():
            normal_contents.append(content)
            continue
            
        title_line = lines[0]
        
        # 正常的第xx章格式
        if re.search(r'^第(\d+)章', title_line):
            match = re.search(r'^第(\d+)章', title_line)
            if match:
                chapter_num = int(match.group(1))
                max_normal_chapter = max(max_normal_chapter, chapter_num)
            normal_contents.append(content)
        else:
            # 特殊章节（番外、需要重新格式化的、未知格式的）
            special_contents.append(content)
    
    # 从最大正常章节号+1开始为特殊章节编号
    next_chapter_num = max_normal_chapter + 1
    processed_special_contents = []
    
    for content in special_contents:
        lines = content.split('\n')
        if not lines or not lines[0].strip():
            processed_special_contents.append(content)
            continue
            
        title_line = lines[0]
        
        # 处理番外章节
        if title_line.startswith('__EXTRA__'):
            extra_title = title_line[9:]  # 移除 __EXTRA__ 前缀
            new_title = f"第{next_chapter_num}章 {extra_title}"
            lines[0] = new_title
            next_chapter_num += 1
            processed_special_contents.append('\n'.join(lines))
            
        # 处理需要重新格式化的章节（1、标题 -> 第x章 标题）
        elif title_line.startswith('__REFORMAT__'):
            parts = title_line[12:].split('__')  # 移除 __REFORMAT__ 前缀并分割
            if len(parts) >= 2:
                original_num = parts[0]
                title_part = parts[1] if parts[1] else ""
                if title_part:
                    new_title = f"第{next_chapter_num}章 {title_part}"
                else:
                    new_title = f"第{next_chapter_num}章"
            else:
                new_title = f"第{next_chapter_num}章"
            lines[0] = new_title
            next_chapter_num += 1
            processed_special_contents.append('\n'.join(lines))
            
        # 处理未知格式章节
        elif title_line.startswith('__UNKNOWN__'):
            unknown_title = title_line[11:]  # 移除 __UNKNOWN__ 前缀
            new_title = f"第{next_chapter_num}章 {unknown_title}"
            lines[0] = new_title
            next_chapter_num += 1
            processed_special_contents.append('\n'.join(lines))
        else:
            # 直接添加其他章节
            processed_special_contents.append(content)
    
    # 合并正常章节和处理后的特殊章节
    processed_contents = normal_contents + processed_special_contents

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for content in processed_contents:
            if content.strip():
                outfile.write(content)
                outfile.write('\n\n')

    safe_print(f"✅ 合并完成！", style="bold green")
    return True 