#!/usr/bin/env python3
"""
测试标注保存功能
"""
import requests
import json
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_save_annotation():
    """测试保存标注功能"""
    
    # 测试数据
    test_data = {
        "image_name": "6.jpg",  # 替换为实际的图像名称
        "component_coords": "[569, 190, 723, 400]",  # 替换为实际的组件坐标
        "label": "incorrect"
    }
    
    # 服务器地址
    url = "http://192.168.99.119:5001/save_annotation"
    
    print("=== 测试标注保存功能 ===")
    print(f"发送数据: {test_data}")
    
    try:
        # 发送POST请求
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应数据: {result}")
            
            if result.get('success'):
                print("✅ 保存成功!")
            else:
                print(f"❌ 保存失败: {result.get('message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

def test_get_stats():
    """测试获取统计信息功能"""
    
    # 服务器地址
    url = "http://192.168.99.119:5001/get_annotation_stats/6"
    
    print("\n=== 测试获取统计信息功能 ===")
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"统计数据: {result}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

if __name__ == "__main__":
    test_save_annotation()
    test_get_stats() 