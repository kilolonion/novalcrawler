# 🧪 本地测试服务器

专门用于测试小说爬虫功能的本地模拟网站。

## 📋 功能特性

- ✅ **完整的小说网站结构** - 包含目录页、章节页、分页等
- ✅ **50个测试章节** - 足够的内容用于测试各种功能
- ✅ **规范的HTML结构** - 符合常见小说网站的页面布局
- ✅ **无反爬虫限制** - 专门为测试设计，无访问限制
- ✅ **支持robots.txt** - 测试爬虫的robots协议遵守功能
- ✅ **多种内容格式** - 包含段落、列表、特殊字符等

## 🚀 快速启动

### 方法1：使用启动脚本（推荐）

```bash
python test_server/start_server.py
```

脚本会自动：
- 检查并安装Flask依赖
- 启动测试服务器
- 打开浏览器访问测试网站

### 方法2：直接运行

```bash
# 安装依赖
pip install flask

# 启动服务器
python test_server/app.py
```

## 📍 访问地址

- **网站首页**: http://localhost:8080
- **章节示例**: http://localhost:8080/chapter/1
- **Robots.txt**: http://localhost:8080/robots.txt
- **网站地图**: http://localhost:8080/sitemap.xml

## 🧪 测试用例

### 基本功能测试

```bash
# 使用爬虫测试目录页面
python universal_novel_crawler.py -u http://localhost:8080

# 测试章节范围下载
python universal_novel_crawler.py -u http://localhost:8080 -r 1-10

# 测试多线程下载
python universal_novel_crawler.py -u http://localhost:8080 -r 1-5 -t 3
```

### 高级功能测试

```bash
# 测试robots.txt检查
python universal_novel_crawler.py -u http://localhost:8080 --debug

# 测试文件合并功能
python universal_novel_crawler.py -u http://localhost:8080 -r 1-5 --merge

# 测试断点续传
python universal_novel_crawler.py -u http://localhost:8080 -r 1-20
# 中断后再次运行，测试续传功能
python universal_novel_crawler.py -u http://localhost:8080 -r 1-20
```

## 📊 网站结构

```
http://localhost:8080/
├── /                           # 首页目录（支持分页）
├── /chapter/1                  # 第1章
├── /chapter/2                  # 第2章
├── ...                         # 更多章节
├── /chapter/50                 # 第50章
├── /robots.txt                 # 机器人协议
└── /sitemap.xml               # 网站地图
```

## 🎯 测试重点

使用这个测试服务器可以验证以下爬虫功能：

1. **目录解析** - 测试章节链接提取
2. **内容提取** - 测试正文内容清理
3. **分页处理** - 测试多页目录的处理
4. **并发下载** - 测试多线程下载效率
5. **错误处理** - 测试异常情况的处理
6. **文件管理** - 测试文件命名和保存
7. **robots.txt** - 测试协议遵守功能

## 💡 使用建议

- 🔧 **开发调试**: 修改爬虫代码时用于快速验证
- 🧪 **功能测试**: 验证新增功能是否正常工作
- 📊 **性能测试**: 测试并发下载和处理速度
- 🛡️ **安全测试**: 确保不会对真实网站造成负担

## 🔧 自定义配置

你可以修改 `app.py` 中的配置：

```python
# 修改章节数量
for i in range(1, 101):  # 改为100章

# 修改分页大小
per_page = 30  # 每页30章

# 修改端口
app.run(port=8080)  # 使用8080端口
```

## ⚠️ 注意事项

- 服务器仅用于本地测试，不要在生产环境使用
- 测试完成后记得停止服务器（Ctrl+C）
- 如果端口5000被占用，可以修改为其他端口 