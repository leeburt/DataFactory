import os
import json
import asyncio
import aiohttp
import re
import sys 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Optional
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
import datetime

from node_connections.convert_node_connection import convert_image_data

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
        
    def _draw_box_to_image(self,full_image_path: str,node_box: List) -> str: 
        """获取节点名称"""
        # print("node_box:",node_box)
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
            
            # 绘制每个检测框

            if len(node_box) >= 4:  # 确保box有足够的坐标
                x1, y1, x2, y2 = node_box[0], node_box[1], node_box[2], node_box[3]
                
                # 绘制矩形框，使用红色，线宽为2
                draw.rectangle([x1, y1, x2, y2], outline='red', width=2)

            # 保存调试图片
            debug_dir = os.path.join(self.config.output_dir, "debug_images")
            os.makedirs(debug_dir, exist_ok=True)
            
            # 生成调试图片文件名
            image_name = os.path.basename(full_image_path)
            name_without_ext = os.path.splitext(image_name)[0]
            debug_image_path = os.path.join(debug_dir, f"{name_without_ext}_{str(node_box)}_with_boxes.jpg")
            
            # 保存调试图片
            image.save(debug_image_path, 'JPEG', quality=95)
            print(f"调试图片已保存: {debug_image_path}")
            
            # 将图片转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=95)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return image_base64
            
        except Exception as e:
            print(f"绘制检测框时出错: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")
            return ""
        
        
    async def _get_component_io(self, session, image_path: str, node_info: str, model_client: ModelClient,prompt: str) -> Dict:
        """获取特定组件的输入输出信息"""
        try:
            node_box = eval(node_info)
            # 获取完整图像路径
            full_image_path = os.path.join(self.config.image_root_dir, image_path)
            # image_base64 = self._draw_box_to_image(full_image_path,node_box)

            # 编码图像
            image_base64 = ImageProcessor.encode_image(full_image_path)

            # print("prompt:",prompt)
            run_prompt = prompt.format(x1=node_box[0],y1=node_box[1],x2=node_box[2],y2=node_box[3])
            # print(run_prompt)
            
            # 调用模型获取组件IO信息
            result = await model_client.generate(
                session,
                run_prompt,
                "",
                image_base64,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            if "error" in result:
                print(f"获取组件IO信息时出错 ({node_box}): {result['error']}")
                return {"description": {}, "warning": result['error']}
            
            # 检查响应内容是否为空
            if not result.get("content"):
                return {"description": {}, "warning": "模型返回的内容为空"}

            try:
                description = self._parse_json_from_description(result["content"])
                description["connections"] ={}
                description["connections"]["input"] = description["input"]
                description["connections"]["output"] = description["output"]
                description["connections"]["bidirectional"] = description["bidirectional"]
                description.pop("input")
                description.pop("output")
                description.pop("bidirectional")
                rtn_description = self.convert_boxes_in_data(description)
                return {"description": rtn_description, "warning": "JSON格式正确"}
            except Exception as e:
                return {"description": result["content"], "warning": "非JSON格式"}
            
        except Exception as e:
            print(f"获取组件IO信息时出错 ({node_box}): {str(traceback.format_exc())}")
            return {"description": {}, "warning": "获取组件IO信息时出错"}
    
        
    
    async def _process_image(self, session, image_path: str) -> None:
        """处理单张图像，获取组件列表和IO分析"""
        image_id = image_path.replace('\\', '/')
        # print(f"\n处理图像: {image_id}")
        
        try:
            #获取图片的wh 
            if image_id in self.all_results and self.all_results.get(image_id):
                print(f"  图像 {image_id} 已处理过")
                return

            # 第一步：使用模型获取组件列表
            components_origin = await self._get_component_list(session, image_path)
            # print(f"  模型找到 {len(components)} 个组件")
            
            import random 
            ## 从components的key中随机选择一部分
            components_keys = list(components_origin.keys())
            selected_keys = random.sample(components_keys, int(max(1, len(components_origin) * self.sample_rate))) #至少取一个值
            components = {k: components_origin[k] for k in selected_keys}
            print(f"  随机选择 {len(components)} 个组件 ,from {len(components_origin)} 个组件")

            # 初始化分析结果
            analysis_result = {
                "components": components_origin,
                "component_details": {}
            }
            
            # 第二步：并行分析所有组件的IO信息
            async def analyze_component_io(component):
                io_info = await self._get_component_io(
                    session, image_path, component, self.model_client, self.prompts_data["COMPONENT_IO_PROMPT_MODEL_QWEN"]
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
                    if (len(node_io_detail['connections']["input"]) == len(det_io_input)) and ((len(node_io_detail['connections']["output"])+len(node_io_detail['connections']["bidirectional"])) == len(det_io_output)):
                        io_num_match=True
                else:
                    io_num_match = False

                io_info["io_num_match"] = io_num_match
                io_info["det_io_info"] = components[component]
                
                # 增强组件数据，添加可视化IO端口信息

                analysis_result["component_details"][component] = io_info

            # 保存分析结果
            analysis_result = convert_image_data(analysis_result)
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
            print(f"JSON解析错误: {str(e)},{description}")
            return None
        except Exception as e:
            print(f"未知解析错误: {str(e)},{description}")
            return None
    

    def parse_box_format(self, box_str: str) -> tuple:
        """
        解析box格式字符串并返回(x1,y1,x2,y2)的元组
        
        支持的格式：
        1. "<|box_start|>(x1,y1),(x2,y2)<|box_end|>"
        2. "[x1, y1, x2, y2]"
        3. "(x1,y1,x2,y2)"
        
        Args:
            box_str: box格式的字符串
            
        Returns:
            tuple: (x1, y1, x2, y2) 格式的元组，如果解析失败返回None
        """
        if not box_str or not isinstance(box_str, str):
            return None
            
        try:
            # 格式1: <|box_start|>(x1,y1),(x2,y2)<|box_end|>
            pattern1 = r'<\|box_start\|>\((\d+),(\d+)\),\((\d+),(\d+)\)<\|box_end\|>'
            match1 = re.search(pattern1, box_str)
            if match1:
                x1, y1, x2, y2 = map(int, match1.groups())
                return str((x1, y1, x2, y2))
            
            # 格式2: [x1, y1, x2, y2]
            pattern2 = r'\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]'
            match2 = re.search(pattern2, box_str)
            if match2:
                x1, y1, x2, y2 = map(int, match2.groups())
                return str((x1, y1, x2, y2))
            
            # 格式3: (x1,y1,x2,y2)
            pattern3 = r'\((\d+),(\d+),(\d+),(\d+)\)'
            match3 = re.search(pattern3, box_str)
            if match3:
                x1, y1, x2, y2 = map(int, match3.groups())
                return str((x1, y1, x2, y2))
                
            # 如果是数组格式，尝试直接解析
            if box_str.strip().startswith('[') and box_str.strip().endswith(']'):
                coords = json.loads(box_str)
                if len(coords) == 4:
                    return str(tuple(coords))
                    
        except (ValueError, json.JSONDecodeError, AttributeError) as e:
            print(f"解析box格式时出错: {box_str}, 错误: {e}")
            
        return None

    def convert_boxes_in_data(self, data: dict) -> dict:
        """
        递归地在数据结构中查找并转换所有的box格式
        
        Args:
            data: 包含box信息的数据字典
            
        Returns:
            dict: 转换后的数据字典，box字段被替换为(x1,y1,x2,y2)格式
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key == "box" and isinstance(value, str):
                    # 转换box格式
                    parsed_box = self.parse_box_format(value)
                    result[key] = parsed_box if parsed_box else value
                else:
                    # 递归处理其他字段
                    result[key] = self.convert_boxes_in_data(value)
            return result
        elif isinstance(data, list):
            return [self.convert_boxes_in_data(item) for item in data]
        else:
            return data

    def convert_io_coordinates(self, io_data: dict) -> dict:
        """
        转换输入输出坐标信息为(x1,y1,x2,y2)格式的字符串
        
        Args:
            io_data: 包含input和output坐标列表的字典
            
        Returns:
            dict: 转换后的数据，坐标被转换为(x1,y1,x2,y2)格式
        """
        result = {}
        
        for io_type in ['input', 'output']:
            if io_type in io_data:
                converted_coords = []
                for coord_list in io_data[io_type]:
                    if len(coord_list) >= 4:
                        x1, y1, x2, y2 = coord_list[0], coord_list[1], coord_list[2], coord_list[3]
                        converted_coords.append(f"({x1}, {y1}, {x2}, {y2})")
                    else:
                        converted_coords.append(str(coord_list))
                result[io_type] = converted_coords
            else:
                result[io_type] = []
                
        return result

    async def run(self) -> Dict:
        """运行组件分析流程"""
        # 获取所有图像文件
        image_files = get_image_files(self.config.image_root_dir)
        
        if not image_files:
            raise Exception(f"在目录 {self.config.image_root_dir} 中未找到图像文件")
        
        print(f"发现 {len(image_files)} 个图像文件")
        
        # 创建信号量限制并发
        semaphore = asyncio.Semaphore(self.config.num_workers)
        # semaphore = asyncio.Semaphore(1)
        
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
    asyncio.run(analyzer.run())  
    