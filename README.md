# GitHub Trending 爬虫技术文档

## 1. 项目概述

### 1.1 功能描述

GitHub Trending 爬虫是一个自动化工具，用于定期抓取 GitHub 平台上的热门项目信息。该工具能够获取项目名称、编程语言、收藏数、分支数、项目描述等数据，并将英文描述翻译成中文，最终生成 CSV 格式的数据报告。

### 1.2 主要特点

- 自动爬取 GitHub 热门项目列表
- 提供英文描述到中文的自动翻译功能
- 支持定时执行，可配置为每日固定时间运行
- 完整的日志记录系统，便于追踪程序运行状态
- 数据以 CSV 格式保存，方便后续分析和处理

## 2. 系统架构

### 2.1 技术栈

- **编程语言**：Python
- **主要依赖库**：
  - requests：处理 HTTP 请求
  - BeautifulSoup4：解析 HTML 内容
  - pandas：数据处理与 CSV 文件生成
  - schedule：实现定时任务
  - logging：日志管理

### 2.2 系统流程

1. 初始化配置和日志系统
2. 定时触发爬虫任务
3. 发送请求获取 GitHub Trending 页面
4. 解析 HTML 提取项目数据
5. 翻译项目描述（英文→中文）
6. 将数据保存为 CSV 文件
7. 等待下一次定时任务

## 3. 模块详解

### 3.1 翻译模块

#### 3.1.1 `translate_to_chinese(text)`

主要翻译接口，接收英文文本并返回中文翻译结果。内部调用 `translate_fallback` 方法执行实际翻译操作。

#### 3.1.2 `translate_fallback(text)`

实现了一个备用翻译方法，通过 Google Translate API 进行翻译：

- 使用 HTTP GET 请求访问 Google 翻译 API
- 设置源语言(英文)和目标语言(中文)
- 解析 JSON 响应获取翻译结果
- 处理可能出现的异常情况并记录日志

### 3.2 数据处理模块

#### 3.2.1 `parse_number(number_str)`

将字符串形式的数字转换为整数值：

- 支持处理带单位的数字，如 "1.5k"、"2.3m" 等
- 自动转换为对应的整数值（k=千，m=百万）
- 处理包含逗号的数字格式，如 "1,234"

### 3.3 爬虫核心模块

#### 3.3.1 `scrape_github_trending()`

实现了 GitHub 热门项目数据的爬取逻辑：

- 设置 User-Agent 头信息模拟浏览器访问
- 使用 BeautifulSoup 解析 HTML 页面内容
- 通过 CSS 选择器定位并提取各项目数据
- 提取信息包括：项目名称、编程语言、描述、收藏数、分支数、当日收藏数等
- 对英文描述进行中文翻译
- 将所有数据整合为结构化的列表返回

### 3.4 数据保存模块

#### 3.4.1 `save_to_csv(data)`

负责将爬取的数据保存为 CSV 文件：

- 使用当前日期命名文件（格式：github-trending-YYYY-MM-DD.csv）
- 使用 pandas DataFrame 进行数据结构化
- 采用 utf-8-sig 编码确保中文正确显示
- 返回保存状态，并记录相关日志

### 3.5 任务调度模块

#### 3.5.1 `job()`

定义了单次执行的完整任务流程：

- 调用爬虫获取数据
- 将获取的数据保存为 CSV 文件
- 记录执行状态日志

#### 3.5.2 `main()`

程序入口函数，负责初始化并设置定时任务：

- 启动时立即执行一次爬虫任务
- 设置定时执行计划（每天 10:00）
- 进入循环，持续检查并执行待处理的定时任务

## 4. 错误处理

### 4.1 异常捕获机制

- 各功能模块都包含 try-except 结构，确保单点失败不影响整体运行
- 网络请求异常处理：捕获连接超时、服务器错误等情况
- 数据解析异常处理：应对页面结构变化导致的选择器失效
- 翻译服务异常处理：处理翻译 API 访问受限或响应异常

### 4.2 日志系统

- 采用 Python 标准 logging 模块实现多级日志
- 日志同时输出到文件和控制台
- 记录包括：INFO（正常操作日志）、WARNING（警告信息）、ERROR（错误信息）
- 日志内容包含时间戳、日志级别和详细信息

## 5. 使用指南

### 5.1 环境要求

- Python 3.6 或更高版本
- 依赖包：requests, beautifulsoup4, pandas, schedule

### 5.2 安装步骤

```bash
pip install requests beautifulsoup4 pandas schedule
```

### 5.3 运行方法

直接执行 Python 脚本：

```bash
python github_trending_scraper.py
```

### 5.4 配置说明

可根据需要修改以下配置：

- 定时执行频率：修改 `schedule.every().day.at("10:00").do(job)` 部分
- 日志级别：调整 `logging.basicConfig()` 中的 level 参数

## 6. 输出说明

### 6.1 CSV 文件结构

生成的 CSV 文件包含以下字段：

- 项目名称：GitHub 仓库全名（用户名/仓库名）
- 使用语言：项目主要编程语言
- 收藏数：项目总 Star 数
- 分支数：项目 Fork 数量
- 描述：原始英文项目描述
- 中文描述：翻译后的中文项目描述
- 当日收藏：24 小时内新增的 Star 数

### 6.2 日志输出

日志文件 `github_trending_scraper.log` 记录程序运行的完整过程，包括：

- 启动和结束信息
- 数据抓取状态
- 翻译过程
- 文件保存结果
- 异常和错误信息

## 7. 注意事项与限制

1. **请求频率限制**：过于频繁的请求可能导致 GitHub 临时封禁 IP
2. **页面结构变化**：GitHub 界面更新可能导致选择器失效，需及时更新
3. **翻译服务限制**：Google 翻译 API 可能有使用频率限制
4. **无登录状态**：当前实现不支持访问需要登录的内容

## 8. 未来改进方向

1. 添加多语言支持，允许将描述翻译为更多语种
2. 实现多页数据抓取，获取更全面的热门项目信息
3. 增加代理 IP 池，避免请求频率限制
4. 支持更多数据导出格式，如 JSON、Excel 等
5. 开发 Web 界面，便于可视化查看和配置

## 9. 附录

### 9.1 依赖库版本要求

- requests >= 2.25.0
- beautifulsoup4 >= 4.9.3
- pandas >= 1.1.5
- schedule >= 1.0.0

### 9.2 相关资源

- GitHub Trending 页面：https://github.com/trending
- Google Translate API 文档：https://cloud.google.com/translate