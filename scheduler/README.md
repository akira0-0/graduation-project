# 自动化爬虫调度器

每天早上10点和晚上10点自动运行微博、小红书、网易新闻爬虫，获取微博热搜作为关键词。

## 快速开始

### 1. 手动运行（测试）

```bash
cd e:\xhs-crawler

# 运行完整任务（自动获取热搜）
uv run python -m scheduler.main run

# 使用指定关键词
uv run python -m scheduler.main run --keywords "人工智能,科技新闻"

# 只运行部分爬虫
uv run python -m scheduler.main run --no-weibo  # 不运行微博
uv run python -m scheduler.main run --no-xhs    # 不运行小红书
uv run python -m scheduler.main run --no-web    # 不运行网易
```

### 2. 设置定时任务

以管理员身份运行：

```bash
scheduler\setup_scheduled_task.bat
```

这会创建两个 Windows 定时任务，每天 10:00 和 22:00 自动运行。

### 3. 其他命令

# 导入所有日期的数据
uv run python -m scheduler.main import --all
uv run python -m scheduler.main import -a

# 导入指定日期
uv run python -m scheduler.main import --date 2026-03-01
uv run python -m scheduler.main import -d 2026-03-01

# 导入今天的数据（默认）
uv run python -m scheduler.main import
```bash
# 测试获取热搜
uv run python -m scheduler.main test-hot

# 仅运行数据转换
uv run python -m scheduler.main convert

# 仅运行数据入库
uv run python -m scheduler.main import
```

## 执行流程

```
1. 获取微博热搜词（15个）
        ↓
2. 并行/串行运行爬虫
   - 微博爬虫（一次性传入所有关键词）
   - 小红书爬虫（每个关键词单独运行）
   - 网易新闻爬虫（一次性传入所有关键词）
        ↓
3. 数据格式转换
   - 小红书: data/xhs/json → data/unified/xhs
   - 微博/网易: 已是统一格式，无需转换
        ↓
4. 数据入库（Supabase）
   - 读取 data/unified/ 下所有平台数据
   - 写入 posts 和 comments 表
```

## 配置说明

修改 `scheduler/config.py`：

```python
# 调度配置
SCHEDULE_TIMES = [time(10, 0), time(22, 0)]  # 每日执行时间：10:00 和 22:00
HOT_SEARCH_COUNT = 15       # 热搜词数量

# 爬虫开关
ENABLE_WEIBO = True
ENABLE_XHS = True
ENABLE_WEB = True

# 爬取数量
WEIBO_MAX_PAGES = 3         # 微博每个关键词爬取页数
XHS_MAX_NOTES = 20          # 小红书每个关键词爬取笔记数
WEB_MAX_ARTICLES = 5        # 网易每个关键词爬取文章数

# 超时和重试
CRAWLER_TIMEOUT = 600       # 单个关键词爬取超时(秒)
RETRY_COUNT = 2             # 失败重试次数
```

## 日志

日志保存在 `logs/` 目录：

```
logs/
├── scheduler_2026-03-01.log
├── scheduler_2026-03-02.log
└── ...
```

## 文件结构

```
scheduler/
├── __init__.py        # 模块导出
├── config.py          # 配置
├── main.py            # 主入口
├── hot_search.py      # 热搜获取
├── runner.py          # 爬虫运行器
├── converter.py       # 格式转换
├── importer.py        # 数据库导入
├── logger.py          # 日志模块
├── run_daily_task.bat        # 运行脚本
├── setup_scheduled_task.bat  # 创建定时任务
└── README.md          # 本文档
```

## 注意事项

1. **微博 Cookie**: 确保 `weibo_crawler/weibo_crawler/config.json` 中的 Cookie 有效
2. **小红书登录**: 首次运行需要扫码登录，后续会保存登录状态
3. **网易新闻**: 使用 DrissionPage，需要安装 Chrome 浏览器
4. **权限**: 创建定时任务需要管理员权限
