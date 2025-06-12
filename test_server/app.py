#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地测试服务器 - 模拟小说网站
用于测试爬虫功能，避免对真实网站造成负担
"""

from flask import Flask, render_template_string, request
import os

app = Flask(__name__)

# 模拟小说数据
NOVEL_DATA = {
    'title': '测试小说：Python爬虫历险记',
    'author': '测试作者',
    'intro': '这是一个专门用来测试爬虫功能的模拟小说网站。包含了各种常见的网站结构和内容格式。',
    'chapters': []
}

# 生成测试章节
for i in range(1, 51):  # 50章
    NOVEL_DATA['chapters'].append({
        'id': i,
        'title': f'第{i}章 爬虫测试章节{i}',
        'content': f'''
            <h1>第{i}章 爬虫测试章节{i}</h1>
            <p>这是第{i}章的内容。本章主要讲述了爬虫程序如何智能地解析网页内容。</p>
            <p>在这一章中，我们的主角学习了如何使用BeautifulSoup来解析HTML文档，如何处理各种复杂的网页结构。</p>
            <p>章节内容包含了多个段落，用来测试内容提取和清理功能。这里还有一些特殊字符：《》""''—…</p>
            <p>第{i}章的核心知识点：</p>
            <ul>
                <li>HTML解析技巧</li>
                <li>CSS选择器的使用</li>
                <li>异常处理机制</li>
                <li>反爬虫应对策略</li>
            </ul>
            <p>最后，第{i}章总结了本章的学习内容，为下一章做好准备。</p>
            <hr>
            <p><em>提示：这是测试章节{i}，用于验证爬虫的内容提取能力。</em></p>
        ''',
        'url': f'/chapter/{i}'
    })

# 首页模板
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ novel.title }} - 测试小说网站</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .chapter-list { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .chapter-item { margin: 5px 0; }
        .chapter-item a { text-decoration: none; color: #333; display: block; padding: 8px; }
        .chapter-item a:hover { background: #f5f5f5; }
        .pagination { margin: 20px 0; text-align: center; }
        .pagination a { margin: 0 5px; padding: 5px 10px; text-decoration: none; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ novel.title }}</h1>
        <p><strong>作者：</strong>{{ novel.author }}</p>
        <p><strong>简介：</strong>{{ novel.intro }}</p>
        <p><strong>总章节：</strong>{{ novel.chapters|length }}章</p>
    </div>
    
    <div class="chapter-list">
        <h2>📚 章节目录</h2>
        {% for chapter in chapters %}
        <div class="chapter-item">
            <a href="{{ chapter.url }}">{{ chapter.title }}</a>
        </div>
        {% endfor %}
        
        {% if has_pagination %}
        <div class="pagination">
            {% if page > 1 %}
            <a href="/?page={{ page - 1 }}">上一页</a>
            {% endif %}
            
            <span>第 {{ page }} 页 / 共 {{ total_pages }} 页</span>
            
            {% if page < total_pages %}
            <a href="/?page={{ page + 1 }}">下一页</a>
            {% endif %}
        </div>
        {% endif %}
    </div>
    
    <div style="margin-top: 30px; padding: 20px; background: #fff3cd; border-radius: 8px;">
        <h3>🧪 测试说明</h3>
        <p>这是一个专门用于测试爬虫的本地服务器，包含以下特性：</p>
        <ul>
            <li>✅ 完整的章节目录结构</li>
            <li>✅ 支持分页显示</li>
            <li>✅ 规范的HTML结构</li>
            <li>✅ 多种内容格式</li>
            <li>✅ 无反爬虫限制</li>
        </ul>
        <p><strong>爬虫测试URL：</strong> <code>http://localhost:8080</code></p>
    </div>
</body>
</html>
'''

# 章节页面模板
CHAPTER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ chapter.title }} - {{ novel.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
        .navigation { margin: 20px 0; text-align: center; }
        .navigation a { margin: 0 10px; padding: 8px 16px; text-decoration: none; background: #007cba; color: white; border-radius: 4px; }
        .navigation a:hover { background: #005a87; }
        .content { border: 1px solid #ddd; padding: 30px; border-radius: 8px; background: #fefefe; }
        .content h1 { color: #333; border-bottom: 2px solid #007cba; padding-bottom: 10px; }
        .content p { margin: 16px 0; text-indent: 2em; }
        .content ul { margin: 16px 0; padding-left: 30px; }
        .footer { margin-top: 30px; text-align: center; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="navigation">
        <a href="/">📚 返回目录</a>
        {% if prev_chapter %}
        <a href="{{ prev_chapter.url }}">⬅️ 上一章</a>
        {% endif %}
        {% if next_chapter %}
        <a href="{{ next_chapter.url }}">➡️ 下一章</a>
        {% endif %}
    </div>
    
    <div class="content">
        {{ chapter.content | safe }}
    </div>
    
    <div class="navigation">
        <a href="/">📚 返回目录</a>
        {% if prev_chapter %}
        <a href="{{ prev_chapter.url }}">⬅️ 上一章</a>
        {% endif %}
        {% if next_chapter %}
        <a href="{{ next_chapter.url }}">➡️ 下一章</a>
        {% endif %}
    </div>
    
    <div class="footer">
        <p>🧪 这是测试章节，用于验证爬虫功能</p>
        <p>当前章节：{{ chapter.id }} / {{ total_chapters }}</p>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    """首页 - 章节目录"""
    page = int(request.args.get('page', 1))
    per_page = 20  # 每页显示20章
    
    total_chapters = len(NOVEL_DATA['chapters'])
    total_pages = (total_chapters + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    chapters = NOVEL_DATA['chapters'][start_idx:end_idx]
    
    return render_template_string(INDEX_TEMPLATE, 
                                novel=NOVEL_DATA,
                                chapters=chapters,
                                page=page,
                                total_pages=total_pages,
                                has_pagination=total_pages > 1)

@app.route('/chapter/<int:chapter_id>')
def chapter(chapter_id):
    """章节页面"""
    if chapter_id < 1 or chapter_id > len(NOVEL_DATA['chapters']):
        return "章节不存在", 404
    
    chapter = NOVEL_DATA['chapters'][chapter_id - 1]
    
    # 获取上一章和下一章
    prev_chapter = None
    next_chapter = None
    
    if chapter_id > 1:
        prev_chapter = NOVEL_DATA['chapters'][chapter_id - 2]
    
    if chapter_id < len(NOVEL_DATA['chapters']):
        next_chapter = NOVEL_DATA['chapters'][chapter_id]
    
    return render_template_string(CHAPTER_TEMPLATE,
                                novel=NOVEL_DATA,
                                chapter=chapter,
                                prev_chapter=prev_chapter,
                                next_chapter=next_chapter,
                                total_chapters=len(NOVEL_DATA['chapters']))

@app.route('/robots.txt')
def robots():
    """robots.txt - 允许所有爬虫"""
    return '''User-agent: *
Allow: /

# 这是测试服务器，欢迎所有爬虫访问
Crawl-delay: 0'''

@app.route('/sitemap.xml')
def sitemap():
    """网站地图"""
    urls = ['http://localhost:8080/']
    for chapter in NOVEL_DATA['chapters']:
        urls.append(f'http://localhost:8080{chapter["url"]}')
    
    sitemap_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'''
    
    for url in urls:
        sitemap_content += f'''
    <url>
        <loc>{url}</loc>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>'''
    
    sitemap_content += '''
</urlset>'''
    
    return sitemap_content, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    print("🚀 启动测试服务器...")
    print("📍 访问地址：http://localhost:8080")
    print("📚 总章节数：", len(NOVEL_DATA['chapters']))
    print("🧪 这是专门用于测试爬虫的本地服务器")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=8080) 