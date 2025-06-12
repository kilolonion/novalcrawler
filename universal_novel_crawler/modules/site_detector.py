from typing import Optional, Dict
from urllib.parse import urlparse

from ..models import SiteConfig
from ..utils import safe_print

class SiteDetector:
    """网站检测和适配器"""
    
    def __init__(self):
        # 添加缓存机制
        self._detection_cache: Dict[str, Optional[SiteConfig]] = {}
        self._detection_logged: set = set()
        
        self.site_configs = {
            'localhost': SiteConfig(
                name='本地测试服务器',
                catalog_selectors=['.chapter-item a', '.chapter-list a', 'div.chapter-item a'],
                content_selectors=['.content', '#content', 'div.content'],
                title_selector='h1',
                next_page_patterns=[r'(\d+)_(\d+)\.html', r'(\d+)/(\d+)\.html'],
                page_info_pattern=r'\((\d+)/(\d+)\)',
                filters=['上一页', '下一页', '目录', '下一章', '上一章', '返回目录']
            ),
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
    
    def detect_site(self, url: str, silent: bool = False) -> Optional[SiteConfig]:
        """检测网站类型，支持缓存和静默模式"""
        domain = urlparse(url).netloc.lower()
        
        # 检查缓存
        if domain in self._detection_cache:
            return self._detection_cache[domain]
        
        # 进行检测
        config = None
        
        # 精确匹配
        for site_key, site_config in self.site_configs.items():
            if site_key in domain:
                config = site_config
                if not silent and domain not in self._detection_logged:
                    safe_print(f"🎯 检测到网站类型: {site_config.name}")
                    self._detection_logged.add(domain)
                break
        
        # 模糊匹配
        if not config and any(keyword in domain for keyword in ['biquge', 'bqg', '笔趣']):
            config = self.site_configs['biquge']
            if not silent and domain not in self._detection_logged:
                safe_print(f"🎯 检测到疑似笔趣阁类网站: {domain}")
                self._detection_logged.add(domain)
        
        # 未知网站使用通用配置
        if not config:
            config = self._create_generic_config()
            if not silent and domain not in self._detection_logged:
                safe_print(f"❓ 未知网站类型: {domain}，将使用通用解析")
                self._detection_logged.add(domain)
        
        # 缓存结果
        self._detection_cache[domain] = config
        return config
    
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