#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试box格式解析功能的脚本
"""

import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from node_connections.get_node_info_from_det_qwen import ComponentAnalyzer
from src.config import Config

def test_box_parsing():
    """测试各种box格式的解析"""
    
    # 创建ComponentAnalyzer实例
    config = Config()
    analyzer = ComponentAnalyzer(config)
    
    # 测试不同的box格式
    test_cases = [
        "<|box_start|>(599,160),(737,253)<|box_end|>",
        "<|box_start|>(343,10),(481,102)<|box_end|>",
        "[599, 160, 737, 253]",
        "[343, 10, 481, 102]",
        "(599,160,737,253)",
        "(343,10,481,102)",
        "invalid_format",
        "",
        None
    ]
    
    print("=== Box格式解析测试 ===\n")
    
    for i, box_str in enumerate(test_cases, 1):
        print(f"测试 {i}: {box_str}")
        result = analyzer.parse_box_format(box_str)
        print(f"结果: {result}")
        print("-" * 50)

def test_convert_json_data():
    """测试转换JSON数据中的box格式"""
    
    config = Config()
    analyzer = ComponentAnalyzer(config)
    
    # 模拟JSON数据
    test_data = {
        "component_name": "SEQUENCER",
        "box": "<|box_start|>(599,160),(737,253)<|box_end|>",
        "connections": {
            "input": [
                {
                    "name": "CLOCK EXTRACTOR",
                    "box": "<|box_start|>(343,10),(481,102)<|box_end|>"
                }
            ],
            "output": [
                {
                    "name": "MEMORY ARRAY", 
                    "box": "<|box_start|>(797,159),(935,252)<|box_end|>"
                }
            ],
            "bidirectional": []
        }
    }
    
    print("\n=== JSON数据转换测试 ===\n")
    print("原始数据:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    
    # 转换数据
    converted_data = analyzer.convert_boxes_in_data(test_data)
    
    print("\n转换后数据:")
    print(json.dumps(converted_data, indent=2, ensure_ascii=False))

def test_visual_io_enhancement():
    """测试可视化IO端口信息增强功能"""
    
    config = Config()
    analyzer = ComponentAnalyzer(config)
    
    # 模拟组件数据
    component_data = {
        "description": {
            "component_name": "SEQUENCER",
            "box": "(599, 160, 737, 253)",
            "connections": {
                "input": [
                    {
                        "name": "CLOCK EXTRACTOR",
                        "box": "(343, 10, 481, 102)"
                    }
                ],
                "output": [
                    {
                        "name": "MEMORY ARRAY",
                        "box": "(797, 159, 935, 252)"
                    }
                ],
                "bidirectional": []
            }
        },
        "warning": "JSON格式正确",
        "io_num_match": False,
        "det_io_info": {
            "input": [
                [653, 138, 683, 169]
            ],
            "output": [
                [658, 240, 677, 259],
                [727, 196, 742, 211]
            ]
        }
    }
    
    print("\n=== 可视化IO端口信息增强测试 ===\n")
    print("原始组件数据:")
    print(json.dumps(component_data, indent=2, ensure_ascii=False))
    
    # 增强组件数据
    enhanced_data = analyzer.enhance_component_with_visual_io(component_data)
    
    print("\n增强后的组件数据:")
    print(json.dumps(enhanced_data, indent=2, ensure_ascii=False))

def convert_model_analysis_file():
    """转换模型分析文件中的所有box格式"""
    
    config = Config()
    analyzer = ComponentAnalyzer(config)
    
    # 读取原始文件
    input_file = "results/qwen_7b_v2/model_analysis.json"
    output_file = "results/qwen_7b_v2/model_analysis_converted.json"
    
    try:
        print(f"\n=== 转换文件 {input_file} ===\n")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"原始文件包含 {len(data)} 个图像")
        
        # 转换所有数据
        converted_data = analyzer.convert_boxes_in_data(data)
        
        # 保存转换后的文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, ensure_ascii=False, indent=2)
        
        print(f"转换完成！保存到: {output_file}")
        
        # 显示一个示例转换结果
        if converted_data:
            first_key = list(converted_data.keys())[0]
            if 'component_details' in converted_data[first_key]:
                details = converted_data[first_key]['component_details']
                if details:
                    first_component = list(details.keys())[0]
                    component_data = details[first_component]
                    
                    print(f"\n示例转换结果 (组件: {first_component}):")
                    if 'description' in component_data:
                        desc = component_data['description']
                        if 'box' in desc:
                            print(f"主要box: {desc['box']}")
                        if 'connections' in desc:
                            for conn_type in ['input', 'output', 'bidirectional']:
                                if conn_type in desc['connections']:
                                    for conn in desc['connections'][conn_type]:
                                        if 'box' in conn:
                                            print(f"{conn_type} box: {conn['box']}")
        
    except FileNotFoundError:
        print(f"文件 {input_file} 不存在")
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
    except Exception as e:
        print(f"转换过程中出错: {e}")

def convert_and_enhance_model_analysis():
    """转换并增强模型分析文件"""
    
    config = Config()
    analyzer = ComponentAnalyzer(config)
    
    # 读取原始文件
    input_file = "results/qwen_7b_v5/model_analysis.json"
    output_file = "results/qwen_7b_v5/model_analysis_enhanced.json"
    
    try:
        print(f"\n=== 转换并增强文件 {input_file} ===\n")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"原始文件包含 {len(data)} 个图像")
        
        # 转换并增强所有数据
        enhanced_data = {}
        for image_key, image_data in data.items():
            enhanced_image_data = image_data.copy()
            
            # 处理component_details
            if 'component_details' in enhanced_image_data:
                enhanced_component_details = {}
                for component_key, component_data in enhanced_image_data['component_details'].items():
                    # 先转换box格式
                    converted_component = analyzer.convert_boxes_in_data(component_data)
                    # 再增强可视化IO信息
                    enhanced_component = analyzer.enhance_component_with_visual_io(converted_component)
                    enhanced_component_details[component_key] = enhanced_component
                
                enhanced_image_data['component_details'] = enhanced_component_details
            
            enhanced_data[image_key] = enhanced_image_data
        
        # 保存增强后的文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
        
        print(f"转换和增强完成！保存到: {output_file}")
        
        # 显示一个示例转换结果
        if enhanced_data:
            first_key = list(enhanced_data.keys())[0]
            if 'component_details' in enhanced_data[first_key]:
                details = enhanced_data[first_key]['component_details']
                if details:
                    first_component = list(details.keys())[0]
                    component_data = details[first_component]
                    
                    print(f"\n示例增强结果 (组件: {first_component}):")
                    
                    if 'description' in component_data:
                        desc = component_data['description']
                        if 'box' in desc:
                            print(f"主要box: {desc['box']}")
                    
                    if 'visual_io_ports' in component_data:
                        visual_ports = component_data['visual_io_ports']
                        print(f"可视化输入端口: {visual_ports.get('input', [])}")
                        print(f"可视化输出端口: {visual_ports.get('output', [])}")
                    
                    if 'description' in component_data and 'connections' in component_data['description']:
                        connections = component_data['description']['connections']
                        print("连接信息（含可视化位置）:")
                        for conn_type in ['input', 'output', 'bidirectional']:
                            if conn_type in connections:
                                for i, conn in enumerate(connections[conn_type]):
                                    visual_pos = conn.get('visual_position', '未知')
                                    print(f"  {conn_type}[{i}]: {conn.get('name', '未知')} -> 位置: {visual_pos}")
        
    except FileNotFoundError:
        print(f"文件 {input_file} 不存在")
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
    except Exception as e:
        print(f"转换过程中出错: {e}")

if __name__ == "__main__":
    # 运行所有测试
    test_box_parsing()
    test_convert_json_data()
    test_visual_io_enhancement()
    convert_model_analysis_file()
    convert_and_enhance_model_analysis() 