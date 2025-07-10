import json
import os
from pathlib import Path

def convert_component_details_to_test_format(component_details):
    """
    将 component_details 转换为 test.json 格式
    """
    result = {}
    
    for box_coord, details in component_details.items():
        if 'description' not in details:
            print("details:",details)
            continue
            
        description = details['description']
        component_name = description.get('component_name')
        
        # 解析边界框坐标
        # box_coord 格式如 "[599, 160, 737, 253]"
        coords = eval(box_coord)  # 将字符串转换为列表
        component_box = [float(coord) for coord in coords]
        
        # 转换连接信息
        connections = {
            "input": [],
            "output": [],
            "inout": []
        }
        
        # 处理输入连接
        if 'input' in description.get('connections', {}):
            for input_conn in description['connections']['input']:

                connections['input'].append({
                    "name": input_conn.get('name'),
                    "count": 1  # 默认值为1
                })
        
        # 处理输出连接
        if 'output' in description.get('connections', {}):
            for output_conn in description['connections']['output']:
                connections['output'].append({
                    "name": output_conn.get('name'),
                    "count": 1  # 默认值为1
                })
        
        # 处理双向连接（如果有的话，添加到 inout）
        if 'bidirectional' in description.get('connections', {}):
            for bidir_conn in description['connections']['bidirectional']:
                connections['inout'].append({
                    "name": bidir_conn.get('name'),
                    "count": 1  # 默认值为1
                })
        
        # 使用组件名作为键
        result[component_name] = {
            "component_box": component_box,
            "connections": connections
        }
    
    return result

def process_model_analysis_file(input_file, output_dir):
    """
    处理 model_analysis.json 文件，为每个图片生成单独的 JSON 文件
    """
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    processed_count = 0
    
    for image_name, image_data in data.items():
        # 检查是否有 component_details
        if 'component_details' not in image_data or not image_data['component_details']:
            print(f"跳过 {image_name}：没有 component_details 数据")
            continue
        
        # 转换数据格式
        converted_data = convert_component_details_to_test_format(image_data['component_details'])
        
        if not converted_data:
            print(f"跳过 {image_name}：转换后没有有效数据")
            continue
        
        # 生成输出文件名
        output_filename = f"{Path(image_name).stem}.json"
        output_filepath = output_path / output_filename
        
        # 保存转换后的数据
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, ensure_ascii=False)
        
        processed_count += 1
        print(f"已处理 {image_name} -> {output_filepath}")
    
    print(f"\n总共处理了 {processed_count} 个图片文件")

def main():
    # 配置输入和输出路径
    input_files = [
        "/data/home/libo/work/DataFactory/results/1_stage_with_box/model_analysis.json",
    ]
    
    for input_file in input_files:
        if os.path.exists(input_file):
            print(f"\n处理文件: {input_file}")
            # 根据输入文件路径生成输出目录
            output_dir = f"converted_data/{Path(input_file).parent.name}"
            process_model_analysis_file(input_file, output_dir)
            break  # 找到第一个存在的文件就处理
    else:
        print("未找到有效的 model_analysis.json 文件")

if __name__ == "__main__":
    main() 