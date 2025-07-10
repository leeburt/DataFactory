#!/bin/bash

echo "开始运行同步模式测试..."
echo "当前目录: $(pwd)"
echo "Python版本: $(python3 --version)"
echo

# 检查依赖
echo "检查Python依赖..."
python3 -c "import requests; print('✅ requests 已安装')" 2>/dev/null || echo "❌ 需要安装 requests: pip install requests"
python3 -c "import PIL; print('✅ PIL 已安装')" 2>/dev/null || echo "❌ 需要安装 PIL: pip install Pillow"

echo

# 运行简单测试
echo "运行简单测试..."
cd src
python3 simple_test.py

echo
echo "运行完整测试..."
python3 test_model_client_sync.py

echo
echo "测试完成!" 