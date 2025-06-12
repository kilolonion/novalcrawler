"""
安全检查模块 - 检测和阻止访问敏感或被禁止的网站
Security Checker Module - Detect and block access to sensitive or prohibited websites
"""

import re
import tldextract
from typing import List, Set, Tuple, Optional
from urllib.parse import urlparse

from ..utils import safe_print


class SecurityChecker:
    """安全检查器 - 检测敏感网站和不当使用"""
    
    def __init__(self):
        # 敏感域名后缀黑名单
        self.SENSITIVE_DOMAINS = {
            # 政府机关
            '.gov.cn', '.gov', '.government.cn',
            # 军事机构
            '.mil.cn', '.mil', '.army.cn', '.navy.cn', '.airforce.cn',
            # 公安系统
            '.police.cn', '.gaj.', '.mps.gov.cn',
            # 司法系统
            '.court.gov.cn', '.procuratorate.gov.cn', '.justice.gov.cn',
            # 国家安全
            '.mss.gov.cn', '.state-security.cn',
            # 涉密机构
            '.classified.', '.secret.', '.confidential.',
        }
        
        # 敏感关键词
        self.SENSITIVE_KEYWORDS = {
            # 政府相关
            'government', '政府', '人民政府', '市政府', '省政府', '县政府',
            'gongan', '公安', 'police', '警察', '派出所', '治安',
            'court', '法院', '检察院', '司法',
            'military', '军事', '部队', '军区', '战区', '军委',
            # 金融机构
            'bank', '银行', 'securities', '证券', 'insurance', '保险',
            'finance', '金融', 'monetary', '货币', 'central-bank', '央行',
            # 医疗机构  
            'hospital', '医院', 'medical', '医疗', 'health', '卫生',
            'patient', '病人', '病历',
            # 教育机构
            'education', '教育', 'school', '学校', 'university', '大学',
            'student', '学生', '学籍',
            # 电信运营商
            'telecom', '电信', 'mobile', '移动', 'unicom', '联通',
            'communication', '通信',
        }
        
        # 特定敏感网站域名
        self.BLOCKED_DOMAINS = {
            # 政府网站示例
            'www.gov.cn', 'www.12306.cn', 'www.tax.gov.cn',
            # 金融网站示例  
            'www.pboc.gov.cn', 'www.csrc.gov.cn', 'www.cbirc.gov.cn',
            # 军事网站示例
            'www.mod.gov.cn', 'www.81.cn',
            # 其他敏感网站
            'www.miit.gov.cn', 'www.mps.gov.cn',
        }
        
        # 合法的小说网站白名单（允许访问的域名模式）
        self.NOVEL_SITE_PATTERNS = {
            r'.*xiaoshuo.*',  # 包含"小说"
            r'.*novel.*',     # 包含"novel"
            r'.*book.*',      # 包含"book"
            r'.*read.*',      # 包含"read" 
            r'.*story.*',     # 包含"story"
            r'.*fiction.*',   # 包含"fiction"
            r'.*literature.*', # 包含"literature"
            r'.*biquge.*',    # 笔趣阁系列
            r'.*qidian.*',    # 起点（已移除但保留检测）
            r'.*zongheng.*',  # 纵横
            r'.*17k.*',       # 17K
            r'.*jjwxc.*',     # 晋江
            r'localhost.*',   # 本地测试
            r'127\.0\.0\.1.*', # 本地IP
        }
    
    def is_sensitive_site(self, url: str) -> Tuple[bool, str]:
        """
        检查URL是否为敏感网站
        返回: (是否敏感, 原因说明)
        """
        if not url:
            return False, ""
            
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            full_url = url.lower()
            
            # 1. 检查域名后缀
            for sensitive_suffix in self.SENSITIVE_DOMAINS:
                if domain.endswith(sensitive_suffix):
                    return True, f"检测到敏感域名后缀: {sensitive_suffix}"
            
            # 2. 检查特定被禁域名
            if domain in self.BLOCKED_DOMAINS:
                return True, f"域名在黑名单中: {domain}"
            
            # 3. 检查敏感关键词
            for keyword in self.SENSITIVE_KEYWORDS:
                if keyword in domain or keyword in full_url:
                    return True, f"检测到敏感关键词: {keyword}"
            
            # 4. 使用tldextract进一步分析
            try:
                extracted = tldextract.extract(url)
                if extracted.suffix in ['.gov', '.mil', '.edu'] and extracted.domain not in ['github', 'gitlab']:
                    return True, f"检测到敏感顶级域名: .{extracted.suffix}"
            except:
                pass
                
            return False, ""
            
        except Exception as e:
            safe_print(f"⚠️ URL安全检查时出错: {e}")
            return False, ""
    
    def is_likely_novel_site(self, url: str) -> bool:
        """检查URL是否可能是小说网站"""
        if not url:
            return False
            
        domain = urlparse(url).netloc.lower()
        
        for pattern in self.NOVEL_SITE_PATTERNS:
            if re.match(pattern, domain):
                return True
                
        return False
    
    def check_url_safety(self, url: str) -> Tuple[bool, str]:
        """
        综合安全检查
        返回: (是否安全可访问, 提示信息)
        """
        if not url:
            return False, "URL为空"
        
        # 检查是否为敏感网站
        is_sensitive, reason = self.is_sensitive_site(url)
        if is_sensitive:
            return False, f"🚫 拒绝访问敏感网站: {reason}"
        
        # 检查是否为疑似小说网站
        if self.is_likely_novel_site(url):
            return True, "✅ 检测到疑似小说网站，允许访问"
        
        # 对于其他网站给出警告但允许访问
        return True, "⚠️ 未知网站类型，请确保仅用于合法的小说内容爬取"
    
    def validate_crawl_request(self, url: str, force_check: bool = True) -> bool:
        """
        验证爬取请求的合法性
        
        Args:
            url: 要爬取的URL
            force_check: 是否强制检查（默认True）
            
        Returns:
            bool: 是否允许爬取
        """
        if not force_check:
            return True
            
        is_safe, message = self.check_url_safety(url)
        
        if not is_safe:
            safe_print(f"❌ {message}")
            safe_print("📖 请使用本工具爬取合法的小说网站内容")
            safe_print("📋 详细规则请查看 DISCLAIMER.md 免责声明")
            return False
        else:
            if "疑似小说网站" not in message:
                safe_print(f"⚠️ {message}")
            return True
    
    def get_security_report(self, url: str) -> dict:
        """生成安全检查报告"""
        is_sensitive, sensitive_reason = self.is_sensitive_site(url)
        is_novel = self.is_likely_novel_site(url)
        is_safe, safety_message = self.check_url_safety(url)
        
        return {
            'url': url,
            'is_sensitive': is_sensitive,
            'sensitive_reason': sensitive_reason,
            'is_likely_novel_site': is_novel,
            'is_safe': is_safe,
            'safety_message': safety_message,
            'domain': urlparse(url).netloc,
        }


def get_security_checker() -> SecurityChecker:
    """获取安全检查器实例"""
    return SecurityChecker() 