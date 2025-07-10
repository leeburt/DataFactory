import requests
import json
import time
from typing import Dict, Any
import traceback
from image_processor import ImageProcessor

class SyncModelClient:
    """同步模式的Model API Client"""
    
    def __init__(self, api_base: str, api_key: str, model: str):
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        # Check API base URL to determine provider
        self.is_openai = "openai" in api_base.lower()
        self.is_anthropic = "anthropic" in api_base.lower()
    
    def generate(self, prompt: str, query: str, 
                image_base64: str = None, temperature=0.1, 
                max_tokens=2048, enforce_json=False) -> Dict[str, Any]:
        """同步调用模型生成响应"""
        
        retries = 3
        backoff_factor = 2.0
        
        for attempt in range(retries):
            try:
                # Build API request
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                # Build messages
                content = []
                
                # Add text content
                content.append({"type": "text", "text": f"{prompt}\n\n{query}".strip()})
                
                # If image is provided, add image content
                if image_base64:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    })
                
                system_message = "You are a professional circuit diagram analysis assistant. Please answer questions according to the user-specified format"
                if enforce_json:
                    system_message = "You are a professional circuit diagram analysis assistant, always reply in pure JSON format. Do not use Markdown code blocks, do not add any prefix or suffix text, only return raw JSON. Your output should be directly parseable by JSON parsers without any preprocessing."
                
                messages = [
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ]
                
                # Build request payload
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                # Add response_format based on different API providers
                if enforce_json:
                    if self.is_openai:
                        payload["response_format"] = {"type": "json_object"}
                    elif self.is_anthropic:
                        # Anthropic's JSON response format may be different
                        # For Claude, enforce through system message
                        messages[0]["content"] += " Remember, you must only output pure JSON format, do not use code blocks, do not have any additional text."
                
                # Adapt to different API endpoints
                api_endpoint = f"{self.api_base}/chat/completions"
                if self.is_anthropic:
                    api_endpoint = f"{self.api_base}/messages"
                    # Anthropic API需要特殊处理
                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                
                # 发送同步请求
                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=180.0  # 180-second timeout
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    if response.status_code >= 500:
                        print(f"Server error {response.status_code}, retrying...")
                        response.raise_for_status()  # Will be caught by requests.RequestException
                    return {"error": f"API请求失败: {response.status_code}, {error_text}"}
                
                result = response.json()
                
                # 解析响应 (针对不同API提供商)
                if self.is_openai:
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return {"content": content, "usage": result.get("usage", {})}
                    else:
                        return {"error": "无效的OpenAI API响应"}
                elif self.is_anthropic:
                    if "content" in result and len(result["content"]) > 0:
                        # Anthropic API返回格式不同
                        text_contents = [block["text"] for block in result["content"] if block["type"] == "text"]
                        content = "".join(text_contents)
                        return {"content": content, "usage": result.get("usage", {})}
                    else:
                        return {"error": "无效的Anthropic API响应"}
                else:
                    # 通用解析逻辑
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return {"content": content, "usage": result.get("usage", {})}
                    else:
                        return {"error": "无效的API响应"}
                        
            except requests.RequestException as e:
                if attempt < retries - 1:
                    sleep_time = backoff_factor * (2 ** attempt)
                    print(f"Request failed with {type(e).__name__}: {e}. Retrying in {sleep_time}s... (Attempt {attempt+1}/{retries})")
                    time.sleep(sleep_time)
                else:
                    print(f"Request failed after {retries} attempts.")
                    return {"error": f"API request failed after {retries} retries: {traceback.format_exc()}"}
            except Exception as e:
                return {"error": f"生成时出错: {traceback.format_exc()}"}
        
        return {"error": f"API请求在 {retries} 次尝试后失败。"}
    
    def evaluate_consistency(self, prompt: str, query: str,
                           model1_json: str, model2_json: str, 
                           temperature=0.1) -> Dict[str, Any]:
        """评估两个分析结果的一致性（不包含图像）"""
        try:
            # 构建一致性评估提示词
            evaluation_text = f"{prompt}\n\n模型1的分析: {model1_json}\n\n模型2的分析: {model2_json}"
            
            # 调用生成函数进行评估，强制使用JSON格式
            return self.generate(
                evaluation_text,
                query,
                image_base64=None,
                temperature=temperature,
                enforce_json=True
            )
            
        except Exception as e:
            return {"error": f"评估时出错: {str(e)}"}
    
    def evaluate_consistency_with_image(self, prompt: str, query: str,
                                      model1_json: str, model2_json: str, 
                                      image_base64: str, temperature=0.1) -> Dict[str, Any]:
        """评估两个分析结果的一致性（包含原始图像）"""
        try:
            # 构建一致性评估提示词
            evaluation_text = f"{prompt}\n\n模型1的分析: {model1_json}\n\n模型2的分析: {model2_json}\n\n请结合原始电路图判断两个模型的分析是否一致。"
            
            # 调用生成函数进行评估，包含图像，强制使用JSON格式
            return self.generate(
                evaluation_text,
                query,
                image_base64=image_base64,
                temperature=temperature,
                enforce_json=True
            )
            
        except Exception as e:
            return {"error": f"带图像评估时出错: {str(e)}"}


def test_basic_generation():
    """测试基本的文本生成"""
    print("=== 测试基本文本生成 ===")
    
    client = SyncModelClient(
        api_base="http://0.0.0.0:8000/v1", 
        api_key="111", 
        model="checkpoint-135"
    )
    
    prompt = "请分析这个电路图的基本结构"
    query = "描述主要的电路组件"
    
    print(f"发送请求: {prompt}")
    print(f"查询: {query}")
    
    start_time = time.time()
    result = client.generate(prompt, query)
    end_time = time.time()
    
    print(f"耗时: {end_time - start_time:.2f}秒")
    print(f"结果: {result}")
    print()


def test_image_analysis():
    """测试图像分析"""
    print("=== 测试图像分析 ===")
    
    client = SyncModelClient(
        api_base="http://0.0.0.0:8000/v1", 
        api_key="111", 
        model="checkpoint-135"
    )
    
    # 测试图像路径
    image_path = "/data/home/libo/work/DataFactory/.cache/images/583_block_circuit_train_15k_0321_000858.jpg"
    
    try:
        # 编码图像
        print("正在编码图像...")
        image_base64 = ImageProcessor.encode_image(image_path)
        print(f"图像编码完成，长度: {len(image_base64)}")
        
        prompt = "What are the connections for the component located in <|box_start|>(150,50),(209,109)<|box_end|>?"
        query = ""
        
        print(f"发送请求: {prompt}")
        
        start_time = time.time()
        result = client.generate(prompt, query, image_base64=image_base64)
        end_time = time.time()
        
        print(f"耗时: {end_time - start_time:.2f}秒")
        print(f"结果: {result}")
        
    except Exception as e:
        print(f"图像分析测试失败: {e}")
    print()


def test_json_mode():
    """测试JSON模式"""
    print("=== 测试JSON模式 ===")
    
    client = SyncModelClient(
        api_base="http://0.0.0.0:8000/v1", 
        api_key="111", 
        model="checkpoint-135"
    )
    
    prompt = "请分析电路图并返回JSON格式的结果"
    query = "包含组件类型、连接关系和功能描述"
    
    print(f"发送请求: {prompt}")
    print(f"查询: {query}")
    
    start_time = time.time()
    result = client.generate(prompt, query, enforce_json=True)
    end_time = time.time()
    
    print(f"耗时: {end_time - start_time:.2f}秒")
    print(f"结果: {result}")
    
    # 尝试解析JSON
    if "content" in result:
        try:
            json_data = json.loads(result["content"])
            print(f"JSON解析成功: {json_data}")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
    print()


def test_consistency_evaluation():
    """测试一致性评估"""
    print("=== 测试一致性评估 ===")
    
    client = SyncModelClient(
        api_base="http://0.0.0.0:8000/v1", 
        api_key="111", 
        model="checkpoint-135"
    )
    
    prompt = "请评估两个模型分析结果的一致性"
    query = "返回一致性评分和详细说明"
    
    model1_json = '{"components": ["resistor", "capacitor"], "connections": ["A-B", "B-C"]}'
    model2_json = '{"components": ["resistor", "capacitor"], "connections": ["A-B", "C-B"]}'
    
    print(f"模型1结果: {model1_json}")
    print(f"模型2结果: {model2_json}")
    
    start_time = time.time()
    result = client.evaluate_consistency(prompt, query, model1_json, model2_json)
    end_time = time.time()
    
    print(f"耗时: {end_time - start_time:.2f}秒")
    print(f"一致性评估结果: {result}")
    print()


def main():
    """主测试函数"""
    print("开始同步模式的ModelClient测试")
    print("=" * 50)
    
    # 运行各种测试
    test_basic_generation()
    test_json_mode()
    test_consistency_evaluation()
    
    # 如果图像文件存在，则测试图像分析
    image_path = "/data/home/libo/work/DataFactory/.cache/images/583_block_circuit_train_15k_0321_000858.jpg"
    import os
    if os.path.exists(image_path):
        test_image_analysis()
    else:
        print(f"图像文件不存在: {image_path}")
        print("跳过图像分析测试")
    
    print("所有测试完成!")


if __name__ == "__main__":
    main() 