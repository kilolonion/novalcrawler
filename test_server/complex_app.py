#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版本地测试服务器 - 包含复杂边缘情况测试
用于全面测试爬虫的鲁棒性和异常处理能力
"""

from flask import Flask, render_template_string, request, abort, redirect, url_for
import os
import time
import random
import json

app = Flask(__name__)

# 模拟小说数据
NOVEL_DATA = {
    'title': '测试小说：Python爬虫极限挑战',
    'author': '边缘测试专家',
    'intro': '这是一个专门用来测试爬虫极限情况的模拟小说网站。包含了各种复杂的网站结构、编码问题、错误情况和反爬虫场景。',
    'chapters': []
}

# 生成复杂测试章节
def generate_complex_chapters():
    chapters = []
    
    # 第一部分：普通章节（1-15章）
    for i in range(1, 16):
        chapters.append({
            'id': i,
            'title': f'第{i}章 基础测试章节{i}',
            'content': f'''
                <div class="content">
                    <h1>第{i}章 基础测试章节{i}</h1>
                    <p>这是第{i}章的基础内容。本章测试基本的HTML结构解析能力。</p>
                    <p>内容包含多个段落，用于验证段落提取和文本清理功能。</p>
                    <p>第{i}章的核心知识点包括：HTML解析、CSS选择器、异常处理等。</p>
                    <p>本章结束，准备进入下一章的学习。</p>
                </div>
            ''',
            'url': f'/chapter/{i}',
            'type': 'normal',
            'complexity': 'basic'
        })
    
    # 第二部分：边缘情况测试（16-35章）
    edge_cases = [
        # 空内容章节
        {
            'id': 16, 'title': '第16章 空内容边缘测试', 
            'content': '<div class="content"></div>', 
            'type': 'empty', 'complexity': 'edge'
        },
        
        # 超长标题章节
        {
            'id': 17, 
            'title': f'第17章 {"这是一个超级超级超级超级超级超级超级超级超级超级长的标题测试，用来验证爬虫对异常长标题的处理能力" * 3}',
            'content': '<div class="content"><p>测试超长标题的处理能力。</p></div>',
            'type': 'long_title', 'complexity': 'edge'
        },
        
        # 特殊Unicode字符章节
        {
            'id': 18, 
            'title': '第18章 特殊字符♠♣♥♦★☆▲●■◆◇▼▽△▴▾测试',
            'content': '''
                <div class="content">
                    <h1>Unicode字符测试</h1>
                    <p>各种特殊符号：♠♣♥♦★☆▲●■◆◇▼▽△▴▾</p>
                    <p>数学符号：∑∏∫∮∇∂∞±×÷√∝∈∉∪∩⊂⊃</p>
                    <p>箭头符号：←→↑↓↖↗↘↙⇐⇒⇑⇓</p>
                    <p>货币符号：$€£¥¢₹₽₿</p>
                    <p>表情符号：😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘</p>
                </div>
            ''',
            'type': 'unicode', 'complexity': 'edge'
        },
        
        # HTML实体和转义字符
        {
            'id': 19,
            'title': '第19章 HTML实体&lt;&gt;&amp;&quot;&#39;测试',
            'content': '''
                <div class="content">
                    <h1>HTML实体测试</h1>
                    <p>基本实体：&lt;p&gt;这是段落&lt;/p&gt;</p>
                    <p>引号测试：&quot;双引号&quot; &#39;单引号&#39;</p>
                    <p>空格实体：&nbsp;&nbsp;&nbsp;多个空格</p>
                    <p>特殊实体：&copy;&reg;&trade;&sect;&para;</p>
                    <p>数字实体：&#8364;(欧元) &#8482;(商标) &#169;(版权)</p>
                </div>
            ''',
            'type': 'html_entities', 'complexity': 'edge'
        },
        
        # 深度嵌套结构
        {
            'id': 20,
            'title': '第20章 深度嵌套结构挑战',
            'content': '''
                <div class="content">
                    <div><div><div><div><div>
                        <h1>深度嵌套测试</h1>
                        <p>这是深度嵌套的段落</p>
                    </div></div></div></div></div>
                    <table><tbody><tr><td><div><p>表格内嵌套的内容</p></div></td></tr></tbody></table>
                    <blockquote><div><cite><em><strong>多层嵌套的引用</strong></em></cite></div></blockquote>
                </div>
            ''',
            'type': 'nested', 'complexity': 'edge'
        },
        
        # 大量干扰内容
        {
            'id': 21,
            'title': '第21章 干扰内容过滤测试',
            'content': '''
                <div class="content">
                    <h1>干扰内容测试</h1>
                    <p>正文内容开始</p>
                    <div class="advertisement">🎯 热门推荐！点击领取1000元现金红包！</div>
                    <p>正文继续</p>
                    <div class="navigation">上一章 | 下一章 | 返回目录 | 加入书签</div>
                    <p>更多正文</p>
                    <script>console.log("广告脚本");</script>
                    <p>正文结束</p>
                    <div class="footer">本站提供最新章节阅读</div>
                </div>
            ''',
            'type': 'interference', 'complexity': 'edge'
        },
        
        # JavaScript和样式干扰
        {
            'id': 22,
            'title': '第22章 脚本样式干扰测试',
            'content': '''
                <div class="content">
                    <style>.hidden{display:none;}</style>
                    <h1>脚本干扰测试</h1>
                    <p>正文内容</p>
                    <script>
                        document.write("动态生成的干扰内容");
                        alert("弹窗干扰");
                    </script>
                    <p class="hidden">隐藏的内容</p>
                    <p>更多正文</p>
                    <noscript>JavaScript禁用时显示的内容</noscript>
                </div>
            ''',
            'type': 'javascript', 'complexity': 'edge'
        },
        
        # 混合编码测试
        {
            'id': 23,
            'title': '第23章 多语言混合编码测试',
            'content': '''
                <div class="content">
                    <h1>多语言编码测试</h1>
                    <p>中文：你好世界！繁體中文測試。古文：子曰學而時習之不亦說乎</p>
                    <p>日语：こんにちは世界！ひらがなカタカナ漢字テスト</p>
                    <p>韩语：안녕하세요 세계! 한글 테스트입니다.</p>
                    <p>俄语：Привет мир! Русский текст тест.</p>
                    <p>阿拉伯语：مرحبا بالعالم! اختبار النص العربي.</p>
                    <p>泰语：สวัสดีชาวโลก! การทดสอบข้อความไทย</p>
                    <p>印地语：नमस्ते दुनिया! हिंदी पाठ परीक्षण।</p>
                </div>
            ''',
            'type': 'multilang', 'complexity': 'edge'
        },
    ]
    
    chapters.extend(edge_cases)
    
    # 第三部分：分页章节测试（24-30章）
    for base_chapter in range(24, 31):
        for page_num in range(1, 5):  # 每章4页
            chapter_id = f"{base_chapter}_{page_num}"
            if page_num == 1:
                title = f'第{base_chapter}章 分页测试章节{base_chapter}'
            else:
                title = f'第{base_chapter}章 分页测试章节{base_chapter} (第{page_num}页)'
            
            next_page_link = ""
            if page_num < 4:
                next_page_link = f'<a href="/chapter/{base_chapter}_{page_num + 1}">下一页</a>'
            
            chapters.append({
                'id': chapter_id,
                'title': title,
                'content': f'''
                    <div class="content">
                        <h1>{title}</h1>
                        <p>这是第{base_chapter}章第{page_num}页的内容。</p>
                        <p>分页测试：当前页{page_num}/4</p>
                        <p>章节内容继续...</p>
                        <p>更多段落内容用于测试分页解析。</p>
                        {"<p>本页结束，请点击下一页继续阅读。</p>" if page_num < 4 else "<p>本章结束。</p>"}
                        <div class="page-nav">{next_page_link}</div>
                    </div>
                ''',
                'url': f'/chapter/{chapter_id}',
                'type': 'paginated',
                'complexity': 'pagination',
                'page': page_num,
                'total_pages': 4
            })
    
    # 第四部分：错误和反爬虫测试（31-40章）
    error_chapters = [
        {'id': 31, 'title': '第31章 404错误测试', 'type': 'error_404', 'complexity': 'error'},
        {'id': 32, 'title': '第32章 500服务器错误测试', 'type': 'error_500', 'complexity': 'error'},
        {'id': 33, 'title': '第33章 超时测试', 'type': 'timeout', 'complexity': 'error'},
        {'id': 34, 'title': '第34章 重定向测试', 'type': 'redirect', 'complexity': 'error'},
        {'id': 35, 'title': '第35章 反爬虫检测测试', 'type': 'anti_crawler', 'complexity': 'error'},
        {'id': 36, 'title': '第36章 验证码挑战', 'type': 'captcha', 'complexity': 'error'},
        {'id': 37, 'title': '第37章 频率限制测试', 'type': 'rate_limit', 'complexity': 'error'},
        {'id': 38, 'title': '第38章 IP封禁模拟', 'type': 'ip_ban', 'complexity': 'error'},
        {'id': 39, 'title': '第39章 User-Agent检测', 'type': 'user_agent', 'complexity': 'error'},
        {'id': 40, 'title': '第40章 Cookie验证测试', 'type': 'cookie_check', 'complexity': 'error'},
    ]
    
    for error_chapter in error_chapters:
        error_chapter['url'] = f'/chapter/{error_chapter["id"]}'
        error_chapter['content'] = f'''
            <div class="content">
                <h1>{error_chapter["title"]}</h1>
                <p>这是{error_chapter["type"]}测试章节。</p>
                <p>用于测试爬虫对各种错误情况的处理能力。</p>
            </div>
        '''
        chapters.append(error_chapter)
    
    # 第五部分：格式挑战测试（41-50章）
    format_chapters = [
        {
            'id': 41, 'title': '第41章 纯文本格式测试',
            'content': '这是纯文本内容，没有HTML标签。\n\n这是第二段。\n\n包含换行和分段测试。',
            'type': 'plain_text', 'complexity': 'format'
        },
        {
            'id': 42, 'title': '第42章 复杂表格测试',
            'content': '''
                <div class="content">
                    <h1>复杂表格测试</h1>
                    <table border="1" cellpadding="5" cellspacing="0">
                        <thead>
                            <tr><th>姓名</th><th>年龄</th><th>职业</th><th>技能</th></tr>
                        </thead>
                        <tbody>
                            <tr><td>张三</td><td>25</td><td>程序员</td><td>Python, Java</td></tr>
                            <tr><td>李四</td><td>30</td><td>设计师</td><td>PS, AI</td></tr>
                            <tr><td colspan="2">合计</td><td colspan="2">2人</td></tr>
                        </tbody>
                    </table>
                </div>
            ''',
            'type': 'complex_table', 'complexity': 'format'
        },
        {
            'id': 43, 'title': '第43章 嵌套列表测试',
            'content': '''
                <div class="content">
                    <h1>嵌套列表测试</h1>
                    <ol>
                        <li>第一级列表
                            <ul>
                                <li>第二级列表项1</li>
                                <li>第二级列表项2
                                    <ol>
                                        <li>第三级列表项A</li>
                                        <li>第三级列表项B</li>
                                    </ol>
                                </li>
                            </ul>
                        </li>
                        <li>第一级列表项2</li>
                    </ol>
                </div>
            ''',
            'type': 'nested_list', 'complexity': 'format'
        },
        {
            'id': 44, 'title': '第44章 媒体内容测试',
            'content': '''
                <div class="content">
                    <h1>媒体内容测试</h1>
                    <p>文字内容开始</p>
                    <img src="/static/test-image.jpg" alt="测试图片" width="300">
                    <p>图片后的文字</p>
                    <video controls>
                        <source src="/static/test-video.mp4" type="video/mp4">
                        您的浏览器不支持视频播放。
                    </video>
                    <p>视频后的文字</p>
                    <audio controls>
                        <source src="/static/test-audio.mp3" type="audio/mp3">
                        您的浏览器不支持音频播放。
                    </audio>
                    <p>音频后的文字</p>
                </div>
            ''',
            'type': 'media_content', 'complexity': 'format'
        },
        {
            'id': 45, 'title': '第45章 代码和预格式化测试',
            'content': '''
                <div class="content">
                    <h1>代码和预格式化测试</h1>
                    <p>行内代码：<code>print("Hello World")</code></p>
                    <pre><code>
def hello_world():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
                    </code></pre>
                    <p>预格式化文本：</p>
                    <pre>
这是预格式化文本
    保持空格和换行
        缩进也会保持
    </pre>
                </div>
            ''',
            'type': 'code_format', 'complexity': 'format'
        },
    ]
    
    chapters.extend(format_chapters)
    
    # 剩余章节（46-80章）- 随机生成各种复杂情况
    for i in range(46, 81):
        complexity_types = ['mixed', 'random_structure', 'encoding_test', 'performance_test']
        selected_type = random.choice(complexity_types)
        
        chapters.append({
            'id': i,
            'title': f'第{i}章 随机复杂测试{i}',
            'content': generate_random_complex_content(i, selected_type),
            'url': f'/chapter/{i}',
            'type': selected_type,
            'complexity': 'random'
        })
    
    return chapters

def generate_random_complex_content(chapter_id, content_type):
    """生成随机复杂内容"""
    base_content = f'''
        <div class="content">
            <h1>第{chapter_id}章 随机复杂测试{chapter_id}</h1>
            <p>这是第{chapter_id}章的随机生成内容，类型：{content_type}</p>
    '''
    
    if content_type == 'mixed':
        base_content += '''
            <div><span><em>混合标签嵌套测试</em></span></div>
            <blockquote>引用内容<cite>引用来源</cite></blockquote>
            <details><summary>折叠内容</summary><p>隐藏的详细信息</p></details>
        '''
    elif content_type == 'random_structure':
        base_content += '''
            <aside>侧边栏内容</aside>
            <section><article><header>文章头部</header><main>主要内容</main><footer>文章尾部</footer></article></section>
            <nav><a href="#">导航链接1</a><a href="#">导航链接2</a></nav>
        '''
    elif content_type == 'encoding_test':
        base_content += '''
            <p>编码测试：中文 English 日本語 한국어 Русский العربية</p>
            <p>数字测试：①②③④⑤⑥⑦⑧⑨⑩</p>
            <p>符号测试：♠♣♥♦★☆▲●■◆</p>
        '''
    elif content_type == 'performance_test':
        # 生成大量重复内容测试性能
        for i in range(50):
            base_content += f'<p>性能测试段落{i+1}：这是用于测试爬虫性能的重复内容。' * 5 + '</p>'
    
    base_content += '</div>'
    return base_content

# 生成所有章节
NOVEL_DATA['chapters'] = generate_complex_chapters()

# 模板定义
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ novel.title }} - 极限测试版</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }
        .chapter-list { background: white; border: 1px solid #ddd; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .chapter-item { margin: 8px 0; padding: 5px; border-radius: 5px; }
        .chapter-item:hover { background: #f8f9fa; }
        .chapter-item a { text-decoration: none; color: #333; display: block; padding: 10px; }
        .chapter-item.normal { border-left: 4px solid #28a745; }
        .chapter-item.edge { border-left: 4px solid #ffc107; }
        .chapter-item.error { border-left: 4px solid #dc3545; }
        .chapter-item.pagination { border-left: 4px solid #17a2b8; }
        .chapter-item.format { border-left: 4px solid #6f42c1; }
        .chapter-item.random { border-left: 4px solid #fd7e14; }
        .pagination { margin: 30px 0; text-align: center; }
        .pagination a { margin: 0 8px; padding: 8px 15px; text-decoration: none; border: 1px solid #ddd; border-radius: 5px; background: white; }
        .stats { background: #fff3cd; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .complexity-legend { display: flex; flex-wrap: wrap; gap: 15px; margin: 20px 0; }
        .complexity-item { display: flex; align-items: center; }
        .complexity-color { width: 20px; height: 20px; margin-right: 8px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 {{ novel.title }}</h1>
        <p><strong>作者：</strong>{{ novel.author }}</p>
        <p><strong>简介：</strong>{{ novel.intro }}</p>
        <p><strong>总章节：</strong>{{ novel.chapters|length }}章 | <strong>复杂度：</strong>极限挑战级</p>
    </div>
    
    <div class="stats">
        <h3>📊 测试统计</h3>
        <div class="complexity-legend">
            <div class="complexity-item">
                <div class="complexity-color" style="background: #28a745;"></div>
                <span>基础测试 (1-15章)</span>
            </div>
            <div class="complexity-item">
                <div class="complexity-color" style="background: #ffc107;"></div>
                <span>边缘情况 (16-23章)</span>
            </div>
            <div class="complexity-item">
                <div class="complexity-color" style="background: #17a2b8;"></div>
                <span>分页测试 (24-30章)</span>
            </div>
            <div class="complexity-item">
                <div class="complexity-color" style="background: #dc3545;"></div>
                <span>错误测试 (31-40章)</span>
            </div>
            <div class="complexity-item">
                <div class="complexity-color" style="background: #6f42c1;"></div>
                <span>格式测试 (41-45章)</span>
            </div>
            <div class="complexity-item">
                <div class="complexity-color" style="background: #fd7e14;"></div>
                <span>随机复杂 (46-80章)</span>
            </div>
        </div>
    </div>
    
    <div class="chapter-list">
        <h2>📚 极限挑战章节目录</h2>
        {% for chapter in chapters %}
        <div class="chapter-item {{ chapter.complexity }}">
            <a href="{{ chapter.url }}">
                {{ chapter.title }}
                <small style="color: #666; float: right;">{{ chapter.type }}</small>
            </a>
        </div>
        {% endfor %}
        
        {% if has_pagination %}
        <div class="pagination">
            {% if page > 1 %}
            <a href="/?page={{ page - 1 }}">⬅️ 上一页</a>
            {% endif %}
            
            <span style="margin: 0 20px;">第 {{ page }} 页 / 共 {{ total_pages }} 页</span>
            
            {% if page < total_pages %}
            <a href="/?page={{ page + 1 }}">下一页 ➡️</a>
            {% endif %}
        </div>
        {% endif %}
    </div>
    
    <div style="margin-top: 30px; padding: 25px; background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 8px;">
        <h3>🧪 极限测试说明</h3>
        <p><strong>这是爬虫极限挑战版测试服务器，包含以下高难度测试场景：</strong></p>
        <ul>
            <li>🎯 <strong>边缘情况：</strong>空内容、超长标题、特殊字符、HTML实体</li>
            <li>🏗️ <strong>复杂结构：</strong>深度嵌套、混合格式、动态内容</li>
            <li>🔄 <strong>分页处理：</strong>章节内分页、复杂导航</li>
            <li>❌ <strong>错误模拟：</strong>404、500、超时、反爬虫</li>
            <li>🎨 <strong>格式挑战：</strong>表格、列表、媒体、代码</li>
            <li>🌍 <strong>编码测试：</strong>多语言、特殊符号、emoji</li>
            <li>⚡ <strong>性能测试：</strong>大量内容、随机结构</li>
        </ul>
        <p><strong>🎯 测试URL：</strong> <code>http://localhost:8080</code></p>
        <p><strong>💡 建议：</strong>使用不同的章节范围来测试特定功能</p>
    </div>
</body>
</html>
'''

CHAPTER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ chapter.title }} - {{ novel.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.8; background: #f8f9fa; }
        .navigation { margin: 25px 0; text-align: center; }
        .navigation a { margin: 0 12px; padding: 10px 20px; text-decoration: none; background: #007cba; color: white; border-radius: 6px; display: inline-block; }
        .navigation a:hover { background: #005a87; transform: translateY(-1px); }
        .content { border: 1px solid #dee2e6; padding: 40px; border-radius: 12px; background: white; box-shadow: 0 2px 15px rgba(0,0,0,0.1); }
        .content h1 { color: #343a40; border-bottom: 3px solid #007cba; padding-bottom: 15px; margin-bottom: 25px; }
        .content p { margin: 20px 0; text-indent: 2em; }
        .content ul, .content ol { margin: 20px 0; padding-left: 35px; }
        .content table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .content table th, .content table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .content table th { background: #f8f9fa; }
        .content pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .content code { background: #f8f9fa; padding: 2px 4px; border-radius: 3px; }
        .chapter-info { background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 14px; }
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
        <a href="{{ next_chapter.url }}">下一章 ➡️</a>
        {% endif %}
    </div>
    
    <div class="chapter-info">
        <strong>章节信息：</strong>
        ID: {{ chapter.id }} | 
        类型: {{ chapter.type }} | 
        复杂度: {{ chapter.complexity }} |
        当前进度: {{ chapter.id }} / {{ total_chapters }}
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
        <a href="{{ next_chapter.url }}">下一章 ➡️</a>
        {% endif %}
    </div>
    
    <div class="footer">
        <p>🧪 这是爬虫极限挑战测试章节</p>
        <p>测试重点：{{ chapter.type }} | 复杂度：{{ chapter.complexity }}</p>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    """首页 - 章节目录"""
    page = int(request.args.get('page', 1))
    per_page = 25  # 每页显示25章
    
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

@app.route('/chapter/<path:chapter_id>')
def chapter(chapter_id):
    """章节页面 - 支持复杂ID格式"""
    # 查找章节
    chapter_data = None
    chapter_index = -1
    
    for i, ch in enumerate(NOVEL_DATA['chapters']):
        if str(ch['id']) == str(chapter_id):
            chapter_data = ch
            chapter_index = i
            break
    
    if not chapter_data:
        abort(404)
    
    # 处理特殊错误类型
    if chapter_data.get('type') == 'error_404':
        abort(404)
    elif chapter_data.get('type') == 'error_500':
        abort(500)
    elif chapter_data.get('type') == 'timeout':
        time.sleep(30)  # 模拟超时
    elif chapter_data.get('type') == 'redirect':
        return redirect(url_for('chapter', chapter_id=1))
    elif chapter_data.get('type') == 'anti_crawler':
        user_agent = request.headers.get('User-Agent', '')
        if 'python' in user_agent.lower() or 'requests' in user_agent.lower():
            abort(403)
    elif chapter_data.get('type') == 'rate_limit':
        # 简单的频率限制模拟
        time.sleep(2)
    elif chapter_data.get('type') == 'user_agent':
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent or len(user_agent) < 10:
            return "请使用有效的浏览器访问", 403
    
    # 获取上一章和下一章
    prev_chapter = None
    next_chapter = None
    
    if chapter_index > 0:
        prev_chapter = NOVEL_DATA['chapters'][chapter_index - 1]
    
    if chapter_index < len(NOVEL_DATA['chapters']) - 1:
        next_chapter = NOVEL_DATA['chapters'][chapter_index + 1]
    
    return render_template_string(CHAPTER_TEMPLATE,
                                novel=NOVEL_DATA,
                                chapter=chapter_data,
                                prev_chapter=prev_chapter,
                                next_chapter=next_chapter,
                                total_chapters=len(NOVEL_DATA['chapters']))

@app.route('/robots.txt')
def robots():
    """robots.txt - 允许所有爬虫但有限制"""
    return '''User-agent: *
Allow: /
Disallow: /admin/
Disallow: /error/
Crawl-delay: 1

# 极限测试服务器 - 欢迎挑战！''', 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    """网站地图"""
    urls = ['http://localhost:8080/']
    for chapter in NOVEL_DATA['chapters']:
        urls.append(f'http://localhost:8080{chapter["url"]}')
    
    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'''
    
    for url in urls:
        sitemap_xml += f'''
    <url>
        <loc>{url}</loc>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>'''
    
    sitemap_xml += '\n</urlset>'
    return sitemap_xml, 200, {'Content-Type': 'application/xml'}

@app.route('/api/stats')
def stats():
    """API接口 - 获取测试统计"""
    complexity_stats = {}
    type_stats = {}
    
    for chapter in NOVEL_DATA['chapters']:
        complexity = chapter.get('complexity', 'unknown')
        chapter_type = chapter.get('type', 'unknown')
        
        complexity_stats[complexity] = complexity_stats.get(complexity, 0) + 1
        type_stats[chapter_type] = type_stats.get(chapter_type, 0) + 1
    
    return json.dumps({
        'total_chapters': len(NOVEL_DATA['chapters']),
        'complexity_distribution': complexity_stats,
        'type_distribution': type_stats,
        'server_info': 'Extreme Testing Server v2.0'
    }, ensure_ascii=False, indent=2), 200, {'Content-Type': 'application/json; charset=utf-8'}

if __name__ == '__main__':
    print("🚀 启动极限挑战测试服务器...")
    print("📍 访问地址：http://localhost:8080")
    print(f"📚 总章节数： {len(NOVEL_DATA['chapters'])}")
    print("🎯 极限测试模式：包含80个复杂测试场景")
    print("💪 挑战等级：困难++")
    print("-" * 60)
    app.run(debug=True, host='0.0.0.0', port=8080) 