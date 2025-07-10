#!/usr/bin/env python3
"""
测试新的组件分析器 V2 版本
包含组件名字获取功能的测试
"""

import os
import asyncio
import json
from src.config import Config
from node_connections.get_node_info_from_det_v2 import ComponentAnalyzer
from config.prompts_node import (COMPONENT_IO_PROMPT_MODEL, COMPONENT_NAME_PROMPT)

def create_test_config():
    """创建测试配置"""
    config = Config(
        image_root_dir="/data/home/libo/work/DataFactory/.cache/images",  # 请根据实际路径修改
        output_dir="/data/home/libo/work/DataFactory/.cache/test_output",
        model1_api="http://0.0.0.0:8000/v1",  # 请根据实际API地址修改
        model1_key="111",
        model1_model="checkpoint-135",  # 请根据实际模型名称修改
        num_workers=2,
        temperature=0.1,
        max_tokens=2048,
        node_sample_rate=0.5
    )
    
    # 添加 prompts
    config.prompts = {
        "COMPONENT_IO_PROMPT_MODEL": COMPONENT_IO_PROMPT_MODEL,
        "COMPONENT_NAME_PROMPT": COMPONENT_NAME_PROMPT,
    }
    
    return config

async def test_component_analyzer():
    """测试组件分析器"""
    print("开始测试组件分析器 V2...")
    
    # 创建配置
    config = create_test_config()
    
    # 确保输出目录存在
    os.makedirs(config.output_dir, exist_ok=True)
    
    # 创建分析器
    analyzer = ComponentAnalyzer(config)
    
    try:
        # 运行分析
        result_paths = await analyzer.run()
        
        print("分析完成！")
        print(f"结果保存在: {result_paths}")
        
        # 读取并显示部分结果
        if os.path.exists(result_paths["model_analysis"]):
            with open(result_paths["model_analysis"], 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            print(f"\n处理了 {len(results)} 个图像")
            
            # 显示第一个图像的结果示例
            if results:
                first_image = list(results.keys())[0]
                first_result = results[first_image]
                
                print(f"\n示例结果 (图像: {first_image}):")
                print(f"- 检测到的组件数量: {len(first_result.get('components', {}))}")
                print(f"- 获取到的组件名字数量: {len(first_result.get('component_names', {}))}")
                print(f"- 分析的组件详情数量: {len(first_result.get('component_details', {}))}")
                
                # 显示组件名字示例
                if 'component_names' in first_result:
                    print(f"\n组件名字示例:")
                    for i, (box, name) in enumerate(first_result['component_names'].items()):
                        if i >= 3:  # 只显示前3个
                            break
                        print(f"  {box}: {name}")
                
                # 显示组件详情示例
                if 'component_details' in first_result:
                    print(f"\n组件详情示例:")
                    for i, (component, details) in enumerate(first_result['component_details'].items()):
                        if i >= 2:  # 只显示前2个
                            break
                        print(f"  组件 {component}:")
                        print(f"    - 警告: {details.get('warning', 'N/A')}")
                        print(f"    - IO数量匹配: {details.get('io_num_match', 'N/A')}")
                        if details.get('warning') == 'JSON格式正确' and 'description' in details:
                            desc = details['description']
                            if isinstance(desc, dict):
                                print(f"    - 组件名: {desc.get('component_name', 'N/A')}")
                                connections = desc.get('connections', {})
                                print(f"    - 输入连接数: {len(connections.get('input', []))}")
                                print(f"    - 输出连接数: {len(connections.get('output', []))}")
                                print(f"    - 双向连接数: {len(connections.get('bidirectional', []))}")
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_component_analyzer()) 