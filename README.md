# Z-Reader - 小说下载工具

**Z-Reader** 是一个基于 Python 的小说搜索与下载工具，提供现代化的 Web 界面，支持多书源配置和并发下载。

本项目从 [sonovel](https://github.com/freeok/so-novel) 重构得来。

支持大部分主流网络小说网站（番茄、起点等）。

仅供学习交流使用。

可前往 [Release](https://github.com/HereisFrank9527/Z-Reader/releases) 下载windows版本，支持win7及以上，仅20MB。


## ✨ 项目特点

- 🌐 **Web 界面**: 基于 Flask 的现代化 Web 界面，支持移动设备
- 📚 **多书源支持**: 完全基于规则配置，支持 11+ 书源
- 🔍 **智能搜索**: 支持按关键词搜索，可指定书源或搜索所有书源
- ⬇️ **并发下载**: 支持多线程并发下载，可配置线程数
- 📊 **任务管理**: 实时查看下载进度，管理下载任务
- 📁 **文件管理**: 查看和下载已完成的文件
- 🎨 **美观UI**: 渐变色主题，响应式设计

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
python server.py
```

### 3. 访问界面

浏览器打开：`http://localhost:5000`

## 📖 使用说明

### 🔍 搜索书籍
1. 在搜索框输入关键词
2. 选择特定书源或搜索所有书源
3. 查看搜索结果，显示书名、作者、分类、状态等信息

### ⬇️ 下载管理
1. 点击书籍进入详情页
2. 设置起始和结束章节
3. 开始下载，实时查看进度
4. 支持多任务同时下载

### 📁 文件管理
1. 在"已下载"页面查看所有下载完成的文件
2. 点击文件名可直接下载到本地
3. 文件保存在 `downloads/` 目录下


### 配置文件
- `rules/main-rules.json`: 主要书源规则
- `rules/flowlimit-rules.json`: 流量限制配置
- `rules/proxy-rules.json`: 代理配置
- `rules/rule-template.json5`: 规则模板


## 📁 项目结构

## 项目目录结构

```
Z-reader/
├── core/                    # 核心功能层
│   ├── __init__.py         # 包初始化
│   ├── downloader.py       # 下载器 - 协调整个下载流程
│   ├── http_client.py      # HTTP客户端 - 封装网络请求
│   ├── rule_loader.py      # 规则加载器 - 管理书源规则
│   └── selector.py         # 选择器 - HTML解析和提取
│
├── models/                  # 数据模型层
│   ├── __init__.py         # 包初始化
│   ├── book.py             # 书籍模型
│   ├── chapter.py          # 章节模型
│   └── rule.py             # 规则模型
│
├── parsers/                 # 解析器层
│   ├── __init__.py         # 包初始化
│   ├── book_parser.py      # 书籍详情解析器
│   ├── chapter_parser.py   # 章节内容解析器
│   ├── search_parser.py    # 搜索结果解析器
│   └── toc_parser.py       # 目录解析器
│
├── rules/                   # 书源规则配置
│   ├── main-rules.json     # 主要书源规则
│   ├── flowlimit-rules.json # 流量限制规则
│   ├── non-searchable-rules.json # 不可搜索书源
│   ├── proxy-rules.json    # 代理规则
│   └── rule-template.json5 # 规则模板
│
├── utils/                   # 工具模块
│   ├── __init__.py         # 包初始化
│   └── file_utils.py       # 文件操作工具
│
├── static/                  # 静态资源
│   ├── css/
│   │   └── style.css       # 样式文件
│   └── js/
│       └── app.js          # 前端JavaScript
│
├── templates/               # HTML模板
│   ├── index.html          # 主页面模板
|   └── index.md            # 公告文件
│
├── downloads/               # 下载文件存储
│
├── tests/                   # 测试模块
│   ├── __init__.py         # 包初始化
│   ├── examples.py         # 测试示例
│   ├── test_basic.py       # 基础测试
│   └── test_parsers.py     # 解析器测试
│
├── server.py               # Flask Web服务器
├── requirements.txt        # Python依赖
├── check_sources.py        # 书源检查工具
└── test_sources.py         # 书源测试工具
```

## 核心模块详解

### 1. 数据模型层 (models/)

#### book.py - 书籍模型
定义书籍信息的数据结构，包含书名、作者、简介、分类、状态等字段。

#### chapter.py - 章节模型
定义章节信息的数据结构，包含标题、URL、内容、索引等字段。

#### rule.py - 规则模型
定义书源规则的数据结构，包含搜索规则、书籍规则、目录规则、章节规则等配置。

### 2. 核心功能层 (core/)

#### downloader.py - 下载器
协调整个下载流程，包括获取书籍信息、解析目录、并发下载章节、保存文件等。

#### http_client.py - HTTP客户端
封装网络请求功能，提供自动重试、请求间隔控制、SSL验证等功能。

#### rule_loader.py - 规则加载器
负责加载和解析JSON格式的书源规则文件，管理多个书源配置。

#### selector.py - 选择器
提供HTML解析和内容提取功能，支持CSS选择器和XPath表达式。

### 3. 解析器层 (parsers/)

#### search_parser.py - 搜索解析器
解析搜索结果页面，提取书籍列表信息。

#### book_parser.py - 书籍解析器
解析书籍详情页面，提取书籍的详细信息。

#### toc_parser.py - 目录解析器
解析章节目录页面，提取章节列表。

#### chapter_parser.py - 章节解析器
解析章节内容页面，提取章节正文内容。

### 4. Web界面 (server.py)
基于Flask框架的Web服务器，提供用户界面和API接口，支持搜索、下载、文件管理等功能。

## 🛠️ 开发说明

### 添加新书源
1. 在 `rules/` 目录下创建新的规则文件
2. 参考 `rule-template.json5` 格式编写规则
3. 使用 `check_sources.py` 验证规则有效性

### 自定义功能
- 修改 `server.py` 可调整Web界面
- 扩展 `parsers/` 可添加新的解析逻辑
- 修改 `core/` 可调整核心下载逻辑

## 📝 许可证

GPL-3.0

## 支持

如有问题，请查看项目文档或提交Issue。

## 打赏
<details>
<summary>Buy me a cup of coffee！</summary>
<img src="/static/pic.jpg" width="400" height="400">
</details>
---

**版本**: 1.0.0 | **更新**: 2025-10-30