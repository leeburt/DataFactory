#!/usr/bin/env python3
"""
测试脚本：演示如何将模型输出结果转换为字典格式
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from node_connections.get_node_info_from_det import ComponentAnalyzer

def main():
    """主函数：演示结果转换"""
    
    print("开始转换模型结果...")
    
    # 初始化配置和分析器
    config = Config()
    analyzer = ComponentAnalyzer(config)
    
    # 检查是否存在模型分析结果文件
    if not os.path.exists(analyzer.model_analysis_path):
        print(f"错误：未找到模型分析结果文件: {analyzer.model_analysis_path}")
        print("请先运行模型分析流程生成结果文件")
        return
    
    # 加载现有结果
    analyzer.load_results()
    
    print(f"已加载 {len(analyzer.all_results)} 个图像的分析结果")
    
    # 转换结果
    converted_results = analyzer.convert_model_results()
    
    # 保存转换后的结果
    converted_path = analyzer.save_converted_results(converted_results)
    
    # 显示统计信息
    print("\n转换统计信息:")
    total_components = 0
    successful_conversions = 0
    failed_conversions = 0
    
    for image_id, image_data in converted_results.items():
        component_count = len(image_data.get("component_details", {}))
        total_components += component_count
        
        for component_key, component_info in image_data.get("component_details", {}).items():
            if isinstance(component_info, dict):
                status = component_info.get("status", "未知")
                if status == "成功解析JSON":
                    successful_conversions += 1
                elif status == "解析失败":
                    failed_conversions += 1
    
    print(f"- 总图像数: {len(converted_results)}")
    print(f"- 总组件数: {total_components}")
    print(f"- 成功转换: {successful_conversions}")
    print(f"- 转换失败: {failed_conversions}")
    print(f"- 成功率: {successful_conversions/total_components*100:.1f}%" if total_components > 0 else "- 成功率: 0%")
    
    # 显示示例转换结果
    print("\n示例转换结果:")
    for image_id, image_data in list(converted_results.items())[:1]:  # 只显示第一个图像的结果
        print(f"\n图像: {image_id}")
        for component_key, component_info in list(image_data.get("component_details", {}).items())[:2]:  # 只显示前两个组件
            print(f"  组件: {component_key}")
            if isinstance(component_info, dict) and "parsed_data" in component_info:
                parsed_data = component_info["parsed_data"]
                component_name = parsed_data.get("component_name", "未知组件")
                print(f"    组件名称: {component_name}")
                
                connections = parsed_data.get("connections", {})
                inputs = connections.get("input", [])
                outputs = connections.get("output", [])
                
                if isinstance(inputs, list):
                    print(f"    输入数量: {len(inputs)}")
                elif isinstance(inputs, dict):
                    print(f"    输入: 1个 ({inputs.get('name', '未知')})")
                
                if isinstance(outputs, list):
                    print(f"    输出数量: {len(outputs)}")
                elif isinstance(outputs, dict):
                    print(f"    输出: 1个 ({outputs.get('name', '未知')})")
            else:
                print(f"    状态: {component_info.get('status', '未知')}")
    
    print(f"\n完整的转换结果已保存到: {converted_path}")

if __name__ == "__main__":
    main() 