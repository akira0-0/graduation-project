1. 数据库配置：
   请在 spider.py 的第 36-43 行修改 REDIS_CFG 和 PG_CFG 的 host 和 password，适配服务器环境。

2. 运行模式：
   代码已做自动适配。
   - 在 Windows/Mac 上运行会自动弹出浏览器（有头模式）。
   - 在 Linux 服务器上运行会自动静默执行（无头模式）。