from typing import Optional
from urllib.parse import urlparse

from .models import SiteConfig
from .utils import safe_print

class SiteDetector:
    """网站检测和适配器"""
    
    def __init__(self):
        self.site_configs = {
            'huanqixiaoshuo.com': SiteConfig(
                name='幻象小说',
                catalog_selectors=['p a', 'div.list a', '.catalog a', 'td a'],
                content_selectors=['div:not([id]):not([class])', '.content', '#content'],
                title_selector='title',
                next_page_patterns=[r'(\d+)_(\d+)\.html', r'(\d+)/(\d+)\.html'],
                page_info_pattern=r'\((\d+)/(\d+)\)',
                filters=['上一页', '下一页', '目录', '下一章', '上一章', '本章尚未完结', '请点击下一页', '↓直达页面底部', '下页', '尾页']
            ),
            'biquge': SiteConfig(
                name='笔趣阁系列',
                catalog_selectors=['#list dd a', '.listmain dd a', 'div.list a'],
                content_selectors=['#content', '.content', '#booktext'],
                title_selector='h1',
                next_page_patterns=[r'(\d+)_(\d+)\.html', r'(\d+)/(\d+)\.html'],
                page_info_pattern=r'第(\d+)页.*?共(\d+)页',
                filters=['上一页', '下一页', '目录', '下一章', '上一章', 'chaptererror']
            ),
            'qidian.com': SiteConfig(
                name='起点中文网',
                catalog_selectors=['.volume-item .chapter-item a', '.catalog-content a'],
                content_selectors=['.read-content', '.content'],
                title_selector='.chapter-title',
                next_page_patterns=[],  # 通常不分页
                page_info_pattern=r'',
                filters=['上一页', '下一页', '目录', '书签']
            ),
            'piaotia.com': SiteConfig(
                name='飘天文学',
                catalog_selectors=['td.L a', 'a[href*="/html/"]'],
                content_selectors=['#content', '.content', 'div:has-text("　　")'],
                title_selector='h1',
                next_page_patterns=[r'(\d+)\.html'],
                page_info_pattern=r'第(\d+)页',
                filters=['上一页', '下一页', '目录', '下一章', '上一章', '返回书页']
            )
        }
    
    def detect_site(self, url: str) -> Optional[SiteConfig]:
        """检测网站类型"""
        domain = urlparse(url).netloc.lower()
        
        # 精确匹配
        for site_key, config in self.site_configs.items():
            if site_key in domain:
                safe_print(f"🎯 检测到网站类型: {config.name}")
                return config
        
        # 模糊匹配
        if any(keyword in domain for keyword in ['biquge', 'bqg', '笔趣']):
            safe_print(f"🎯 检测到疑似笔趣阁类网站: {domain}")
            return self.site_configs['biquge']
        
        safe_print(f"❓ 未知网站类型: {domain}，将使用通用解析")
        return self._create_generic_config()
    
    def _create_generic_config(self) -> SiteConfig:
        """创建通用配置"""
        return SiteConfig(
            name='通用网站',
            catalog_selectors=['a[href*=".html"]', 'a[href*="chapter"]', 'a[href*="/"]'],
            content_selectors=['div:not([id]):not([class])', '.content', '#content', 'div.text'],
            title_selector='title',
            next_page_patterns=[r'(\d+)_(\d+)\.html', r'(\d+)/(\d+)\.html', r'(\d+)-(\d+)\.html'],
            page_info_pattern=r'\((\d+)/(\d+)\)',
            filters=['上一页', '下一页', '目录', '下一章', '上一章', '返回', '首页', '书签']
        ) 