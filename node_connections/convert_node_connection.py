import json
import re
from difflib import SequenceMatcher
import traceback

def calculate_iou(box1, box2):
    """计算两个边界框的IoU"""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    if x2 <= x1 or y2 <= y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0

def calculate_similarity(str1, str2):
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def parse_box_string(box_str):
    """解析边界框字符串，支持多种格式"""
    # 移除括号并分割
    box_str = eval(box_str) 
    return box_str

def find_best_match(target_box, target_name, components, component_details):
    """根据IoU和名字相似性找到最佳匹配的组件"""
    best_match = None
    best_score = 0.0
    
    for comp_key in components.keys():
        # 解析组件边界框
        comp_box = parse_box_string(comp_key)
        
        # 计算IoU
        if len(target_box) == 0 or len(comp_box) == 0:
            continue
        iou = calculate_iou(target_box, comp_box)
        
        # 获取组件名字
        comp_name = ""
        if comp_key in component_details:
            comp_name = component_details[comp_key]["description"]["component_name"]
        
        # 计算名字相似度
        name_sim = calculate_similarity(target_name, comp_name) if target_name and comp_name else 0.0
        
        # 综合得分：IoU权重0.7，名字相似度权重0.3
        score = iou * 0.7 + name_sim * 0.3
        # print(f"score: {score}, iou: {iou}, name_sim: {name_sim}")
        if score > best_score and score > 0.1:  # 设置最低阈值
            best_score = score
            best_match = comp_key
    
    return best_match

def process_connection(conn, components, component_details):
    """处理单个连接的映射"""
    if not ('box' in conn and conn['box']):
        return
    try:
        target_box = parse_box_string(conn['box'])
        target_name = conn.get('name', '')
        
        best_match = find_best_match(target_box, target_name, components, component_details)
        if best_match:
            conn['box'] = best_match
            conn['name'] = components[best_match]['name']
        else:
            conn.clear()  # 清空连接信息
    except:
        # 如果解析失败，跳过这个连接
        print(f"解析失败: {traceback.format_exc()}")  
        conn.clear()
    return conn


def convert_image_data(image_data):
    # 遍历每个图像的数据
    
    if 'components' not in image_data or 'component_details' not in image_data:
        return {"message": "components or component_details not found"}
    
    components = image_data['components']
    component_details = image_data['component_details']
    
    # 1. 为components中的每个组件添加名字

    for comp_key in components.keys():
        if comp_key in component_details and 'description' in component_details[comp_key] and 'component_name' in component_details[comp_key]['description']:
            # print(f"comp_key: {comp_key}, component_details[comp_key]: {component_details[comp_key]}")
            components[comp_key]['name'] = component_details.get(comp_key,{}).get('description',{}).get('component_name',"")
        else:
            components[comp_key]['name'] = ""


    
    # 2. 处理component_details中的输入输出映射
    for detail_key, detail_value in component_details.items():
        if 'description' not in detail_value or 'connections' not in detail_value['description']:
            continue
        
        connections = detail_value['description']['connections']
        
        # 处理所有类型的连接
        for conn_type in ['input', 'output', 'bidirectional']:
            if conn_type in connections:
                rtn_connections = []
                for conn in connections[conn_type]:
                    rtn_conn = process_connection(conn, components, component_details)
                    if rtn_conn:
                        rtn_connections.append(rtn_conn)
                detail_value['description']['connections'][conn_type] = rtn_connections
    return image_data
    

def process_json_file(input_file, output_file):
    """处理JSON文件的主函数"""
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

        # 遍历每个图像的数据
    for image_name, image_data in data.items():
        data[image_name] = convert_image_data(image_data)

    # 保存处理后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"处理完成，结果已保存到 {output_file}")

def main():
    """主函数"""
    import argparse 
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str, required=True)
    parser.add_argument("--output_file", type=str, required=False,default="")
    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output_file

    print(f"处理文件: {input_file}")
    
    if not output_file:
        output_file = input_file.replace('.json', '_processed.json')
    
    try:
        process_json_file(input_file, output_file)
    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except json.JSONDecodeError:
        print(f"错误：{input_file} 不是有效的JSON文件")
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main() 