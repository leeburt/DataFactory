import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Arrow
import numpy as np
import random
import json
import os
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Tuple, Optional
import math

class FlowchartNode:
    """流程图节点类"""
    def __init__(self, x: float, y: float, width: float, height: float, 
                 node_id: str, node_type: str, label: str):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.node_id = node_id
        self.node_type = node_type
        self.label = label
        self.input_points: List[Tuple[float, float]] = []
        self.output_points: List[Tuple[float, float]] = []
        
    def add_input_point(self, x: float, y: float):
        """添加输入点"""
        self.input_points.append((x, y))
    
    def add_output_point(self, x: float, y: float):
        """添加输出点"""
        self.output_points.append((x, y))
    
    def get_bbox(self) -> Tuple[float, float, float, float]:
        """获取边界框 (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)
    
    def get_center(self) -> Tuple[float, float]:
        """获取中心点"""
        return (self.x + self.width/2, self.y + self.height/2)

class FlowchartConnection:
    """流程图连接类"""
    def __init__(self, start_node: FlowchartNode, end_node: FlowchartNode,
                 start_point: Tuple[float, float], end_point: Tuple[float, float]):
        self.start_node = start_node
        self.end_node = end_node
        self.start_point = start_point
        self.end_point = end_point
        self.path_points: List[Tuple[float, float]] = []
        
    def generate_orthogonal_path(self):
        """生成横平竖直的路径"""
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        
        # 计算中间点以确保垂直进入和离开节点
        # 从输出点水平延伸一段距离，然后垂直转向输入点
        gap = 30  # 延伸距离
        
        # 从起点水平向右延伸
        mid_x1 = x1 + gap
        
        # 到终点水平向左延伸
        mid_x2 = x2 - gap
        
        # 如果两个延伸点重叠，使用中点
        if mid_x1 >= mid_x2:
            mid_x = (x1 + x2) / 2
            self.path_points = [(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)]
        else:
            # 标准的横平竖直路径
            if abs(y2 - y1) < 5:  # 如果Y坐标几乎相同，直接水平连接
                self.path_points = [(x1, y1), (x2, y2)]
            else:
                # 创建Z字形路径
                mid_y = (y1 + y2) / 2
                self.path_points = [(x1, y1), (mid_x1, y1), (mid_x1, mid_y), (mid_x2, mid_y), (mid_x2, y2), (x2, y2)]

class FlowchartGenerator:
    """流程图生成器"""
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.nodes: List[FlowchartNode] = []
        self.connections: List[FlowchartConnection] = []
        self.margin = 50
        self.node_types = ['process', 'decision', 'start', 'end', 'data']
        self.colors = {
            'process': '#4CAF50',
            'decision': '#FF9800',
            'start': '#2196F3',
            'end': '#F44336',
            'data': '#9C27B0'
        }
        
    def generate_random_nodes(self, num_nodes: int = None):
        """生成随机节点"""
        if num_nodes is None:
            num_nodes = random.randint(5, 12)
        
        # 创建网格布局
        grid_cols = int(math.sqrt(num_nodes)) + 1
        grid_rows = (num_nodes + grid_cols - 1) // grid_cols
        
        cell_width = (self.width - 2 * self.margin) / grid_cols
        cell_height = (self.height - 2 * self.margin) / grid_rows
        
        for i in range(num_nodes):
            row = i // grid_cols
            col = i % grid_cols
            
            # 在网格单元内随机偏移
            base_x = self.margin + col * cell_width
            base_y = self.margin + row * cell_height
            
            # 随机偏移，但确保不超出边界
            offset_x = random.uniform(-cell_width * 0.2, cell_width * 0.2)
            offset_y = random.uniform(-cell_height * 0.2, cell_height * 0.2)
            
            x = max(self.margin, min(base_x + offset_x, self.width - self.margin - 120))
            y = max(self.margin, min(base_y + offset_y, self.height - self.margin - 80))
            
            # 节点尺寸
            if i == 0:
                node_type = 'start'
                width, height = 80, 40
            elif i == num_nodes - 1:
                node_type = 'end'
                width, height = 80, 40
            else:
                node_type = random.choice(self.node_types[:-2])  # 不选择start和end
                if node_type == 'decision':
                    width, height = 100, 60
                else:
                    width, height = 120, 50
            
            node = FlowchartNode(x, y, width, height, f"node_{i}", node_type, f"Node {i}")
            
            # 生成输入输出点
            self.generate_io_points(node)
            self.nodes.append(node)
    
    def generate_io_points(self, node: FlowchartNode):
        """为节点生成输入输出点"""
        # 根据节点类型生成输入输出点
        if node.node_type == 'start':
            # start节点只有输出点，没有输入点
            num_inputs = 0
            num_outputs = random.randint(1, 2)
        elif node.node_type == 'end':
            # end节点只有输入点，没有输出点
            num_inputs = random.randint(1, 2)
            num_outputs = 0
        else:
            # 其他节点有输入和输出点
            num_inputs = random.randint(1, 3)
            num_outputs = random.randint(1, 3)
        
        # 生成输入点（在节点左边）
        for i in range(num_inputs):
            offset = (i + 1) * node.height / (num_inputs + 1)
            x = node.x
            y = node.y + offset
            node.add_input_point(x, y)
        
        # 生成输出点（在节点右边）
        for i in range(num_outputs):
            offset = (i + 1) * node.height / (num_outputs + 1)
            x = node.x + node.width
            y = node.y + offset
            node.add_output_point(x, y)
    
    def generate_connections(self):
        """生成节点连接"""
        if len(self.nodes) < 2:
            return
        
        # 找到start和end节点
        start_nodes = [i for i, node in enumerate(self.nodes) if node.node_type == 'start']
        end_nodes = [i for i, node in enumerate(self.nodes) if node.node_type == 'end']
        
        # 确保流程图是连通的 - 从start节点开始构建主路径
        if start_nodes:
            start_idx = start_nodes[0]
            connected_nodes = {start_idx}
            current_idx = start_idx
            
            # 创建一条从start到end的主路径
            available_nodes = [i for i in range(len(self.nodes)) if i not in connected_nodes]
            
            while available_nodes:
                # 如果有end节点且还没连接，优先连接end节点
                if end_nodes and any(idx in available_nodes for idx in end_nodes):
                    # 如果当前节点有输出点，且还有其他节点可连接，不急于连接end
                    if len(available_nodes) > 1 and any(idx in end_nodes for idx in available_nodes):
                        next_candidates = [idx for idx in available_nodes if idx not in end_nodes]
                        if next_candidates:
                            next_idx = random.choice(next_candidates)
                        else:
                            next_idx = random.choice([idx for idx in available_nodes if idx in end_nodes])
                    else:
                        next_idx = random.choice([idx for idx in available_nodes if idx in end_nodes])
                else:
                    next_idx = random.choice(available_nodes)
                
                # 创建连接
                from_node = self.nodes[current_idx]
                to_node = self.nodes[next_idx]
                
                # 检查是否可以连接
                if from_node.output_points and to_node.input_points:
                    start_point = random.choice(from_node.output_points)
                    end_point = random.choice(to_node.input_points)
                    
                    connection = FlowchartConnection(from_node, to_node, start_point, end_point)
                    connection.generate_orthogonal_path()
                    self.connections.append(connection)
                    
                    connected_nodes.add(next_idx)
                    available_nodes.remove(next_idx)
                    current_idx = next_idx
                else:
                    # 如果无法连接，从连接的节点中选择一个新的起点
                    possible_starts = [idx for idx in connected_nodes if self.nodes[idx].output_points]
                    if possible_starts:
                        current_idx = random.choice(possible_starts)
                    else:
                        break
        
        # 添加一些额外的连接，但要避免过多
        max_extra = min(2, len(self.nodes) - 2)
        num_extra = random.randint(0, max_extra)
        
        for _ in range(num_extra):
            # 找到有输出点的节点
            from_candidates = [i for i, node in enumerate(self.nodes) if node.output_points and node.node_type != 'end']
            # 找到有输入点的节点
            to_candidates = [i for i, node in enumerate(self.nodes) if node.input_points and node.node_type != 'start']
            
            if from_candidates and to_candidates:
                from_idx = random.choice(from_candidates)
                to_idx = random.choice(to_candidates)
                
                # 避免重复连接
                if from_idx != to_idx:
                    from_node = self.nodes[from_idx]
                    to_node = self.nodes[to_idx]
                    
                    # 检查是否已经存在这个连接
                    existing = any(conn.start_node == from_node and conn.end_node == to_node 
                                 for conn in self.connections)
                    
                    if not existing:
                        start_point = random.choice(from_node.output_points)
                        end_point = random.choice(to_node.input_points)
                        
                        connection = FlowchartConnection(from_node, to_node, start_point, end_point)
                        connection.generate_orthogonal_path()
                        self.connections.append(connection)
    
    def draw_flowchart(self, filename: str = "flowchart.png"):
        """绘制流程图"""
        fig, ax = plt.subplots(figsize=(self.width/100, self.height/100))
        ax.set_xlim(0, self.width)
        ax.set_ylim(0, self.height)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # 绘制连接线
        for connection in self.connections:
            points = connection.path_points
            if len(points) >= 2:
                for i in range(len(points) - 1):
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]
                    ax.plot([x1, x2], [self.height - y1, self.height - y2], 
                           'k-', linewidth=2, zorder=1)
                
                # 绘制箭头在连接线末端
                if len(points) >= 2:
                    # 最后一段的方向
                    x1, y1 = points[-2]
                    x2, y2 = points[-1]
                    
                    # 计算箭头方向
                    dx = x2 - x1
                    dy = y2 - y1
                    
                    # 标准化方向
                    if dx != 0 or dy != 0:
                        length = math.sqrt(dx*dx + dy*dy)
                        dx /= length
                        dy /= length
                        
                        # 箭头大小
                        arrow_size = 8
                        
                        # 箭头起点（稍微向后一点）
                        arrow_start_x = x2 - dx * arrow_size
                        arrow_start_y = y2 - dy * arrow_size
                        
                        arrow = patches.FancyArrowPatch(
                            (arrow_start_x, self.height - arrow_start_y),
                            (x2, self.height - y2),
                            arrowstyle='->', mutation_scale=15,
                            color='black', zorder=2
                        )
                        ax.add_patch(arrow)
        
        # 绘制节点
        for node in self.nodes:
            y_flipped = self.height - node.y - node.height
            
            if node.node_type == 'decision':
                # 菱形
                diamond = patches.RegularPolygon((node.x + node.width/2, y_flipped + node.height/2),
                                               4, radius=node.width/2,
                                               orientation=math.pi/4,
                                               facecolor=self.colors[node.node_type],
                                               edgecolor='black', linewidth=2, zorder=3)
                ax.add_patch(diamond)
            else:
                # 矩形
                rect = patches.Rectangle((node.x, y_flipped), node.width, node.height,
                                       facecolor=self.colors[node.node_type],
                                       edgecolor='black', linewidth=2, zorder=3)
                ax.add_patch(rect)
            
            # 添加文本
            ax.text(node.x + node.width/2, y_flipped + node.height/2, node.label,
                   ha='center', va='center', fontsize=10, fontweight='bold', zorder=4)
            
            # 只绘制实际存在的输入输出点
            if node.input_points:  # 只有当节点有输入点时才绘制
                for px, py in node.input_points:
                    circle = Circle((px, self.height - py), 4, color='blue', zorder=5)
                    ax.add_patch(circle)
                    # 添加一个小的水平线段表示输入
                    ax.plot([px-8, px], [self.height - py, self.height - py], 'b-', linewidth=2, zorder=4)
            
            if node.output_points:  # 只有当节点有输出点时才绘制
                for px, py in node.output_points:
                    circle = Circle((px, self.height - py), 4, color='red', zorder=5)
                    ax.add_patch(circle)
                    # 添加一个小的水平线段表示输出
                    ax.plot([px, px+8], [self.height - py, self.height - py], 'r-', linewidth=2, zorder=4)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=100, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        
        return filename
    
    def get_yolo_pose_data(self) -> Dict:
        """获取YOLO pose格式的数据"""
        data = {
            'image_width': self.width,
            'image_height': self.height,
            'nodes': [],
            'keypoints': []
        }
        
        for node in self.nodes:
            # 节点边界框（用于目标检测）
            x, y, w, h = node.get_bbox()
            # 归一化坐标
            x_norm = x / self.width
            y_norm = y / self.height
            w_norm = w / self.width
            h_norm = h / self.height
            
            # 中心点坐标
            cx_norm = x_norm + w_norm / 2
            cy_norm = y_norm + h_norm / 2
            
            node_data = {
                'node_id': node.node_id,
                'node_type': node.node_type,
                'bbox': [cx_norm, cy_norm, w_norm, h_norm],  # YOLO格式：center_x, center_y, width, height
                'keypoints': []
            }
            
            # 输入点关键点
            for i, (px, py) in enumerate(node.input_points):
                kp = {
                    'id': f"{node.node_id}_input_{i}",
                    'type': 'input',
                    'x': px / self.width,
                    'y': py / self.height,
                    'visibility': 1  # 1表示可见
                }
                node_data['keypoints'].append(kp)
                data['keypoints'].append(kp)
            
            # 输出点关键点
            for i, (px, py) in enumerate(node.output_points):
                kp = {
                    'id': f"{node.node_id}_output_{i}",
                    'type': 'output',
                    'x': px / self.width,
                    'y': py / self.height,
                    'visibility': 1
                }
                node_data['keypoints'].append(kp)
                data['keypoints'].append(kp)
            
            data['nodes'].append(node_data)
        
        return data
    
    def save_yolo_annotation(self, data: Dict, filename: str):
        """保存YOLO pose格式的标注文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def generate_yolo_txt_format(self, data: Dict) -> str:
        """生成YOLO txt格式的标注"""
        lines = []
        
        # 类别映射
        class_mapping = {
            'process': 0,
            'decision': 1,
            'start': 2,
            'end': 3,
            'data': 4
        }
        
        for node in data['nodes']:
            # 节点类别
            class_id = class_mapping.get(node['node_type'], 0)
            
            # 边界框
            cx, cy, w, h = node['bbox']
            
            # 关键点
            keypoints = []
            for kp in node['keypoints']:
                keypoints.extend([kp['x'], kp['y'], kp['visibility']])
            
            # 组装行
            line = f"{class_id} {cx} {cy} {w} {h}"
            if keypoints:
                line += " " + " ".join(map(str, keypoints))
            
            lines.append(line)
        
        return "\n".join(lines)

def generate_batch_data(output_dir: str, num_samples: int = 100):
    """生成批量数据"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    images_dir = os.path.join(output_dir, 'images')
    labels_dir = os.path.join(output_dir, 'labels')
    annotations_dir = os.path.join(output_dir, 'annotations')
    
    for dir_path in [images_dir, labels_dir, annotations_dir]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    for i in range(num_samples):
        print(f"生成第 {i+1}/{num_samples} 个样本...")
        
        # 创建流程图生成器
        generator = FlowchartGenerator(
            width=random.randint(600, 1000),
            height=random.randint(400, 800)
        )
        
        # 生成节点和连接
        generator.generate_random_nodes(random.randint(5, 15))
        generator.generate_connections()
        
        # 绘制流程图
        image_filename = f"flowchart_{i:04d}.png"
        image_path = os.path.join(images_dir, image_filename)
        generator.draw_flowchart(image_path)
        
        # 获取YOLO数据
        yolo_data = generator.get_yolo_pose_data()
        
        # 保存JSON格式标注
        json_filename = f"flowchart_{i:04d}.json"
        json_path = os.path.join(annotations_dir, json_filename)
        generator.save_yolo_annotation(yolo_data, json_path)
        
        # 保存YOLO txt格式标注
        txt_filename = f"flowchart_{i:04d}.txt"
        txt_path = os.path.join(labels_dir, txt_filename)
        txt_content = generator.generate_yolo_txt_format(yolo_data)
        with open(txt_path, 'w') as f:
            f.write(txt_content)
    
    print(f"成功生成 {num_samples} 个样本到 {output_dir}")

if __name__ == "__main__":
    # 生成测试数据
    generate_batch_data("./output", 50)
    
    # 生成单个示例
    print("\n生成单个示例...")
    generator = FlowchartGenerator(800, 600)
    generator.generate_random_nodes(8)
    generator.generate_connections()
    
    # 绘制并保存
    image_file = generator.draw_flowchart("example_flowchart.png")
    print(f"示例流程图保存到: {image_file}")
    
    # 获取YOLO数据
    yolo_data = generator.get_yolo_pose_data()
    generator.save_yolo_annotation(yolo_data, "example_annotation.json")
    
    # 打印关键点信息
    print(f"\n流程图包含 {len(yolo_data['nodes'])} 个节点")
    print(f"总计 {len(yolo_data['keypoints'])} 个关键点")
    
    for node in yolo_data['nodes']:
        print(f"节点 {node['node_id']} ({node['node_type']}): {len(node['keypoints'])} 个关键点")