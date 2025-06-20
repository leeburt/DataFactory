import os
import json
import asyncio
import aiohttp
import re
from typing import Dict, List, Any, Tuple, Union
from tqdm import tqdm
from src.config import Config
from src.model_client import ModelClient
from src.image_processor import ImageProcessor
import traceback

class ConsistencyEvaluator:
    """一致性评估器，实现两步评估的第二步"""
    
    def __init__(self, config: Config, result_paths: Dict[str, str]):
        self.config = config
        self.prompts_data = self.config.prompts
        self.result_paths = result_paths
        
        # 初始化评估模型客户端
        self.evaluator_client = ModelClient(
            api_base=config.evaluator_api,
            api_key=config.evaluator_key,
            model=config.evaluator_model
        )
        
        # 结果存储
        self.consistency_results = []
        self.component_consistency_results = {}  # 按组件的一致性结果

        self.step1_results = self._load_model_analyses()
        self.step2_results = {}
        
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        self.component_consistency_path = os.path.join(self.config.output_dir, "component_consistency_results.json")

        if os.path.exists(self.component_consistency_path):
            self.load_results()
    
    def _load_prompts(self) -> Dict[str, str]:
        """加载提示词"""
        try:
            with open(self.config.prompts_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"加载提示词失败: {str(traceback.format_exc())}")
    
    def _load_model_analyses(self) -> tuple:
        """加载两个模型的分析结果"""
        try:
            # 加载模型1分析结果
            with open(self.result_paths["model_analysis"], 'r', encoding='utf-8') as f:
                model_analyses = json.load(f)
            
            return model_analyses
        except Exception as e:
            raise Exception(f"加载模型分析结果失败: {str(e)}")
    
    def _check_json_format(self, model_analysis: Dict) -> Tuple[bool, Union[str, None]]:
        """检查组件描述是否为有效JSON格式"""
        if not model_analysis or "component_details" not in model_analysis:
            return False, "分析结果中缺少component_details部分"
        
        component_details = model_analysis.get("component_details", {})
        if not component_details:
            return False, "component_details为空"
        
        # 检查是否所有组件描述都是有效JSON
        non_json_components = []
        for component, details in component_details.items():
            if "warning" in details and details["warning"] == "非JSON格式":
                non_json_components.append(component)
            elif "error" in details:
                non_json_components.append(component)
            else:
                # 尝试验证description是否为有效的JSON字符串
                try:
                    desc = details.get("description", "")
                    json.loads(desc)
                except (json.JSONDecodeError, TypeError):
                    non_json_components.append(component)
        
        if non_json_components:
            components_str = ", ".join(non_json_components[:3])
            if len(non_json_components) > 3:
                components_str += f"等{len(non_json_components)}个组件"
            return False, f"以下组件描述不是有效的JSON格式: {components_str}"
        
        return True, None
    
    def _get_image_path(self, image_id: str) -> str:
        """获取图像的完整路径"""
        # 尝试直接在图像根目录查找
        direct_path = os.path.join(self.config.image_root_dir, image_id)
        if os.path.exists(direct_path):
            return direct_path
        
        # 尝试在子目录中查找
        for root, dirs, files in os.walk(self.config.image_root_dir):
            for file in files:
                if file == image_id or file == os.path.basename(image_id):
                    return os.path.join(root, file)
        
        # 如果找不到，返回原始ID（可能导致后续处理错误，但能提供明确的错误信息）
        print(f"警告: 找不到图像 {image_id} 的路径")
        return os.path.join(self.config.image_root_dir, image_id)
    
    async def _evaluate_consistency(self, session, image_id: str, model1_analysis: Dict, model2_analysis: Dict) -> Dict:
        """评估两个模型分析结果的一致性（包含原始图像）"""
        try:
            # 首先检查两个模型的输出是否为JSON格式
            model1_json_valid, model1_error = self._check_json_format(model1_analysis)
            model2_json_valid, model2_error = self._check_json_format(model2_analysis)
            
            # 如果任一模型输出不是有效的JSON格式，则跳过一致性评估
            if not model1_json_valid or not model2_json_valid:
                reason = "模型输出格式问题: "
                if not model1_json_valid:
                    reason += f"模型1: {model1_error}; "
                if not model2_json_valid:
                    reason += f"模型2: {model2_error}"
                
                print(f"跳过图像 {image_id} 的一致性评估: {reason}")
                return {
                    "image_id": image_id,
                    "is_consistent": False,
                    "reason": reason,
                    "json_valid": False
                }
            
            # 获取原始图像路径并编码为base64
            image_path = self._get_image_path(image_id)
            try:
                image_base64 = ImageProcessor.encode_image(image_path)
                print(f"已加载图像: {image_path}")
            except Exception as e:
                print(f"警告: 无法加载图像 {image_path}: {str(traceback.format_exc())}")
                print(f"将继续评估，但不包含图像")
                image_base64 = None
            
            # 获取评估提示词
            eval_prompt = self.prompts_data["consistency_eval_prompt"]
            
            # 替换占位符
            eval_prompt = eval_prompt.replace("{{model1_json}}", json.dumps(model1_analysis, ensure_ascii=False, indent=2))
            eval_prompt = eval_prompt.replace("{{model2_json}}", json.dumps(model2_analysis, ensure_ascii=False, indent=2))
            
            image_base64=None
            # 调用评估模型（使用包含图像的评估方法）
            if image_base64:
                print(f"使用原始图像进行评估: {image_id}")
                result = await self.evaluator_client.evaluate_consistency_with_image(
                    session,
                    eval_prompt,
                    "评估两个模型分析的一致性",
                    json.dumps(model1_analysis, ensure_ascii=False),
                    json.dumps(model2_analysis, ensure_ascii=False),
                    image_base64,
                    temperature=0.1
                )
            else:
                print(f"不使用图像进行评估: {image_id}")
                result = await self.evaluator_client.evaluate_consistency(
                    session,
                    eval_prompt,
                    "评估两个模型分析的一致性",
                    json.dumps(model1_analysis, ensure_ascii=False),
                    json.dumps(model2_analysis, ensure_ascii=False),
                    temperature=0.1
                )
            
            if "error" in result:
                print(f"评估一致性时出错 ({image_id}): {result['error']}")
                return {
                    "image_id": image_id,
                    "is_consistent": False,
                    "reason": f"评估出错: {result['error']}",
                    "json_valid": True,
                    "used_image": image_base64 is not None
                }
            
            # 检查响应内容是否为空
            if not result.get("content"):
                print(f"评估模型返回的内容为空 ({image_id})")
                return {
                    "image_id": image_id,
                    "is_consistent": "unknown",
                    "reason": "评估模型返回的内容为空",
                    "json_valid": True,
                    "used_image": image_base64 is not None
                }
            
            # 尝试从响应中提取JSON
            try:
                # 显示响应内容的前100个字符，用于调试
                content_preview = result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
                print(f"评估响应预览 ({image_id}): {content_preview}")
                
                # 直接解析整个响应
                try:
                    eval_result = json.loads(result["content"])
                    if "is_consistent" in eval_result and "reason" in eval_result:
                        return {
                            "image_id": image_id,
                            "is_consistent": eval_result["is_consistent"],
                            "reason": eval_result["reason"],
                            "json_valid": True,
                            "used_image": image_base64 is not None
                        }
                except json.JSONDecodeError:
                    pass
                
                # 如果上面失败，尝试从文本中提取JSON
                match = re.search(r'\{.*\}', result["content"], re.DOTALL)
                if match:
                    try:
                        json_str = match.group(0)
                        eval_result = json.loads(json_str)
                        if "is_consistent" in eval_result and "reason" in eval_result:
                            return {
                                "image_id": image_id,
                                "is_consistent": eval_result["is_consistent"],
                                "reason": eval_result["reason"],
                                "json_valid": True,
                                "used_image": image_base64 is not None
                            }
                    except json.JSONDecodeError:
                        pass
                
                # 如果都失败了，尝试简单解析响应中的一致性信息
                is_consistent = "yes" in result["content"].lower() or "true" in result["content"].lower()
                
                # 尝试提取理由
                # 首先尝试从JSON中提取reason字段
                reason = None
                
                # 尝试提取完整的reason字段
                reason_pattern = r'"reason"\s*:\s*"([^"]*(?:"[^"]*"[^"]*)*)"'
                reason_match = re.search(reason_pattern, result["content"], re.IGNORECASE | re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip()
                
                # 如果上面提取失败，尝试从整个内容中提取一致性解释
                if not reason or len(reason) < 20:  # 如果理由太短或未提取到
                    # 尝试提取以"Both models"开头的句子作为理由
                    both_models_pattern = r'Both models[^\.]*(?:\.[^\.]*){0,5}'
                    both_match = re.search(both_models_pattern, result["content"], re.IGNORECASE | re.DOTALL)
                    if both_match:
                        reason = both_match.group(0).strip()
                    
                    # 如果仍未提取到，尝试提取包含"consistent"的句子
                    if not reason or len(reason) < 20:
                        consistent_pattern = r'[^\.]*consistent[^\.]*(?:\.[^\.]*){0,3}'
                        consistent_match = re.search(consistent_pattern, result["content"], re.IGNORECASE | re.DOTALL)
                        if consistent_match:
                            reason = consistent_match.group(0).strip()
                
                # 如果所有尝试都失败，使用一个默认值
                if not reason or len(reason) < 20:
                    reason = "基于模型响应内容判断的一致性结果，未能提取详细理由"
                
                # 无法解析，返回简单判断结果
                return {
                    "image_id": image_id,
                    "is_consistent": is_consistent,
                    "reason": reason,
                    "json_valid": True,
                    "used_image": image_base64 is not None
                }
                
            except Exception as e:
                print(f"解析评估结果时出错 ({image_id}): {str(traceback.format_exc())}")
                return {
                    "image_id": image_id,
                    "is_consistent": "unknown",
                    "reason": f"解析评估结果出错: {str(traceback.format_exc())}",
                    "json_valid": True,
                    "used_image": image_base64 is not None
                }
            
        except Exception as e:
            print(f"评估一致性时出错 ({image_id}): {str(traceback.format_exc())}")
            return {
                "image_id": image_id,
                "is_consistent": False,
                "reason": f"评估出错: {str(e)}",
                "json_valid": False,
                "used_image": False
            }         
        
    
    async def _evaluate_component_pair(self, session, image_path: str, component: str, model1_details: Dict, model2_details: Dict) -> Dict:
        """评估一对组件的一致性"""
        try:
            # 加载两个模型的组件详情
            image_id = os.path.basename(image_path)
            
            # 检查是否有详情
            if not model1_details or not model2_details:
                return {
                    "component": f"{component}",
                    "is_consistent": False,
                    "consistency_score": 0,
                    "score_details": ["缺少组件详情"],
                    "better_model": "",
                    "reasoning": "至少一个模型未提供此组件的详细分析"
                }
            
            # 编码图像
            try:
                image_base64 = ImageProcessor.encode_image(image_path)
            except Exception as e:
                print(f"警告: 无法加载图像 {image_path}: {str(traceback.format_exc())}")
                image_base64 = None
            
            # 获取组件一致性评估提示词
            component_prompt = self.prompts_data["component_consistency_prompt"]
            
            # 替换占位符
            component_prompt = component_prompt.format(component1_name=component
                                                       , component2_name=component
                                                       , component1_details=json.dumps(model1_details, ensure_ascii=False)
                                                       , component2_details=json.dumps(model2_details, ensure_ascii=False))
            
            # print(component_prompt)
            
            # 调用评估模型
            result = await self.evaluator_client.generate(
                session,
                component_prompt,
                f"评估组件 {component} 连接关系的一致性",
                image_base64,
                temperature=0.1,
                enforce_json=True
            )
            
            if "error" in result:
                print(f"组件一致性评估时出错: {result['error']}")
                return {
                    "component": f"{component}",
                    "is_consistent": False,
                    "consistency_score": 0,
                    "score_details": ["评估出错"],
                    "better_model": "",
                    "reasoning": f"评估时出错: {result['error']}"
                }
            
            # 解析评估结果
            try:
                content = result["content"]
                
                # 首先，检查返回内容是否包含markdown代码块标记
                if "```" in content:
                    # 尝试提取markdown代码块中的JSON
                    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
                    match = re.search(code_block_pattern, content)
                    if match:
                        content = match.group(1)
                
                # 尝试直接解析为JSON
                try:
                    eval_result = json.loads(content)
                    return eval_result
                except json.JSONDecodeError:
                    pass
                
                # 尝试从文本中提取JSON
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    try:
                        json_str = match.group(0)
                        eval_result = json.loads(json_str)
                        return eval_result
                    except json.JSONDecodeError:
                        pass
                
                # 尝试修复常见的JSON格式问题后重新解析
                if content.strip().startswith("{") and "}" in content:
                    try:
                        # 提取从开始的'{'到最后的'}'之间的内容
                        start_idx = content.find("{")
                        end_idx = content.rfind("}") + 1
                        if start_idx != -1 and end_idx != -1:
                            json_str = content[start_idx:end_idx]
                            # 尝试修复常见的JSON格式问题
                            # 1. 替换单引号为双引号
                            json_str = json_str.replace("'", "\"")
                            # 2. 确保属性名使用双引号
                            json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                            
                            eval_result = json.loads(json_str)
                            return eval_result
                    except json.JSONDecodeError:
                        pass
                
                print(f"无法解析组件一致性评估结果，将返回默认值")
                print(f"原始响应: {content[:200]}...")
                
                # 如果无法解析，返回一个默认结果，尝试从内容中判断一致性
                is_consistent = "consistent" in content.lower() and not "not consistent" in content.lower()
                
                # 尝试提取一致性分数
                score_match = re.search(r'(?:consistency_score|score)[\s:"]*(\d+)', content)
                score = int(score_match.group(1)) if score_match else 50
                
                return {
                    "component": f"{component}",
                    "is_consistent": is_consistent,
                    "consistency_score": score,
                    "score_details": [],
                    "better_model": "",
                    "reasoning": f"解析失败，基于文本内容分析可能的一致性:{content}"
                }
                
            except Exception as e:
                print(f"解析组件一致性评估结果时出错: {str(traceback.format_exc())}")
                
                return {
                    "component": f"{component}",
                    "is_consistent": False,
                    "consistency_score": 0,
                    "score_details": ["解析错误"],
                    "better_model": "",
                    "reasoning": f"解析评估结果时出错: {str(traceback.format_exc())}"
                }
            
        except Exception as e:
            print(f"评估组件对时出错: {str(traceback.format_exc())}")
            return {
                "component": f"{component}",
                "is_consistent": False,
                "consistency_score": 0,
                "score_details": ["处理错误"],
                "better_model": "",
                "reasoning": f"处理组件对时出错: {str(traceback.format_exc())}"
            }
    
    async def _evaluate_component_consistency(self, session, image_id: str) -> Dict:
        """评估同一图像中每个组件的分析一致性"""
        model_analysis = self.step1_results[image_id]
        if image_id not in self.step2_results:
            return 
        try:
            # print(f"\n评估图像 {image_id} 的组件级一致性")

            
            # 获取图像完整路径
            image_path = self._get_image_path(image_id)
            component_pairs=list(model_analysis["component_details"].keys())
            
            # 逐对评估组件一致性
            print(f"  评估 {len(component_pairs)} 对组件的一致性...")
            component_results = []
            
            for component in tqdm(component_pairs, desc=f"  组件对评估"):
                model_name = list(model_analysis["component_details"][component].keys())
                model1_details = model_analysis["component_details"][component][model_name[0]]
                model2_details = model_analysis["component_details"][component][model_name[1]]
                result = await self._evaluate_component_pair(session, image_path, component, model1_details, model2_details)
                component_results.append(result)
                model_analysis["component_details"][component]['eval_result'] = result
                
            
            # 计算整体一致性
            consistent_count = sum(1 for r in component_results if r.get("consistency_score", 0)>= 85)
            overall_consistent = consistent_count / len(component_results) >= 0.75  # 如果75%以上的组件一致，则认为整体一致
            
            # 计算平均一致性分数
            total_score = sum(r.get("consistency_score", 0) for r in component_results)
            avg_score = total_score / len(component_results) if component_results else 0
            
            # 汇总结果
            result = {
                "image_id": image_id,
                "overall_consistent": overall_consistent,
                "overall_score": avg_score,
                "component_count": len(component_pairs),
                "consistent_count": consistent_count,
                "component_results": component_results,
                "reason": f"{consistent_count}/{len(component_pairs)} 组件分析一致"
            }   
            
        except Exception as e:
            print(f"评估组件级一致性时出错 ({image_id}): {str(traceback.format_exc())}")
            result =  {
                "image_id": image_id,
                "overall_consistent": False,
                "component_count": 0,
                "component_results": [],
                "reason": f"评估出错: {str(traceback.format_exc())}"
            }
        

        model_analysis['total_eval_result'] = result
        self.step2_results[image_id] = model_analysis
        return 
    
    async def run(self) -> None:
        """运行一致性评估流程"""        
        # 获取共同的图像ID列表
        common_image_ids = set(self.step1_results.keys())
        
        if not common_image_ids:
            raise Exception("没有找到两个模型共同分析的图像")
        
        print(f"发现 {len(common_image_ids)} 个共同分析的图像")
        
        # 创建信号量限制并发
        semaphore = asyncio.Semaphore(self.config.num_workers)
        
        # 判断是否进行组件级评估
        use_component_level = True  # 设置为True启用组件级评估
        
        if use_component_level:
            # 组件级评估
            print("\n使用组件级别一致性评估...")

            completed_count = 0  # 新增：已完成数量
            save_interval = 10   # 新增：每多少次保存一次

            async def evaluate_components_with_semaphore(image_id):
                nonlocal completed_count
                async with semaphore:
                    result = await self._evaluate_component_consistency(
                        session, 
                        image_id,
                    )
                    completed_count += 1
                    print(f"  完成图像 {image_id} 的组件级一致性评估")
                    # 每save_interval次保存一次
                    if completed_count % save_interval == 0:
                        self._save_results()
            
            # 创建所有任务
            tasks = []
            
            # 异步处理所有图像
            async with aiohttp.ClientSession() as session:
                for image_id in common_image_ids:
                    tasks.append(evaluate_components_with_semaphore(image_id))
                
                # 执行所有任务
                await asyncio.gather(*tasks)
            
        else:
            pass 
 
        # 保存结果
        self._save_results()
    
    def _save_results(self) -> None:
        """保存评估结果"""
        # 判断使用哪种结果
        if self.step2_results:
            # 保存组件级一致性评估结果
            with open(self.component_consistency_path, 'w', encoding='utf-8') as f:
                json.dump(self.step2_results, f, ensure_ascii=False, indent=2)
            print(f"组件级一致性评估结果已保存到 {self.component_consistency_path}")

    def load_results(self) -> None:
        """加载评估结果"""
        with open(self.component_consistency_path, 'r', encoding='utf-8') as f:
            self.step2_results = json.load(f)
        