@echo off
setlocal enabledelayedexpansion

echo 电路图两步评估工具
echo ===========================================

rem 创建结果目录
if not exist ".\results" mkdir ".\results"

rem 运行评估程序
python main.py --config ./config/run_config.json

echo 评估完成!
pause 