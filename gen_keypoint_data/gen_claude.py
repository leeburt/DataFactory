import graphviz
import json
import random
import os
import re # 引入正则表达式模块
from PIL import Image

# --- 配置参数 ---
CLASS_ID_NODE = 0
CLASS_ID_INPUT = 1
CLASS_ID_OUTPUT = 2

def parse_xdot(xdot_string, img_height):
    """
    一个简单的解析器，用于从 xdot 字符串中提取节点和边的坐标。
    """
    yolo_objects = {}
    lines = xdot_string.split('\n')
    
    # 正则表达式
    node_pattern = re.compile(r'_draw_\s*=\s*".*?c 7 -#000000.*?P 4 ([\d\.]+) ([\d\.]+) ([\d\.]+) ([\d\.]+) ([\d\.]+) ([\d\.]+) ([\d\.]+) ([\d\.]+).*?";\s*# Node: (.*)')
    edge_pattern = re.compile(r'_hldraw_\s*=\s*".*?c 7 -#000000.*?p 3 ([\d\.]+) ([\d\.]+) ([\d\.]+) ([\d\.]+) ([\d\.]+) ([\d\.]+).*?";\s*# Edge: (.*) -> (.*)')
    edge_tail_pattern = re.compile(r'_tdraw_\s*=\s*".*?c 7 -#000000.*?B 4 ([\d\.]+) ([\d\.]+) .*?";\s*# Edge: (.*) -> (.*)')


    # 1. 查找所有节点定义并初始化 yolo_objects
    # xdot 不直接给出节点名，我们通过注释来识别
    for line in lines:
        if line.strip().startswith('// Node '):
            node_name = line.strip().split(' ')[-1]
            yolo_objects[node_name] = {'bbox': None, 'keypoints': []}

    # 2. 解析节点的 BBox
    # xdot 通过一系列绘图指令来画图，我们需要找到画矩形的指令
    for line in lines:
        # 在xdot中，节点通常被画成一个填充矩形(F)和一个边框矩形(P)
        if 'c 7 -#000000' in line and ' P 4 ' in line and line.strip().endswith(';'):
            parts = line.split('"')
            if len(parts) > 1:
                draw_commands = parts[1]
                node_name_match = re.search(r'// Node (\S+)', line)
                if node_name_match:
                    node_name = node_name_match.group(1)
                    
                    # 提取矩形的四个点
                    points_match = re.search(r'P 4 ([\d\.]+\s[\d\.]+) ([\d\.]+\s[\d\.]+) ([\d\.]+\s[\d\.]+) ([\d\.]+\s[\d\.]+)', draw_commands)
                    if points_match:
                        points_str = points_match.groups()
                        points = [list(map(float, p.split())) for p in points_str]
                        
                        all_x = [p[0] for p in points]
                        all_y = [p[1] for p in points]
                        
                        llx, urx = min(all_x), max(all_x)
                        lly, ury = min(all_y), max(all_y)
                        
                        if node_name in yolo_objects:
                             yolo_objects[node_name]['bbox_points'] = (llx, lly, urx, ury)


    # 3. 解析边的端点
    for line in lines:
        # 提取边的头部（箭头，即输入点）
        if '_hldraw_' in line:
            head_match = re.search(r'# Edge: (\S+) -> (\S+)', line)
            if head_match:
                tail_node, head_node = head_match.groups()
                points_match = re.search(r'p 3 ([\d\.]+\s[\d\.]+) ([\d\.]+\s[\d\.]+) ([\d\.]+\s[\d\.]+)', line)
                if points_match:
                    points_str = points_match.groups()
                    # 箭头的尖端是这三个点的平均值或其中一个特定点，这里取第一个点作为近似
                    x, y = map(float, points_str[0].split())
                    if head_node in yolo_objects:
                        yolo_objects[head_node]['keypoints'].append({'pos': (x, y), 'type': CLASS_ID_INPUT})

        # 提取边的尾部（连接处，即输出点）
        if '_tdraw_' in line:
            tail_match = re.search(r'# Edge: (\S+) -> (\S+)', line)
            if tail_match:
                tail_node, head_node = tail_match.groups()
                # B-spline 的第一个点就是连接点
                bspline_match = re.search(r'B 4 ([\d\.]+\s[\d\.]+)', line)
                if bspline_match:
                    x, y = map(float, bspline_match.group(1).split())
                    if tail_node in yolo_objects:
                         yolo_objects[tail_node]['keypoints'].append({'pos': (x, y), 'type': CLASS_ID_OUTPUT})

    return yolo_objects


def generate_flowchart_data(output_dir, image_id):
    num_nodes = random.randint(5, 20)
    nodes = {}
    for i in range(num_nodes):
        node_name = f"node_{i}"
        num_inputs = random.randint(1, 10)
        num_outputs = random.randint(1, 10)
        inputs = [f"in_{j}" for j in range(num_inputs)]
        outputs = [f"out_{j}" for j in range(num_outputs)]
        nodes[node_name] = {'inputs': inputs, 'outputs': outputs}

    g = graphviz.Digraph(f'flowchart_{image_id}', format='png',
                        graph_attr={'nodesep': '1.0', 'ranksep': '1.5'},
                        node_attr={'comment': 'Node'}, # 添加注释以在xdot中识别
                        edge_attr={'comment': 'Edge'}) # 添加注释以在xdot中识别
                        
    g.attr(rankdir='LR', splines='ortho', concentrate='false')
    g.attr('node', shape='record', style='rounded,filled', fillcolor='lightblue')
    g.attr('edge', arrowsize='0.7')

    for name, ports in nodes.items():
        input_ports_label = " | ".join([f"<{p}> {p}" for p in ports['inputs']])
        output_ports_label = " | ".join([f"<{p}> {p}" for p in ports['outputs']])
        node_label = f"{{ {input_ports_label} }} | {name} | {{ {output_ports_label} }}"
        g.node(name, label=node_label, comment=f'Node {name}') # 为节点添加特定注释

    all_output_ports = [f"{name}:{port}" for name, data in nodes.items() for port in data['outputs']]
    all_input_ports = [f"{name}:{port}" for name, data in nodes.items() for port in data['inputs']]
    random.shuffle(all_output_ports)
    random.shuffle(all_input_ports)
    
    num_edges = min(len(all_output_ports), len(all_input_ports), random.randint(num_nodes, num_nodes * 2))
    used_inputs, used_outputs = set(), set()
    
    for i in range(num_edges):
        if i < len(all_output_ports) and i < len(all_input_ports):
            output_port_str, input_port_str = all_output_ports[i], all_input_ports[i]
            if output_port_str.split(':')[0] != input_port_str.split(':')[0]:
                 if input_port_str not in used_inputs and output_port_str not in used_outputs:
                    g.edge(output_port_str, input_port_str, comment=f"Edge {output_port_str.split(':')[0]} -> {input_port_str.split(':')[0]}")
                    used_inputs.add(input_port_str)
                    used_outputs.add(output_port_str)

    try:
        image_path = os.path.join(output_dir, 'images', f'flowchart_{image_id}.png')
        label_path = os.path.join(output_dir, 'labels', f'flowchart_{image_id}.txt')
        dot_source = g.source
        graph_obj = graphviz.Source(dot_source)
        
        # 改为使用 xdot 格式
        xdot_str = graph_obj.pipe(format='xdot').decode('utf-8')
        
        graph_obj.render(os.path.join(output_dir, 'images', f'flowchart_{image_id}'), format='png', cleanup=True)
    except graphviz.backend.execute.CalledProcessError as e:
        print(f"Error executing Graphviz for image {image_id}: {e}")
        print("Please ensure Graphviz is installed and in your system's PATH.")
        return

    with Image.open(image_path) as img:
        img_width, img_height = img.size

    # 使用新的解析器
    raw_yolo_objects = parse_xdot(xdot_str, img_height)
    
    with open(label_path, 'w') as f:
        for node_name, data in raw_yolo_objects.items():
            if data.get('bbox_points') is None or not data.get('keypoints'):
                continue

            # 处理 BBox
            llx, lly, urx, ury = data['bbox_points']
            x_min_px, y_min_px = llx, img_height - ury
            x_max_px, y_max_px = urx, img_height - lly
            
            box_w = (x_max_px - x_min_px)
            box_h = (y_max_px - y_min_px)
            x_center = x_min_px + box_w / 2
            y_center = y_min_px + box_h / 2
            
            x_center_norm = x_center / img_width
            y_center_norm = y_center / img_height
            w_norm = box_w / img_width
            h_norm = box_h / img_height
            
            bbox_str = f"{x_center_norm:.6f} {y_center_norm:.6f} {w_norm:.6f} {h_norm:.6f}"
            
            # 处理 Keypoints
            keypoints_list = []
            for kp_data in data['keypoints']:
                kpt_x, kpt_y = kp_data['pos']
                kpt_type = kp_data['type']
                
                kpt_x_px = kpt_x
                kpt_y_px = img_height - kpt_y
                kpt_x_norm = kpt_x_px / img_width
                kpt_y_norm = kpt_y_px / img_height
                
                keypoints_list.append(f"{kpt_x_norm:.6f} {kpt_y_norm:.6f} {kpt_type}")
                
            keypoints_str = " ".join(keypoints_list)
            
            if keypoints_str:
                line = f"{CLASS_ID_NODE} {bbox_str} {keypoints_str}\n"
                f.write(line)

    print(f"Successfully generated: {image_path} and {label_path}")


if __name__ == "__main__":
    output_directory = "flowchart_dataset"
    os.makedirs(os.path.join(output_directory, "images"), exist_ok=True)
    os.makedirs(os.path.join(output_directory, "labels"), exist_ok=True)
    number_of_samples = 20
    for i in range(number_of_samples):
        generate_flowchart_data(output_directory, i)
        
    print("\n--- Data Generation Complete ---")
    print(f"Dataset saved in: {os.path.abspath(output_directory)}")
    # ... (rest of the print statements)