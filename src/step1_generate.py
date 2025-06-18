import os
import json
import asyncio
import aiohttp
import re
from typing import Dict, List, Any
from tqdm import tqdm
from src.config import Config
from src.image_processor import ImageProcessor
from src.model_client import ModelClient
from src.utils import get_image_files

class ComponentAnalyzer:
    """电路组件分析器，实现两步评估的第一步"""
    
    def __init__(self, config: Config):
        self.config = config
        self.prompts_data = self._load_prompts()
        
        # 初始化两个模型客户端
        self.model1_client = ModelClient(
            api_base=config.model1_api,
            api_key=config.model1_key,
            model=config.model1_model
        )
        
        self.model2_client = ModelClient(
            api_base=config.model2_api,
            api_key=config.model2_key,
            model=config.model2_model
        )
        
        # 结果存储
        self.model1_circuit_analyses = {}
        self.model2_circuit_analyses = {}
        
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
    
    def _load_prompts(self) -> Dict[str, str]:
        """加载提示词"""
        try:
            with open(self.config.prompts_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"加载提示词失败: {str(e)}")
    
    async def _get_component_list(self, session, image_path: str, model_client: ModelClient, model_name: str) -> List[str]:
        """获取电路图中的组件列表"""
        try:
            # 获取完整图像路径
            full_image_path = os.path.join(self.config.image_root_dir, image_path)
            
            # 检查文件是否存在
            if not os.path.exists(full_image_path):
                print(f"图像不存在: {full_image_path}")
                return []
                
            # 编码图像
            image_base64 = ImageProcessor.encode_image(full_image_path)
            
            # 获取提示词
            components_list_prompt = self.prompts_data["components_list_prompt"]
            
            # 调用模型获取组件列表
            result = await model_client.generate(
                session,
                components_list_prompt,
                "请列出电路图中的所有组件",
                image_base64,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            if "error" in result:
                print(f"获取组件列表时出错 ({model_name}): {result['error']}")
                return []
            
            # 检查响应内容是否为空
            if not result.get("content"):
                print(f"模型返回的内容为空 ({model_name})")
                return []
            
            # 尝试从响应中提取JSON数组
            try:
                # 显示响应内容的前100个字符，用于调试
                content_preview = result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
                print(f"模型响应预览 ({model_name}): {content_preview}")
                
                # 尝试直接解析整个响应
                try:
                    components = json.loads(result["content"])
                    if isinstance(components, list):
                        return components
                    elif isinstance(components, dict) and "components" in components:
                        # 有时模型可能会返回 {"components": [...]} 格式
                        return components["components"] if isinstance(components["components"], list) else []
                except json.JSONDecodeError:
                    pass
                
                # 如果上面失败，尝试从文本中提取JSON数组
                match = re.search(r'\[.*\]', result["content"], re.DOTALL)
                if match:
                    try:
                        json_str = match.group(0)
                        components = json.loads(json_str)
                        if isinstance(components, list):
                            return components
                    except json.JSONDecodeError:
                        pass
                
                # 如果依然无法解析，尝试使用更复杂的正则表达式
                # 寻找类似 ["元件1", "元件2", ...] 的模式
                match = re.search(r'\[\s*"[^"]*"(?:\s*,\s*"[^"]*")*\s*\]', result["content"], re.DOTALL)
                if match:
                    try:
                        json_str = match.group(0)
                        components = json.loads(json_str)
                        if isinstance(components, list):
                            return components
                    except json.JSONDecodeError:
                        pass
                
                # 如果都失败了，尝试创建一个简单的解析器来提取引号括起来的内容作为组件
                # 适用于类似 ["组件1", "组件2"] 的内容
                components = []
                matches = re.findall(r'"([^"]+)"', result["content"])
                if matches:
                    components = matches
                    return components
                
                print(f"无法解析组件列表 ({model_name}): {result['content']}")
                return []
                
            except Exception as e:
                print(f"解析组件列表时出错 ({model_name}): {str(e)}")
                return []
            
        except Exception as e:
            print(f"获取组件列表时出错 ({model_name}): {str(e)}")
            return []
    
    async def _get_component_io(self, session, image_path: str, component: str, model_client: ModelClient) -> Dict:
        """获取特定组件的输入输出信息"""
        try:
            # 获取完整图像路径
            full_image_path = os.path.join(self.config.image_root_dir, image_path)
            
            # 编码图像
            image_base64 = ImageProcessor.encode_image(full_image_path)
            
            # 获取提示词并替换组件名称
            component_io_prompt = self.prompts_data["component_io_prompt"].replace("{{component_name}}", component)
            
            # 调用模型获取组件IO信息
            result = await model_client.generate(
                session,
                component_io_prompt,
                f"请分析组件 {component} 的输入输出",
                image_base64,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            if "error" in result:
                print(f"获取组件IO信息时出错 ({component}): {result['error']}")
                return {"error": result["error"]}
            
            # 检查响应内容是否为空
            if not result.get("content"):
                return {"error": "模型返回的内容为空"}
            
            # 提取JSON对象
            # 首先尝试从JSON代码块中提取
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            json_matches = re.search(json_pattern, result["content"], re.DOTALL)
            
            if json_matches:
                try:
                    json_str = json_matches.group(1)
                    json_obj = json.loads(json_str)
                    return {"description": json.dumps(json_obj, ensure_ascii=False)}
                except json.JSONDecodeError:
                    pass
            
            # 如果上面失败，尝试从整个文本中提取JSON对象
            try:
                # 直接尝试解析整个响应
                json_obj = json.loads(result["content"])
                return {"description": json.dumps(json_obj, ensure_ascii=False)}
            except json.JSONDecodeError:
                # 尝试从文本中找到JSON对象
                obj_match = re.search(r'(\{.*\})', result["content"], re.DOTALL)
                if obj_match:
                    try:
                        json_str = obj_match.group(1)
                        json_obj = json.loads(json_str)
                        return {"description": json.dumps(json_obj, ensure_ascii=False)}
                    except json.JSONDecodeError:
                        pass
            
            # 如果以上都失败，返回原始内容
            print(f"警告: 无法将组件 {component} 的描述解析为JSON格式")
            return {"description": result["content"], "warning": "非JSON格式"}
            
        except Exception as e:
            print(f"获取组件IO信息时出错 ({component}): {str(e)}")
            return {"error": str(e)}
    
    async def _process_image(self, session, image_path: str) -> None:
        """处理单张图像，获取组件列表和IO分析"""
        image_id = image_path.replace('\\', '/')
        print(f"\n处理图像: {image_id}")
        
        # 第一步，获取两个模型的组件列表
        print(f"  获取组件列表...")
        
        model1_components = await self._get_component_list(session, image_path, self.model1_client, "模型1")
        print(f"  模型1找到 {len(model1_components)} 个组件")
        
        model2_components = model1_components
        
        # 初始化分析结果
        model1_analysis = {
            "components": model1_components,
            "component_details": {}
        }
        
        model2_analysis = {
            "components": model2_components,
            "component_details": {}
        }
        
        # 对模型1的组件进行IO分析
        if model1_components:
            print(f"  分析模型1识别的组件IO信息...")
            for component in tqdm(model1_components, desc=f"  模型1组件分析"):
                io_info = await self._get_component_io(session, image_path, component, self.model1_client)
                model1_analysis["component_details"][component] = io_info
        
        # 对模型2的组件进行IO分析
        if model2_components:
            print(f"  分析模型2识别的组件IO信息...")
            for component in tqdm(model2_components, desc=f"  模型2组件分析"):
                io_info = await self._get_component_io(session, image_path, component, self.model2_client)
                model2_analysis["component_details"][component] = io_info
        
        # 保存模型分析结果
        self.model1_circuit_analyses[image_id] = model1_analysis
        self.model2_circuit_analyses[image_id] = model2_analysis
        
        print(f"  完成图像 {image_id} 处理")
    
    async def run(self) -> Dict:
        """运行组件分析流程"""
        # 获取所有图像文件
        image_files = get_image_files(self.config.image_root_dir)
        
        if not image_files:
            raise Exception(f"在目录 {self.config.image_root_dir} 中未找到图像文件")
        
        print(f"发现 {len(image_files)} 个图像文件")
        
        # 创建信号量限制并发
        semaphore = asyncio.Semaphore(self.config.num_workers)
        
        async def process_with_semaphore(image_path):
            async with semaphore:
                await self._process_image(session, image_path)
        
        # 创建所有任务
        tasks = []
        
        # 异步处理所有图像
        async with aiohttp.ClientSession() as session:
            for image_path in image_files:
                tasks.append(process_with_semaphore(image_path))
            
            # 执行所有任务
            await asyncio.gather(*tasks)
        
        # 保存结果
        result_paths = self._save_results()
        
        return result_paths
    
    def _save_results(self) -> Dict[str, str]:
        """保存分析结果，仅保存最终分析结果，不保存components列表"""
        # 保存模型1分析结果
        model1_analysis_path = os.path.join(self.config.output_dir, "model1_analysis.json")
        with open(model1_analysis_path, 'w', encoding='utf-8') as f:
            json.dump(self.model1_circuit_analyses, f, ensure_ascii=False, indent=2)
        
        # 保存模型2分析结果
        model2_analysis_path = os.path.join(self.config.output_dir, "model2_analysis.json")
        with open(model2_analysis_path, 'w', encoding='utf-8') as f:
            json.dump(self.model2_circuit_analyses, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析结果保存完成:")
        print(f"- 模型1分析结果: {model1_analysis_path}")
        print(f"- 模型2分析结果: {model2_analysis_path}")
        
        return {
            "model1_analysis": model1_analysis_path,
            "model2_analysis": model2_analysis_path
        } 