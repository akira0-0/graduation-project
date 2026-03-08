@echo off
chcp 65001 >nul
echo ========================================
echo 清理临时浏览器数据目录
echo ========================================
echo.

echo 选择操作:
echo 1. 查看临时目录（不删除）
echo 2. 删除所有临时目录
echo 3. 保留最新5个，删除其他
echo 4. 退出
echo.

set /p choice=请输入选项 (1-4): 

if "%choice%"=="1" (
    echo.
    echo [查看模式] 扫描临时目录...
    python scripts\cleanup_temp_browsers.py --dry-run
    goto end
)

if "%choice%"=="2" (
    echo.
    echo [删除模式] 确认要删除所有临时目录吗？
    set /p confirm=输入 Y 确认: 
    if /i "%confirm%"=="Y" (
        python scripts\cleanup_temp_browsers.py
    ) else (
        echo 已取消
    )
    goto end
)

if "%choice%"=="3" (
    echo.
    echo [保留模式] 将保留最新的5个目录
    python scripts\cleanup_temp_browsers.py --keep-latest 5
    goto end
)

if "%choice%"=="4" (
    echo 已退出
    goto end
)

echo 无效的选项！

:end
echo.
pause
