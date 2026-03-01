# 微博爬虫 (Weibo Crawler)

一个用于学术研究的微博数据爬虫工具。

## 功能特性

- 🔍 关键词搜索微博
- 💬 获取评论数据
- 📝 支持长文本获取
- 💾 自动保存为 JSON 格式

## 快速开始

### 1. 安装依赖

**本项目使用父项目 (xhs-crawler) 的虚拟环境**

在父项目根目录执行：

```bash
cd e:\xhs-crawler
uv sync
```

### 2. 配置 Cookie

1. 访问 https://m.weibo.cn 并登录
2. 打开浏览器开发者工具 (F12)
3. 切换到 Network 标签
4. 刷新页面，找到任意请求
5. 复制 Cookie 值
6. 复制 `config.json.template` 为 `config.json`
7. 粘贴 Cookie 到 `config.json` 的 `cookie` 字段

### 3. 配置关键词

编辑 `config.json`:

```json
{
  "cookie": "你的Cookie",
  "keywords": ["Python", "AI"],
  "max_pages": 3
}
```

### 4. 运行爬虫

**方式 1：使用批处理脚本（推荐）**

在父项目根目录双击运行：
```
run_weibo_crawler.bat
```

**方式 2：使用 uv run**

```bash
cd e:\xhs-crawler
uv run weibo_crawler\weibo_crawler\main.py
```

**方式 3：激活虚拟环境后运行**

```bash
cd e:\xhs-crawler
.venv\Scripts\activate
python weibo_crawler\weibo_crawler\main.py
```

## 数据输出

爬取的数据保存在 `data/` 目录下：

- `task_YYYYMMDD_posts_YYYYMMDD_HHMMSS.json` - 微博帖子数据
- `task_YYYYMMDD_comments_YYYYMMDD_HHMMSS.json` - 评论数据

## 注意事项

⚠️ **仅供学习研究使用**

- 请遵守微博平台使用条款
- 控制请求频率，避免被封禁
- 不要用于商业用途
- Cookie 会过期，需定期更新

## 项目结构

```
weibo_crawler/
├── pyproject.toml      # uv 项目配置
├── config.json         # 爬虫配置
├── main.py            # 主程序入口
├── crawler.py         # 爬虫核心逻辑
├── utils.py           # 工具函数
└── data/              # 数据输出目录
```

## License

仅供学习和研究使用
