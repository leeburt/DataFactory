import os
import json
import asyncio
import aiohttp
import re
import sys 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any
from tqdm import tqdm
from src.config import Config
from src.image_processor import ImageProcessor
from src.model_client import ModelClient
from src.utils import get_image_files
import traceback
from node_connections.get_node_io import NodeIO

import base64
from PIL import Image, ImageDraw, ImageFont
import io

class ComponentAnalyzer:
    """电路组件分析器，实现两步评估的第一步"""
    
    def __init__(self, config: Config):
        self.config = config
        self.prompts_data = self.config.prompts
        
        # 初始化模型客户端
        self.model_client = ModelClient(
            api_base=config.model2_api,
            api_key=config.model2_key,
            model=config.model2_model
        )
        
        # 结果存储
        self.all_results = {}
        
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        self.model_analysis_path = os.path.join(self.config.output_dir, "model_analysis.json")

        if os.path.exists(self.model_analysis_path):
            self.load_results()

        self.NodeIO = NodeIO()

        self.sample_rate = self.config.node_sample_rate

    
    async def _get_component_list(self, session, image_path: str) -> List:
        """获取电路图中的组件列表"""
        try:
            # 获取完整图像路径
            full_image_path = os.path.join(self.config.image_root_dir, image_path)
            results_io,results_node,node_io_map = self.NodeIO(full_image_path)
            return node_io_map
        except Exception as e:
            print(f"获取组件列表时出错: {str(e)}")
            return {}

    async def _get_component_name(self, session, image_path: str, node_box: List) -> str:
        """获取单个组件的名字"""
        try:
            # 获取完整图像路径
            full_image_path = os.path.join(self.config.image_root_dir, image_path)
            
            # 绘制检测框并获取图像
            image_base64 = self._draw_box_to_image(full_image_path, node_box)
            
            if not image_base64:
                return "未知组件"
            
            # 使用获取单个组件名字的prompt
            result = await self.model_client.generate(
                session,
                self.prompts_data["COMPONENT_NAME_PROMPT"],
                "请识别红色框中组件的名字",
                image_base64,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            if "error" in result:
                print(f"获取组件名字时出错 ({node_box}): {result['error']}")
                return "未知组件"
            
            # 检查响应内容是否为空
            if not result.get("content"):
                print(f"模型返回的内容为空 ({node_box})")
                return "未知组件"
            
            # 解析组件名字
            component_name = result["content"].strip()
            
            # 如果返回的是JSON格式，尝试解析
            if component_name.startswith("{") and component_name.endswith("}"):
                try:
                    parsed = json.loads(component_name)
                    if "component_name" in parsed:
                        component_name = parsed["component_name"]
                    elif "name" in parsed:
                        component_name = parsed["name"]
                except:
                    pass
            
            # 清理组件名字，移除多余的格式
            component_name = component_name.replace('"', '').replace("'", "").strip()
            
            # 如果名字为空或太短，返回默认名字
            if not component_name or len(component_name) < 1:
                component_name = "未知组件"
            
            return component_name
                
        except Exception as e:
            print(f"获取组件名字时出错 ({node_box}): {str(e)}")
            return "未知组件"

    async def _get_all_component_names(self, session, image_path: str, components: Dict) -> Dict:
        """获取所有组件的名字（基于目标检测结果逐个询问）"""
        try:
            print(f"  开始获取 {len(components)} 个组件的名字...")
            component_names = {}
            
            # 并行获取所有组件的名字
            async def get_single_component_name(component_key):
                try:
                    node_box = eval(component_key)
                    component_name = await self._get_component_name(session, image_path, node_box)
                    return component_key, component_name
                except Exception as e:
                    print(f"获取组件名字时出错 ({component_key}): {str(e)}")
                    return component_key, "未知组件"
            
            # 创建并发任务
            tasks = [get_single_component_name(key) for key in components.keys()]
            results = await asyncio.gather(*tasks)
            
            # 收集结果
            for component_key, component_name in results:
                component_names[component_key] = component_name
            
            print(f"  成功获取 {len(component_names)} 个组件名字")
            return component_names
                
        except Exception as e:
            print(f"获取所有组件名字时出错: {str(e)}")
            return {}
        
    def _draw_box_to_image(self,full_image_path: str,node_box: List) -> str: 
        """绘制检测框到图像并返回base64编码"""
        try:
            # 检查文件是否存在
            if not os.path.exists(full_image_path):
                print(f"图像不存在: {full_image_path}")
                return ""
            
            # 打开图像
            image = Image.open(full_image_path)
            
            # 如果是RGBA模式，转换为RGB
            if image.mode == 'RGBA':
                image = image.convert('RGB')
            
            # 创建绘图对象
            draw = ImageDraw.Draw(image)
            
            # 绘制检测框
            if len(node_box) >= 4:  # 确保box有足够的坐标
                x1, y1, x2, y2 = node_box[0], node_box[1], node_box[2], node_box[3]
                # 确保坐标正确排序
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                
                # 计算中心点和半径
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                # 使用宽度和高度的较小值来计算半径，确保圆圈在框内
                width = x2 - x1
                height = y2 - y1
                radius = max(width, height) // 2  # 使用较小维度的1/4作为半径
                draw.ellipse(
                        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                        outline='blue', 
                        width=4
                    )
            else:
                print(f"警告：检测框坐标不足4个点: {node_box}")

            # 保存调试图片（可选）
            debug_dir = os.path.join(self.config.output_dir, "debug_images")
            os.makedirs(debug_dir, exist_ok=True)
            
            # 生成调试图片文件名
            image_name = os.path.basename(full_image_path)
            name_without_ext = os.path.splitext(image_name)[0]
            debug_image_path = os.path.join(debug_dir, f"{name_without_ext}_{str(node_box)}_with_boxes.jpg")
            
            # 保存调试图片
            image.save(debug_image_path, 'JPEG', quality=95)
            
            # 将图片转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=95)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return image_base64
            
        except Exception as e:
            print(f"绘制检测框时出错: {str(e)}")
            return ""
        
        
    async def _get_component_io(self, session, image_path: str, node_info: str, model_client: ModelClient, prompt: str, component_names: Dict = None) -> Dict:
        """获取特定组件的输入输出信息"""
        try:
            node_box = eval(node_info)
            # 获取完整图像路径
            full_image_path = os.path.join(self.config.image_root_dir, image_path)
            image_base64 = self._draw_box_to_image(full_image_path,node_box)

            # 创建包含所有组件信息的prompt
            enhanced_prompt = prompt
            if component_names:
                enhanced_prompt = prompt.format(query_component_box={node_info:component_names[node_info]},all_component_box=component_names)

            print(enhanced_prompt)
            
            # 调用模型获取组件IO信息
            result = await model_client.generate(
                session,
                enhanced_prompt,
                "",
                image_base64,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            if "error" in result:
                print(f"获取组件IO信息时出错 ({node_box}): {result['error']}")
                return {"error": result["error"]}
            
            # 检查响应内容是否为空
            if not result.get("content"):
                return {"error": "模型返回的内容为空"}

            try:
                description = self._parse_json_from_description(result["content"])
                return {"description": description, "warning": "JSON格式正确"}
            except Exception as e:
                return {"description": result["content"], "warning": "非JSON格式"}
            
        except Exception as e:
            print(f"获取组件IO信息时出错 ({node_box}): {str(traceback.format_exc())}")
            return {"error": str(e)}
    
        
    
    async def _process_image(self, session, image_path: str) -> None:
        """处理单张图像，获取组件列表和IO分析"""
        image_id = image_path.replace('\\', '/')
        
        try:
            if image_id in self.all_results and self.all_results.get(image_id):
                print(f"  图像 {image_id} 已处理过")
                return

            # 第一步：使用目标检测获取组件列表
            components_origin = await self._get_component_list(session, image_path)
            
            # 随机选择部分组件进行分析
            import random 
            components_keys = list(components_origin.keys())
            selected_keys = random.sample(components_keys, int(max(1, len(components_origin) * self.sample_rate)))
            components = {k: components_origin[k] for k in selected_keys}
            print(f"  随机选择 {len(components)} 个组件 ,from {len(components_origin)} 个组件")

            # 第二步：基于目标检测结果，逐个获取组件名字
            component_names = await self._get_all_component_names(session, image_path, components)
            
            # 初始化分析结果
            analysis_result = {
                "components": components_origin,
                "component_names": component_names,  # 保存组件名字映射
                "component_details": {}
            }
            
            # 第三步：并行分析所有组件的IO信息（使用组件名字信息）
            async def analyze_component_io(component):
                io_info = await self._get_component_io(
                    session, image_path, component, self.model_client, 
                    self.prompts_data["COMPONENT_IO_PROMPT_MODE_WITH_BOX"], 
                    component_names  # 传递组件名字信息
                )
                return component, io_info

            tasks = [analyze_component_io(k) for k in components.keys()]
            results = await asyncio.gather(*tasks)

            for component, io_info in results:
                analysis_result["component_details"][component] = io_info
                det_io_input=components[component]["input"]
                det_io_output=components[component]["output"]
                node_io_detail=None
                if io_info["warning"] == "JSON格式正确":
                    node_io_detail = io_info["description"]
                    io_num_match = False
                    if (len(node_io_detail["connections"]["input"]) == len(det_io_input)) and ((len(node_io_detail["connections"]["output"])+len(node_io_detail["connections"]["bidirectional"])) == len(det_io_output)):
                        io_num_match=True

                io_info["io_num_match"] = io_num_match
                io_info["det_io_info"] = components[component]

            # 保存分析结果
            self.all_results[image_id] = analysis_result
            
            print(f"  完成图像 {image_id} 处理")
        except Exception as e:
            print(f"  处理图像 {image_id} 时出错: {str(traceback.format_exc())}")

    
    def _parse_json_from_description(self, description: str) -> Dict:
        """从描述字符串中解析JSON"""
        try:
            # 如果description包含```json代码块，提取其中的JSON
            if "```json" in description:
                # 提取```json和```之间的内容
                json_start = description.find("```json") + 7
                json_end = description.find("```", json_start)
                if json_end != -1:
                    json_str = description[json_start:json_end].strip()
                else:
                    json_str = description[json_start:].strip()
            else:
                # 直接尝试解析整个字符串
                json_str = description.strip()
            
            # 尝试解析JSON
            parsed_json = json.loads(json_str)
            return parsed_json
            
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            print(f"JSON解析错误: {str(e)}")
            return None
        except Exception as e:
            print(f"未知解析错误: {str(e)}")
            return None
    

        
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
    asyncio.run(analyzer.run())  
    