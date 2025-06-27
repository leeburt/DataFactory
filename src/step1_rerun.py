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
        self.all_results = {}
        
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        self.model_analysis_path = os.path.join(self.config.output_dir, "model_analysis.json")

        if os.path.exists(self.model_analysis_path):
            self.load_results()

        self.old_results_path = self.config.old_results_path
        self.old_results = {}
        if os.path.exists(self.old_results_path):
            with open(self.old_results_path, 'r', encoding='utf-8') as f:
                self.old_results = json.load(f)
        else:
            print(f"[error] {self.old_results_path} 不存在")
        

    
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
        
        # 第一步，获取两个模型的组件列表
        # print(f"  获取组件列表...")
        try:
            if image_id in self.all_results:
                print(f"  图像 {image_id} 已处理过")
                return
            if self.config.rerun and image_id in self.old_results:
                model1_components = self.old_results[image_id]["components"]
            else:
                print(f"[error] {image_id} 未处理过")
                return 

            model2_components = model1_components
            
            # 初始化分析结果
            model1_analysis = {
                "components": model1_components,
                "component_details": {}
            }
            
            # 并行分析所有组件的IO信息
            async def analyze_component_io(component):
                # 并行获取模型1和模型2的IO信息
                io1_task = self._get_component_io(session, image_path, component, self.model1_client, self.prompts_data["component_io_prompt_model1"])
                io1= await asyncio.gather(io1_task)
                return component, io1

            tasks = [analyze_component_io(component) for component in model1_components]
            results = await asyncio.gather(*tasks)

            for component, io1 in results:
                model1_analysis["component_details"][component] = io1
            
            # 保存模型分析结果
            self.model1_circuit_analyses[image_id] = model1_analysis
            self.convert_model_results()
            
            print(f"  完成图像 {image_id} 处理")
        except Exception as e:
            print(f"  处理图像 {image_id} 时出错: {str(traceback.format_exc())}")

    def convert_model_results(self) -> None:
        """转换模型结果"""
        for image_id, analysis in self.model1_circuit_analyses.items():
            self.all_results[image_id] = {}
            self.all_results[image_id]["components"] = analysis["components"]
            self.all_results[image_id]["component_details"] = {}
            for component in analysis["components"]:
                if self.model1_client.model == self.model2_client.model:
                    model1_name = self.model1_client.model
                    model2_name = self.model2_client.model+"_2"
                else:
                    model1_name = self.model1_client.model
                    model2_name = self.model2_client.model
                self.all_results[image_id]["component_details"][component] = {
                    model1_name: analysis["component_details"][component],
                    model2_name: self.old_results[image_id]["component_details"][component][model2_name]
                }
        return
        
    
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
        # 保存模型1分析结果


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