#!/bin/bash

echo "电路图两步评估工具"
echo "==========================================="

# 运行评估程序
python3 main.py --config  ./config/run_config.json --output-dir ./results/4o_pk_o4_mini

echo "评估完成!" 