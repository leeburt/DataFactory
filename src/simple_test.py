#!/usr/bin/env python3
"""
简单的同步模式测试脚本
用于测试ModelClient的基本功能
"""

import requests
import json
import time
import os
from image_processor import ImageProcessor
# base64
import base64

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def simple_api_call(prompt, query="", image_path=None, enforce_json=False):
    """简单的API调用函数"""
    
    # API配置
    api_base = "http://0.0.0.0:8000/v1"
    api_key = "111"
    model = "checkpoint-135"
    
    # 构建请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 构建消息内容
    content = []
    
    
    # 如果有图像，添加图像内容
    if image_path and os.path.exists(image_path):
        try:
            print(f"正在处理图像: {image_path}")
            image_base64 = encode_image(image_path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })
            print(f"图像编码完成，长度: {len(image_base64)}")
        except Exception as e:
            print(f"图像处理失败: {e}")
            return None
    
    content.append({"type": "text", "text": f"{prompt}".strip()})
    # 构建系统消息
    system_message = "You are a professional circuit diagram analysis assistant. Please answer questions according to the user-specified format"
    if enforce_json:
        system_message = "You are a professional circuit diagram analysis assistant, always reply in pure JSON format. Do not use Markdown code blocks, do not add any prefix or suffix text, only return raw JSON. Your output should be directly parseable by JSON parsers without any preprocessing."

    # 构建消息列表
    messages = [
        {
            "role": "user",
            "content": content
        }
    ]
    
    # 构建请求载荷
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 512
    }
    
    # 如果需要JSON格式，添加响应格式
    if enforce_json:
        payload["response_format"] = {"type": "json_object"}
    
    # 发送请求
    api_endpoint = f"{api_base}/chat/completions"
    
    try:
        print(f"发送请求到: {api_endpoint}")
        print(f"模型: {model}")
        print(f"提示词: {prompt}")
        if query:
            print(f"查询: {query}")
        
        start_time = time.time()
        response = requests.post(
            api_endpoint,
            headers=headers,
            json=payload,
            timeout=180.0
        )
        end_time = time.time()
        
        print(f"请求耗时: {end_time - start_time:.2f}秒")
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                
                print("=== 响应内容 ===")
                print(content)
                print("\n=== 使用统计 ===")
                print(f"Token使用: {usage}")
                
                # 如果是JSON模式，尝试解析
                if enforce_json:
                    try:
                        json_data = json.loads(content)
                        print("\n=== JSON解析成功 ===")
                        print(json.dumps(json_data, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError as e:
                        print(f"\n=== JSON解析失败 ===")
                        print(f"错误: {e}")
                
                return {
                    "content": content,
                    "usage": usage,
                    "response_time": end_time - start_time
                }
            else:
                print("无效的API响应格式")
                return None
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"请求异常: {e}")
        return None
    except Exception as e:
        print(f"其他异常: {e}")
        return None


def test_text_only():
    """测试纯文本请求"""
    print("=" * 60)
    print("测试1: 纯文本请求")
    print("=" * 60)
    
    prompt = "请分析电路图的基本组成"
    query = "描述主要的电路元件和它们的作用"
    
    result = simple_api_call(prompt, query)
    if result:
        print("✅ 纯文本测试成功")
    else:
        print("❌ 纯文本测试失败")
    print()


def test_json_mode():
    """测试JSON模式"""
    print("=" * 60)
    print("测试2: JSON模式")
    print("=" * 60)
    
    prompt = "请分析电路图并返回结构化数据"
    query = "包含组件类型、数量和连接关系的JSON格式"
    
    result = simple_api_call(prompt, query, enforce_json=True)
    if result:
        print("✅ JSON模式测试成功")
    else:
        print("❌ JSON模式测试失败")
    print()


def test_with_image():
    """测试带图像的请求"""
    print("=" * 60)
    print("测试3: 图像分析")
    print("=" * 60)
    
    image_path = "/data/home/libo/work/DataFactory/.cache/images/583_block_circuit_train_15k_0321_000858.jpg"
    
    if not os.path.exists(image_path):
        print(f"图像文件不存在: {image_path}")
        print("跳过图像测试")
        return
    
    prompt = "What are the connections for the component located in       <|box_start|>(150,50),(209,109)<|box_end|>?"
    query = ""
    
    result = simple_api_call(prompt, query, image_path=image_path)
    if result:
        print("✅ 图像分析测试成功")
    else:
        print("❌ 图像分析测试失败")
    print()


def main():
    """主函数"""
    print("开始同步模式API测试")
    print("当前时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # 运行测试
    # test_text_only()
    # test_json_mode()
    test_with_image()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main() 