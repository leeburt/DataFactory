#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gen_data import FlowchartGenerator
import json

def test_single_flowchart():
    """测试单个流程图生成"""
    print("生成测试流程图...")
    
    # 创建流程图生成器
    generator = FlowchartGenerator(800, 600)
    
    # 生成8个节点
    generator.generate_random_nodes(8)
    
    # 打印节点信息
    print("\n节点信息:")
    for i, node in enumerate(generator.nodes):
        print(f"节点 {i}: {node.node_type}, 输入点: {len(node.input_points)}, 输出点: {len(node.output_points)}")
    
    # 生成连接
    generator.generate_connections()
    
    print(f"\n连接数量: {len(generator.connections)}")
    
    # 打印连接信息
    for i, conn in enumerate(generator.connections):
        start_node_idx = generator.nodes.index(conn.start_node)
        end_node_idx = generator.nodes.index(conn.end_node)
        print(f"连接 {i}: 节点{start_node_idx}({conn.start_node.node_type}) -> 节点{end_node_idx}({conn.end_node.node_type})")
    
    # 绘制流程图
    image_file = generator.draw_flowchart("test_flowchart.png")
    print(f"\n流程图保存到: {image_file}")
    
    # 获取YOLO数据
    yolo_data = generator.get_yolo_pose_data()
    
    # 保存标注数据
    generator.save_yolo_annotation(yolo_data, "test_annotation.json")
    
    # 生成YOLO txt格式
    txt_content = generator.generate_yolo_txt_format(yolo_data)
    with open("test_annotation.txt", "w") as f:
        f.write(txt_content)
    
    print(f"\n总节点数: {len(yolo_data['nodes'])}")
    print(f"总关键点数: {len(yolo_data['keypoints'])}")
    
    # 验证节点类型
    start_nodes = [node for node in yolo_data['nodes'] if node['node_type'] == 'start']
    end_nodes = [node for node in yolo_data['nodes'] if node['node_type'] == 'end']
    
    print(f"\nstart节点数: {len(start_nodes)}")
    print(f"end节点数: {len(end_nodes)}")
    
    # 验证start和end节点的输入输出点
    if start_nodes:
        start_node = start_nodes[0]
        input_points = [kp for kp in start_node['keypoints'] if kp['type'] == 'input']
        output_points = [kp for kp in start_node['keypoints'] if kp['type'] == 'output']
        print(f"start节点 - 输入点: {len(input_points)}, 输出点: {len(output_points)}")
    
    if end_nodes:
        end_node = end_nodes[0]
        input_points = [kp for kp in end_node['keypoints'] if kp['type'] == 'input']
        output_points = [kp for kp in end_node['keypoints'] if kp['type'] == 'output']
        print(f"end节点 - 输入点: {len(input_points)}, 输出点: {len(output_points)}")
    
    return True

if __name__ == "__main__":
    test_single_flowchart() 