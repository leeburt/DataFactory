#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示box格式转换和可视化IO端口信息的脚本
"""

import json
import re

def parse_box_format(box_str: str) -> str:
    """解析box格式字符串并返回(x1,y1,x2,y2)的字符串格式"""
    if not box_str or not isinstance(box_str, str):
        return None
        
    try:
        # 格式1: <|box_start|>(x1,y1),(x2,y2)<|box_end|>
        pattern1 = r'<\|box_start\|>\((\d+),(\d+)\),\((\d+),(\d+)\)<\|box_end\|>'
        match1 = re.search(pattern1, box_str)
        if match1:
            x1, y1, x2, y2 = map(int, match1.groups())
            return f"({x1}, {y1}, {x2}, {y2})"
        
        # 格式2: [x1, y1, x2, y2]
        pattern2 = r'\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]'
        match2 = re.search(pattern2, box_str)
        if match2:
            x1, y1, x2, y2 = map(int, match2.groups())
            return f"({x1}, {y1}, {x2}, {y2})"
        
        # 格式3: (x1,y1,x2,y2)
        pattern3 = r'\((\d+),(\d+),(\d+),(\d+)\)'
        match3 = re.search(pattern3, box_str)
        if match3:
            x1, y1, x2, y2 = map(int, match3.groups())
            return f"({x1}, {y1}, {x2}, {y2})"
            
        # 如果是数组格式，尝试直接解析
        if box_str.strip().startswith('[') and box_str.strip().endswith(']'):
            coords = json.loads(box_str)
            if len(coords) == 4:
                return f"({coords[0]}, {coords[1]}, {coords[2]}, {coords[3]})"
                
    except (ValueError, json.JSONDecodeError, AttributeError) as e:
        print(f"解析box格式时出错: {box_str}, 错误: {e}")
        
    return None

def convert_io_coordinates(io_data: dict) -> dict:
    """转换输入输出坐标信息为(x1,y1,x2,y2)格式的字符串"""
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

def demo_conversion():
    """演示转换功能"""
    
    print("=== Box格式转换演示 ===\n")
    
    # 测试不同的box格式
    test_cases = [
        "<|box_start|>(599,160),(737,253)<|box_end|>",
        "[599, 160, 737, 253]",
        "(599,160,737,253)"
    ]
    
    for box_str in test_cases:
        result = parse_box_format(box_str)
        print(f"原格式: {box_str}")
        print(f"转换后: {result}")
        print("-" * 50)
    
    print("\n=== 可视化IO端口转换演示 ===\n")
    
    # 模拟组件的IO端口数据
    io_data = {
        "input": [
            [653, 138, 683, 169]
        ],
        "output": [
            [658, 240, 677, 259],
            [727, 196, 742, 211]
        ]
    }
    
    print("原始IO数据:")
    print(json.dumps(io_data, indent=2))
    
    converted_io = convert_io_coordinates(io_data)
    print("\n转换后的IO数据:")
    print(json.dumps(converted_io, indent=2, ensure_ascii=False))
    
    print("\n=== 完整组件数据示例 ===\n")
    
    # 完整的组件数据示例
    component_example = {
        "component_name": "SEQUENCER",
        "component_box": "(599, 160, 737, 253)",
        "connections": {
            "input": [
                {
                    "name": "CLOCK EXTRACTOR",
                    "target_box": "(343, 10, 481, 102)",
                    "visual_position": "(653, 138, 683, 169)"
                }
            ],
            "output": [
                {
                    "name": "MEMORY ARRAY",
                    "target_box": "(797, 159, 935, 252)",
                    "visual_position": "(658, 240, 677, 259)"
                }
            ]
        },
        "visual_io_ports": {
            "input": ["(653, 138, 683, 169)"],
            "output": ["(658, 240, 677, 259)", "(727, 196, 742, 211)"]
        }
    }
    
    print("完整的组件数据示例（含可视化位置）:")
    print(json.dumps(component_example, indent=2, ensure_ascii=False))
    
    print("\n=== 说明 ===")
    print("1. component_box: 组件在图像中的边界框位置")
    print("2. connections.input/output.visual_position: 该连接在图像中的实际端口位置")
    print("3. visual_io_ports: 所有输入输出端口在图像中的可视化位置")
    print("4. 所有坐标格式统一为: (x1, y1, x2, y2)")

if __name__ == "__main__":
    demo_conversion() 