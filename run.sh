#!/bin/bash

echo "电路图两步评估工具"
echo "==========================================="

# 创建结果目录
mkdir -p ./results

# 运行评估程序
python3 main.py --config ./config/run_config.json

echo "评估完成!" 