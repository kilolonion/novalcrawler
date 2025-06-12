import getpass
import json
import os
import platform
import shutil
import sqlite3
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import LoginConfig
from .utils import console, safe_print

class LoginManager:
    """处理所有登录相关逻辑"""

    def __init__(self, login_config: LoginConfig):
        self.login_config = login_config
        self.session = requests.Session()
        
        # 改进的反反爬虫头部设置
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })

    def get_login_config(self, site_url: str) -> None:
        """获取登录配置"""
        # 先询问是否需要登录
        need_login = input("\n🔐 是否需要登录？ (y/n, 默认n): ").strip().lower()
        
        if need_login not in ['y', 'yes', '是', '需要']:
            self.login_config.mode = 'none'
            safe_print("✅ 选择无需登录模式")
            return
        
        # 需要登录时显示登录方式选择
        safe_print("\n🔐 请选择登录方式:")
        print("1. 无需登录")
        print("2. 用户名密码登录") 
        print("3. 手动输入Cookie")
        print("4. 从浏览器自动获取Cookie")
        print("5. 启动浏览器登录 (默认)")
        
        choice = input("请选择 (1-5, 默认5): ").strip() or "5"
        
        if choice == "1":
            self.login_config.mode = 'none'
            safe_print("✅ 选择无需登录模式")
            
        elif choice == "2":
            self.login_config.mode = 'credentials'
            self.login_config.username = input("请输入用户名: ").strip()
            self.login_config.password = getpass.getpass("请输入密码: ")
            
            # 推断登录URL
            parsed = urlparse(site_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            common_login_paths = ['/login', '/user/login', '/member/login', '/signin', '/user.html', '/login.html']
            
            print("\n🔗 请选择登录页面:")
            for i, path in enumerate(common_login_paths, 1):
                print(f"  {i}. {base_url}{path}")
            print(f"  {len(common_login_paths) + 1}. 手动输入完整URL")
            
            login_choice = input(f"请选择 (1-{len(common_login_paths) + 1}): ").strip()
            
            if login_choice.isdigit():
                choice_num = int(login_choice)
                if 1 <= choice_num <= len(common_login_paths):
                    self.login_config.login_url = base_url + common_login_paths[choice_num - 1]
                elif choice_num == len(common_login_paths) + 1:
                    self.login_config.login_url = input("请输入完整登录URL: ").strip()
                else:
                    self.login_config.login_url = base_url + "/login"  # 默认
            else:
                self.login_config.login_url = base_url + "/login"  # 默认
                
            safe_print(f"🔗 登录URL: {self.login_config.login_url}")
            safe_print("✅ 已设置用户名密码登录")
            
        elif choice == "3":
            self.login_config.mode = 'cookies'
            print("🍪 Cookie登录模式")
            print("请输入Cookie字符串（从浏览器开发者工具复制）:")
            cookie_str = input().strip()
            
            if cookie_str:
                try:
                    self.login_config.cookies = self.parse_cookie_string(cookie_str)
                    safe_print(f"✅ 已解析 {len(self.login_config.cookies)} 个Cookie")
                except Exception as e:
                    safe_print(f"❌ Cookie解析失败: {e}")
                    self.login_config.mode = 'none'
            else:
                safe_print("❌ 未提供Cookie，使用无登录模式")
                self.login_config.mode = 'none'
                
        elif choice == "4":
            self.login_config.mode = 'browser_cookies'
            print("🍪 浏览器Cookie自动提取模式")
            browser_choice = input("选择浏览器 (1-Chrome, 2-Edge, 3-自动, 默认3): ").strip() or "3"
            if browser_choice == "1":
                self.login_config.browser = 'chrome'
            elif browser_choice == "2":
                self.login_config.browser = 'edge'
            else:
                self.login_config.browser = 'auto'
            safe_print(f"✅ 已设置从{self.login_config.browser}浏览器提取Cookie")
            
        elif choice == "5":
            self.login_config.mode = 'browser_login'
            print("🌐 浏览器登录模式")
            browser_choice = input("选择启动的浏览器 (1-Chrome, 2-Edge, 3-默认, 默认3): ").strip() or "3"
            if browser_choice == "1":
                self.login_config.browser = 'chrome'
            elif browser_choice == "2":
                self.login_config.browser = 'edge'
            else:
                self.login_config.browser = 'auto'
            safe_print("✅ 已设置浏览器登录模式")
            
        else:
            safe_print("❌ 无效选择，使用无登录模式")
            self.login_config.mode = 'none'

    def ensure_login(self, site_url: str) -> requests.Session:
        """执行登录操作并返回session"""
        if self.login_config.mode == 'none':
            return self.session
            
        elif self.login_config.mode == 'cookies':
            if self.login_config.cookies:
                self.session.cookies.update(self.login_config.cookies)
                safe_print(f"✅ 已设置 {len(self.login_config.cookies)} 个Cookie")
                self.save_session()
                self.verify_login()
            return self.session
            
        elif self.login_config.mode == 'credentials':
            self.login_with_password()
            return self.session
            
        elif self.login_config.mode == 'browser_cookies':
            # 从浏览器自动提取Cookie
            parsed_url = urlparse(site_url)
            domain = parsed_url.netloc.replace('www.', '')
            
            safe_print(f"🍪 正在从{self.login_config.browser}浏览器提取Cookie...")
            cookies = self.extract_cookies_from_browser(domain, self.login_config.browser)
            
            if cookies:
                self.session.cookies.update(cookies)
                safe_print(f"✅ 成功提取 {len(cookies)} 个Cookie")
                self.save_session()
                self.verify_login()
            else:
                safe_print("❌ 未能从浏览器提取到Cookie")
            return self.session
                
        elif self.login_config.mode == 'browser_login':
            # 启动浏览器登录
            login_urls = self.find_login_urls(site_url)
            if login_urls:
                self.launch_browser_login(login_urls[0])
            else:
                safe_print("❌ 未找到登录页面")
            return self.session
        
        return self.session

    def login_with_password(self) -> bool:
        """用户名密码登录"""
        try:
            safe_print(f"🔐 正在访问登录页面: {self.login_config.login_url}")
            response = self.session.get(self.login_config.login_url, timeout=10)
            
            if response.status_code != 200:
                safe_print(f"❌ 无法访问登录页面，状态码: {response.status_code}")
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 寻找登录表单
            form = soup.find('form')
            if not form:
                safe_print("❌ 未找到登录表单")
                return False
            
            # 准备登录数据
            login_data = {}
            
            # 查找用户名和密码字段
            username_fields = ['username', 'user', 'email', 'account', 'login']
            password_fields = ['password', 'passwd', 'pwd', 'pass']
            
            inputs = form.find_all('input')
            for inp in inputs:
                name = inp.get('name', '').lower()
                input_type = inp.get('type', '').lower()
                
                if any(field in name for field in username_fields) or input_type == 'email':
                    login_data[inp.get('name')] = self.login_config.username
                elif any(field in name for field in password_fields) or input_type == 'password':
                    login_data[inp.get('name')] = self.login_config.password
                elif input_type == 'hidden':
                    login_data[inp.get('name')] = inp.get('value', '')
            
            # 提交登录
            action_url = form.get('action', '')
            if action_url:
                if action_url.startswith('/'):
                    login_url = urlparse(self.login_config.login_url)
                    submit_url = f"{login_url.scheme}://{login_url.netloc}{action_url}"
                else:
                    submit_url = urljoin(self.login_config.login_url, action_url)
            else:
                submit_url = self.login_config.login_url
            
            safe_print("🔑 正在提交登录信息...")
            login_response = self.session.post(submit_url, data=login_data, timeout=10)
            
            if login_response.status_code == 200:
                # 检查登录是否成功
                if self.verify_login():
                    safe_print("✅ 登录成功！")
                    self.save_session()
                    return True
                else:
                    safe_print("❌ 登录失败，请检查用户名和密码")
                    return False
            else:
                safe_print(f"❌ 登录请求失败，状态码: {login_response.status_code}")
                return False
                
        except Exception as e:
            safe_print(f"❌ 登录过程出错: {str(e)}")
            return False

    def verify_login(self) -> bool:
        """验证登录状态"""
        try:
            # 简单检查：有Cookie就认为登录成功
            if len(self.session.cookies) > 0:
                safe_print("✅ 登录状态验证通过")
                return True
            else:
                safe_print("❌ 未检测到登录Cookie")
                return False
                
        except Exception as e:
            safe_print(f"⚠️  登录验证失败: {str(e)}")
            return False

    def save_session(self) -> None:
        """保存会话信息"""
        try:
            session_file = "session_cookies.json"
            cookies_dict = {}
            
            # 安全地转换cookies
            for cookie in self.session.cookies:
                if hasattr(cookie, 'name') and hasattr(cookie, 'value'):
                    cookies_dict[cookie.name] = cookie.value
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_dict, f, ensure_ascii=False, indent=2)
                
            safe_print(f"💾 会话已保存到: {session_file}")
        except Exception as e:
            safe_print(f"⚠️  会话保存失败: {str(e)}")

    def load_session(self) -> bool:
        """加载保存的会话"""
        try:
            session_file = "session_cookies.json"
            if os.path.exists(session_file):
                with open(session_file, 'r', encoding='utf-8') as f:
                    cookies_dict = json.load(f)
                    
                self.session.cookies.update(cookies_dict)
                safe_print(f"📁 已加载保存的会话")
                return True
        except Exception as e:
            safe_print(f"⚠️  会话加载失败: {str(e)}")
            
        return False

    def get_browser_cookie_paths(self) -> Dict[str, str]:
        """获取浏览器Cookie数据库路径"""
        system = platform.system()
        home = Path.home()
        
        paths = {}
        
        if system == "Windows":
            paths['chrome'] = home / "AppData/Local/Google/Chrome/User Data/Default/Cookies"
            paths['edge'] = home / "AppData/Local/Microsoft/Edge/User Data/Default/Cookies"
        elif system == "Darwin":  # macOS
            paths['chrome'] = home / "Library/Application Support/Google/Chrome/Default/Cookies"
            paths['edge'] = home / "Library/Application Support/Microsoft Edge/Default/Cookies"
        elif system == "Linux":
            paths['chrome'] = home / ".config/google-chrome/Default/Cookies"
            paths['edge'] = home / ".config/microsoft-edge/Default/Cookies"
            
        return {k: str(v) for k, v in paths.items() if v.exists()}

    def extract_cookies_from_browser(self, domain: str, browser: str = 'auto') -> Dict[str, str]:
        """从浏览器提取指定域名的Cookie"""
        cookie_paths = self.get_browser_cookie_paths()
        
        if browser == 'auto':
            # 优先使用Edge，然后Chrome
            browsers_to_try = ['edge', 'chrome']
        else:
            browsers_to_try = [browser]
            
        for browser_name in browsers_to_try:
            if browser_name not in cookie_paths:
                continue
                
            try:
                return self._extract_cookies_from_db(cookie_paths[browser_name], domain)
            except Exception as e:
                safe_print(f"⚠️  从{browser_name}提取Cookie失败: {e}")
                continue
                
        return {}

    def _extract_cookies_from_db(self, db_path: str, domain: str) -> Dict[str, str]:
        """从Cookie数据库文件提取Cookie"""
        try:
            # 复制数据库文件避免锁定
            import tempfile
            import shutil
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
                shutil.copy2(db_path, tmp_file.name)
                temp_db_path = tmp_file.name
            
            try:
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()
                
                # Chrome/Edge Cookie数据库结构
                query = """
                    SELECT name, value, host_key 
                    FROM cookies 
                    WHERE host_key LIKE ? OR host_key LIKE ?
                """
                
                cursor.execute(query, (f'%{domain}%', f'%.{domain}%'))
                rows = cursor.fetchall()
                
                cookies = {}
                for name, value, host_key in rows:
                    if domain in host_key:
                        cookies[name] = value
                        
                conn.close()
                return cookies
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_db_path)
                except:
                    pass
                    
        except Exception as e:
            raise Exception(f"数据库访问失败: {e}")

    def launch_browser_login(self, login_url: str) -> bool:
        """启动浏览器进行登录"""
        try:
            safe_print(f"🌐 正在启动浏览器，请在浏览器中完成登录...")
            safe_print(f"🔗 登录页面: {login_url}")
            
            # 尝试启动浏览器
            webbrowser.open(login_url)
            
            print("\n请在浏览器中完成以下步骤：")
            print("1. 📝 输入用户名和密码")
            print("2. ✅ 完成登录验证")
            print("3. 🔄 登录成功后，返回这里按回车继续")
            
            input("\n按回车键继续...")
            
            # 提取域名
            parsed_url = urlparse(login_url)
            domain = parsed_url.netloc.replace('www.', '')
            
            # 尝试从浏览器获取Cookie
            safe_print("🍪 正在从浏览器提取Cookie...")
            cookies = self.extract_cookies_from_browser(domain)
            
            if cookies:
                self.session.cookies.update(cookies)
                safe_print(f"✅ 成功提取 {len(cookies)} 个Cookie")
                self.save_session()
                return self.verify_login()
            else:
                safe_print("❌ 未能提取到Cookie，请确保已完成登录")
                return False
                
        except Exception as e:
            safe_print(f"❌ 浏览器登录失败: {e}")
            return False

    def parse_cookie_string(self, cookie_str: str) -> Dict[str, str]:
        """解析Cookie字符串"""
        cookies = {}
        for item in cookie_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies

    def find_login_urls(self, site_url: str) -> List[str]:
        """查找可能的登录URL"""
        parsed_url = urlparse(site_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # 常见登录路径
        common_paths = [
            '/login',
            '/user/login', 
            '/member/login',
            '/signin',
            '/user.html',
            '/login.html',
            '/member.html'
        ]
        
        login_urls = []
        for path in common_paths:
            login_urls.append(base_url + path)
            
        return login_urls 