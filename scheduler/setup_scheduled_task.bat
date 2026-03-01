@echo off
chcp 65001 >nul
echo ============================================================
echo 创建 Windows 定时任务（每天早上10点和晚上10点）
echo ============================================================

REM 任务名称
set TASK_NAME_AM=DailyCrawlerTask_AM
set TASK_NAME_PM=DailyCrawlerTask_PM

REM 脚本路径
set SCRIPT_PATH=E:\xhs-crawler\scheduler\run_daily_task.bat

REM 删除已存在的同名任务
schtasks /delete /tn "%TASK_NAME_AM%" /f 2>nul
schtasks /delete /tn "%TASK_NAME_PM%" /f 2>nul
schtasks /delete /tn "DailyCrawlerTask" /f 2>nul

REM 创建每日 10:00 执行的定时任务（早上）
schtasks /create /tn "%TASK_NAME_AM%" /tr "%SCRIPT_PATH%" /sc daily /st 10:00 /f

REM 创建每日 22:15 执行的定时任务（晚上）
schtasks /create /tn "%TASK_NAME_PM%" /tr "%SCRIPT_PATH%" /sc daily /st 22:15 /f

if %errorlevel% equ 0 (
    echo.
    echo [OK] 定时任务创建成功！
    echo.
    echo 任务1: %TASK_NAME_AM% - 每天 10:00
    echo 任务2: %TASK_NAME_PM% - 每天 22:15
    echo 脚本路径: %SCRIPT_PATH%
    echo.
    echo 管理命令:
    echo   查看任务: schtasks /query /tn "%TASK_NAME_AM%" /v
    echo   立即运行: schtasks /run /tn "%TASK_NAME_AM%"
    echo   删除任务: schtasks /delete /tn "%TASK_NAME_AM%" /f
    echo             schtasks /delete /tn "%TASK_NAME_PM%" /f
    echo.
) else (
    echo.
    echo [ERROR] 创建失败，请以管理员身份运行此脚本
    echo.
)

pause
