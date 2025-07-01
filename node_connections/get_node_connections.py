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
import traceback

class ComponentAnalyzer:
    """电路组件分析器，实现两步评估的第一步"""
    
    def __init__(self, config: Config):
        self.config = config
        self.prompts_data = self.config.prompts
        
        # 初始化模型客户端
        self.model_client = ModelClient(
            api_base=config.model1_api,
            api_key=config.model1_key,
            model=config.model1_model
        )
        
        # 结果存储
        self.all_results = {}
        
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        self.model_analysis_path = os.path.join(self.config.output_dir, "model_analysis.json")

        if os.path.exists(self.model_analysis_path):
            self.load_results()

    
    async def _get_component_list(self, session, image_path: str, model_client: ModelClient, model_name: str,prompt: str) -> List[str]:
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
        
            
            # 调用模型获取组件列表
            result = await model_client.generate(
                session,
                prompt,
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
                # print(f"模型响应预览 ({model_name}): {content_preview}")
                
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
    
    async def _get_component_io(self, session, image_path: str, component: str, model_client: ModelClient,prompt: str) -> Dict:
        """获取特定组件的输入输出信息"""
        try:
            # 获取完整图像路径
            full_image_path = os.path.join(self.config.image_root_dir, image_path)
            
            # 编码图像
            image_base64 = ImageProcessor.encode_image(full_image_path)
            
            # 获取提示词并替换组件名称
            component_io_prompt = prompt.format(component_name=component)
            
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
            
            return {"description": result["content"], "warning": "非JSON格式"}
            
        except Exception as e:
            print(f"获取组件IO信息时出错 ({component}): {str(traceback.format_exc())}")
            return {"error": str(e)}
        
    
    async def _process_image(self, session, image_path: str) -> None:
        """处理单张图像，获取组件列表和IO分析"""
        image_id = image_path.replace('\\', '/')
        # print(f"\n处理图像: {image_id}")
        
        try:
            if image_id in self.all_results and self.all_results.get(image_id):
                print(f"  图像 {image_id} 已处理过")
                return

            # 第一步：使用模型获取组件列表
            components = await self._get_component_list(
                session, image_path, self.model_client, self.model_client.model, self.prompts_data["components_list_prompt_model1"]
            )
            # print(f"  模型找到 {len(components)} 个组件")

            # 初始化分析结果
            analysis_result = {
                "components": components,
                "component_details": {}
            }
            
            # 第二步：并行分析所有组件的IO信息
            async def analyze_component_io(component):
                io_info = await self._get_component_io(
                    session, image_path, component, self.model_client, self.prompts_data["component_io_prompt_model1"]
                )
                return component, io_info

            tasks = [analyze_component_io(component) for component in components]
            results = await asyncio.gather(*tasks)

            for component, io_info in results:
                analysis_result["component_details"][component] = io_info
            
            # 保存分析结果
            self.all_results[image_id] = analysis_result
            
            print(f"  完成图像 {image_id} 处理")
        except Exception as e:
            print(f"  处理图像 {image_id} 时出错: {str(traceback.format_exc())}")

    def convert_model_results(self) -> None:
        """转换模型结果 (此方法在新流程中不再需要)"""
        pass
        
    
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
        
        # 异步处理所有图像
        async with aiohttp.ClientSession() as session:
            # 创建所有任务
            tasks = [process_with_semaphore(image_path) for image_path in image_files]
            
            # 使用asyncio.as_completed来正确显示进度
            completed = 0
            with tqdm(total=len(tasks), desc="处理图像") as pbar:
                for coro in asyncio.as_completed(tasks):
                    await coro
                    completed += 1
                    pbar.update(1)
                    
                    # 每处理10张图片就保存一次
                    if completed % 10 == 0:
                        self._save_results()
        
        # 保存结果
        result_paths = self._save_results()
        
        return result_paths
    
    def _save_results(self) -> Dict[str, str]:
        """保存分析结果，仅保存最终分析结果，不保存components列表"""
        # 保存模型分析结果


        with open(self.model_analysis_path, 'w', encoding='utf-8') as f:
            json.dump(self.all_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析结果保存完成:")
        print(f"- 模型分析结果: {self.model_analysis_path}")
        return {
            "model_analysis": self.model_analysis_path,
        } 
    
    def load_results(self) -> None:
        """加载评估结果"""
        print(f"加载模型分析结果: {self.model_analysis_path}")
        try:
            with open(self.model_analysis_path, 'r', encoding='utf-8') as f:
                self.all_results = json.load(f)
        except json.JSONDecodeError:
            print(f"警告: '{self.model_analysis_path}' 为空或包含无效的JSON数据。将初始化为空结果。")
            self.all_results = {}


if __name__ == "__main__":
    config = Config()
    analyzer = ComponentAnalyzer(config)
    analyzer.run()  
    