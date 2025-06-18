import aiohttp
from typing import Dict, Any

class ModelClient:
    """模型API客户端"""
    
    def __init__(self, api_base: str, api_key: str, model: str):
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        # 检查API基础URL以确定供应商
        self.is_openai = "openai" in api_base.lower()
        self.is_anthropic = "anthropic" in api_base.lower()
    
    async def generate(self, session, prompt: str, query: str, 
                      image_base64: str = None, temperature=0.1, 
                      max_tokens=2048, enforce_json=True) -> Dict[str, Any]:
        """调用模型生成回答"""
        try:
            # 构建API请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 构建消息
            content = []
            
            # 添加文本内容
            content.append({"type": "text", "text": f"{prompt}\n\n{query}"})
            
            # 如果提供了图像，添加图像内容
            if image_base64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                })
            
            system_message = "你是一个专业的电路图分析助手。请按照用户指定的格式回答问题"
            if enforce_json:
                system_message = "你是一个专业的电路图分析助手，总是以纯JSON格式回复。不要使用Markdown代码块，不要添加任何前缀或后缀文本，只返回原始JSON。你的输出应该可以直接被JSON解析器解析，不需要任何预处理。"
            
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
            
            # 构建请求体
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # 根据不同的API提供商添加response_format
            if enforce_json:
                if self.is_openai:
                    payload["response_format"] = {"type": "json_object"}
                elif self.is_anthropic:
                    # Anthropic的JSON响应格式可能有所不同
                    # 对于Claude，通过system message强制执行
                    messages[0]["content"] += " 切记，你必须只输出纯JSON格式，不要使用代码块，不要有任何额外的文本。"
            
            # 适配不同API端点
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
            
            # 发送请求
            async with session.post(
                api_endpoint,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {"error": f"API请求失败: {response.status}, {error_text}"}
                
                result = await response.json()
                
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
                
        except Exception as e:
            return {"error": f"生成时出错: {str(e)}"}
    
    async def evaluate_consistency(self, session, prompt: str, query: str,
                                 model1_json: str, model2_json: str, 
                                 temperature=0.1) -> Dict[str, Any]:
        """评估两个分析结果的一致性（不包含图像）"""
        try:
            # 构建一致性评估提示词
            evaluation_text = f"{prompt}\n\n模型1的分析: {model1_json}\n\n模型2的分析: {model2_json}"
            
            # 调用生成函数进行评估，强制使用JSON格式
            return await self.generate(
                session,
                evaluation_text,
                query,
                image_base64=None,
                temperature=temperature,
                enforce_json=True
            )
            
        except Exception as e:
            return {"error": f"评估时出错: {str(e)}"}
    
    async def evaluate_consistency_with_image(self, session, prompt: str, query: str,
                                           model1_json: str, model2_json: str, 
                                           image_base64: str, temperature=0.1) -> Dict[str, Any]:
        """评估两个分析结果的一致性（包含原始图像）
        
        Args:
            session: aiohttp会话
            prompt: 评估提示词
            query: 评估查询
            model1_json: 模型1的分析结果JSON
            model2_json: 模型2的分析结果JSON
            image_base64: 原始图像的base64编码
            temperature: 温度参数
            
        Returns:
            评估结果字典
        """
        try:
            # 构建一致性评估提示词
            evaluation_text = f"{prompt}\n\n模型1的分析: {model1_json}\n\n模型2的分析: {model2_json}\n\n请结合原始电路图判断两个模型的分析是否一致。"
            
            # 调用生成函数进行评估，包含图像，强制使用JSON格式
            return await self.generate(
                session,
                evaluation_text,
                query,
                image_base64=image_base64,
                temperature=temperature,
                enforce_json=True
            )
            
        except Exception as e:
            return {"error": f"带图像评估时出错: {str(e)}"} 