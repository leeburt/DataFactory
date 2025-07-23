
from PIL import Image, ImageDraw, ImageFont
import ast
import os
import argparse

import sys 
print(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_keypoint.get_node_io import NodeIO

def get_box_center_and_size(box_str):
    """
    从字符串格式的box中提取中心点和大小
    box_str: "[x1, y1, x2, y2]" 格式的字符串
    """
    box = ast.literal_eval(box_str)
    x1, y1, x2, y2 = box
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    width = x2 - x1
    height = y2 - y1
    return center_x, center_y, width, height

def get_keypoint_center(box):
    """
    从box坐标中计算关键点中心
    box: [x1, y1, x2, y2]
    """
    x1, y1, x2, y2 = box
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    return center_x, center_y

def normalize_coordinates(x, y, width, height, img_width, img_height):
    """
    将绝对坐标转换为归一化坐标
    """
    norm_x = x / img_width
    norm_y = y / img_height
    norm_width = width / img_width
    norm_height = height / img_height
    return norm_x, norm_y, norm_width, norm_height

def denormalize_coordinates(norm_x, norm_y, norm_width, norm_height, img_width, img_height):
    """
    将归一化坐标转换回绝对坐标
    """
    x = norm_x * img_width
    y = norm_y * img_height
    width = norm_width * img_width
    height = norm_height * img_height
    return x, y, width, height

def parse_yolo_pose_line(line):
    """
    解析YOLO pose格式的一行数据
    """
    parts = line.strip().split()
    class_id = int(parts[0])
    center_x = float(parts[1])
    center_y = float(parts[2])
    width = float(parts[3])
    height = float(parts[4])
    
    # 解析关键点
    keypoints = []
    for i in range(5, len(parts), 3):
        if i + 2 < len(parts):
            kp_x = float(parts[i])
            kp_y = float(parts[i + 1])
            visibility = int(parts[i + 2])
            keypoints.append((kp_x, kp_y, visibility))
    
    return class_id, center_x, center_y, width, height, keypoints

def visualize_yolo_pose_results(image_path, yolo_lines, save_path=None):
    """
    可视化YOLO pose格式的结果
    
    Args:
        image_path: 原始图片路径
        yolo_lines: YOLO pose格式的标签行列表
        save_path: 保存路径，如果为None则显示图片
    """
    # 打开图片
    image = Image.open(image_path)
    img_width, img_height = image.size
    draw = ImageDraw.Draw(image)
    
    # 尝试使用默认字体
    try:
        font = ImageFont.load_default()
    except:
        font = None
    
    # 定义颜色
    colors = {
        'node_box': 'blue',      # 节点框颜色
        'input_point': 'red',    # 输入关键点颜色 (visibility=0)
        'output_point': 'green', # 输出关键点颜色 (visibility=1)
        'text': 'white'
    }
    
    for line_idx, line in enumerate(yolo_lines):
        class_id, norm_center_x, norm_center_y, norm_width, norm_height, keypoints = parse_yolo_pose_line(line)
        
        # 反归一化节点框坐标
        center_x, center_y, width, height = denormalize_coordinates(
            norm_center_x, norm_center_y, norm_width, norm_height, img_width, img_height
        )
        
        # 计算节点框的边界
        x1 = int(center_x - width / 2)
        y1 = int(center_y - height / 2)
        x2 = int(center_x + width / 2)
        y2 = int(center_y + height / 2)
        
        # 绘制节点框
        draw.rectangle([x1, y1, x2, y2], outline=colors['node_box'], width=2)
        
        # 绘制节点编号
        if font:
            draw.text((x1, y1-20), f"Node {line_idx}", fill=colors['text'], font=font)
        else:
            draw.text((x1, y1-20), f"Node {line_idx}", fill=colors['text'])
        
        # 绘制关键点
        input_count = 0
        output_count = 0
        
        for kp_x, kp_y, visibility in keypoints:
            # 反归一化关键点坐标
            abs_kp_x = int(kp_x * img_width)
            abs_kp_y = int(kp_y * img_height)
            
            if visibility == 0:  # 输入关键点
                color = colors['input_point']
                input_count += 1
                label = f"I{input_count}"
            else:  # 输出关键点
                color = colors['output_point']
                output_count += 1
                label = f"O{output_count}"
            
            # 绘制关键点（小圆圈）
            radius = 5
            draw.ellipse([abs_kp_x-radius, abs_kp_y-radius, 
                         abs_kp_x+radius, abs_kp_y+radius], 
                        fill=color, outline='black', width=1)
            
            # 绘制关键点标签
            if font:
                draw.text((abs_kp_x+8, abs_kp_y-8), label, fill=color, font=font)
            else:
                draw.text((abs_kp_x+8, abs_kp_y-8), label, fill=color)
    
    # 添加图例
    legend_y = 10
    legend_items = [
        ("节点框", colors['node_box']),
        ("输入关键点", colors['input_point']),
        ("输出关键点", colors['output_point'])
    ]
    
    for i, (label, color) in enumerate(legend_items):
        y_pos = legend_y + i * 25
        # 绘制颜色示例
        draw.rectangle([10, y_pos, 30, y_pos+15], fill=color, outline='black')
        # 绘制标签文字
        if font:
            draw.text((35, y_pos), label, fill='black', font=font)
        else:
            draw.text((35, y_pos), label, fill='black')
    
    # 保存或显示图片
    if save_path:
        image.save(save_path)
        print(f"可视化结果已保存到: {save_path}")
    else:
        image.show()
    
    return image

def visualize_from_label_file(image_path, label_path, save_path=None):
    """
    从标签文件读取YOLO pose格式的数据并可视化
    
    Args:
        image_path: 图片路径
        label_path: 标签文件路径
        save_path: 保存路径，如果为None则显示图片
    """
    try:
        with open(label_path, 'r') as f:
            yolo_lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if not yolo_lines:
            print(f"标签文件 {label_path} 为空或不存在有效数据")
            return None
        
        return visualize_yolo_pose_results(image_path, yolo_lines, save_path)
    
    except FileNotFoundError:
        print(f"标签文件 {label_path} 不存在")
        return None
    except Exception as e:
        print(f"读取标签文件时出错: {e}")
        return None

def convert_to_yolo_pose_format(node_io_map, image_path, class_id=0, visibility=2):
    """
    将NodeIO的输出转换为YOLO pose训练集格式
    
    Args:
        node_io_map: NodeIO返回的节点IO映射字典
        image_path: 图片路径，用于获取图片尺寸
        class_id: 默认类别ID，默认为0
        visibility: 关键点可见性，默认为2（可见）
    
    Returns:
        lines: YOLO pose格式的字符串列表
    """
    # 获取图片尺寸
    with Image.open(image_path) as img:
        img_width, img_height = img.size
    
    lines = []
    
    for node_box_str, io_data in node_io_map.items():
        # 获取节点框的中心点和大小
        center_x, center_y, width, height = get_box_center_and_size(node_box_str)
        
        # 归一化节点框坐标
        norm_center_x, norm_center_y, norm_width, norm_height = normalize_coordinates(
            center_x, center_y, width, height, img_width, img_height
        )
        
        # 构建YOLO pose格式的行
        line_parts = [
            str(class_id),  # 类别ID
            f"{norm_center_x:.5f}",  # 归一化中心x
            f"{norm_center_y:.5f}",  # 归一化中心y
            f"{norm_width:.5f}",     # 归一化宽度
            f"{norm_height:.5f}"     # 归一化高度
        ]
        
        # 添加输入关键点 (visibility=0)
        for input_box in io_data.get("input", []):
            kp_x, kp_y = get_keypoint_center(input_box)
            norm_kp_x = kp_x / img_width
            norm_kp_y = kp_y / img_height
            line_parts.extend([f"{norm_kp_x:.5f}", f"{norm_kp_y:.5f}", "1"])
        
        # 添加输出关键点 (visibility=1)
        for output_box in io_data.get("output", []):
            kp_x, kp_y = get_keypoint_center(output_box)
            norm_kp_x = kp_x / img_width
            norm_kp_y = kp_y / img_height
            line_parts.extend([f"{norm_kp_x:.5f}", f"{norm_kp_y:.5f}", "2"])
        
        # 只有当节点有关键点时才添加到结果中
        if len(line_parts) > 5:  # 基本的5个参数之外还有关键点
            lines.append(" ".join(line_parts))
    
    return lines

def save_yolo_pose_labels(lines, output_path):
    """
    将YOLO pose格式的标签保存到文件
    """
    with open(output_path, 'w') as f:
        for line in lines:
            f.write(line + '\n')

def process_image_to_yolo_pose(image_path, output_dir=None, class_id=0, visualize=False, vis_save_path=None):
    """
    处理单张图片，生成YOLO pose格式的标签文件
    
    Args:
        image_path: 输入图片路径
        output_dir: 输出目录，如果为None则使用图片所在目录
        class_id: 类别ID，默认为0
        visualize: 是否生成可视化图片，默认为False
        vis_save_path: 可视化图片保存路径，如果为None则自动生成
    """
    # 初始化NodeIO
    node_io = NodeIO()
    
    # 获取节点IO数据
    results_io, results_node, node_io_map = node_io(image_path)
    
    # 转换为YOLO pose格式
    yolo_lines = convert_to_yolo_pose_format(node_io_map, image_path, class_id)
    
    # 确定输出路径
    if output_dir is None:
        output_dir = os.path.dirname(image_path)
    
    # 生成标签文件名
    image_name = os.path.splitext(os.path.basename(image_path))[0]
    label_path = os.path.join(output_dir, f"{image_name}.txt")
    
    # 保存标签文件
    save_yolo_pose_labels(yolo_lines, label_path)
    
    # 如果需要可视化
    if visualize and yolo_lines:
        if vis_save_path is None:
            vis_save_path = os.path.join(output_dir, f"{image_name}_visualized.jpg")
        
        # 确保可视化保存目录存在
        vis_dir = os.path.dirname(vis_save_path)
        if not os.path.exists(vis_dir):
            os.makedirs(vis_dir)
            
        visualize_yolo_pose_results(image_path, yolo_lines, vis_save_path)
    
    print(f"处理图片: {image_path}")
    print(f"生成标签: {label_path}")
    print(f"节点数量: {len(yolo_lines)}")
    if visualize and yolo_lines:
        print(f"可视化图片: {vis_save_path}")
    
    return yolo_lines, label_path

def batch_process_images(image_dir, output_dir, class_id=0, visualize=True, vis_output_dir=None):
    """
    批量处理图片目录，生成YOLO pose格式的标签文件
    
    Args:
        image_dir: 输入图片目录
        output_dir: 输出标签目录
        class_id: 类别ID，默认为0
        visualize: 是否生成可视化图片，默认为True
        vis_output_dir: 可视化图片输出目录，如果为None则使用output_dir
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if visualize:
        if vis_output_dir is None:
            vis_output_dir = output_dir
        if not os.path.exists(vis_output_dir):
            os.makedirs(vis_output_dir)
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}

    print(f"开始批量处理图片: {image_dir},len(os.listdir(image_dir))={len(os.listdir(image_dir))}")
    import tqdm
    for filename in tqdm.tqdm(os.listdir(image_dir)):
        if any(filename.lower().endswith(ext) for ext in image_extensions):
            image_path = os.path.join(image_dir, filename)
            try:
                # 生成可视化路径
                vis_save_path = None
                if visualize:
                    image_name = os.path.splitext(filename)[0]
                    vis_save_path = os.path.join(vis_output_dir, f"{image_name}_visualized.jpg")
                
                # 处理图片生成标签，包括可视化
                yolo_lines, label_path = process_image_to_yolo_pose(
                    image_path, output_dir, class_id, visualize, vis_save_path
                )
                    
            except Exception as e:
                print(f"处理图片 {filename} 时出错: {e}")
    
    print(f"\n批量处理完成!")
    print(f"标签文件保存在: {output_dir}")
    if visualize:
        print(f"可视化图片保存在: {vis_output_dir}")

def main():
    """
    主函数，处理命令行参数
    """
    parser = argparse.ArgumentParser(description='将NodeIO输出转换为YOLO pose训练集格式')
    
    # 必需参数
    parser.add_argument('--image', '-i', required=True, 
                       help='输入图片路径（单张图片）或图片目录路径（批量处理）')
    
    # 可选参数
    parser.add_argument('--output', '-o', default=None,
                       help='输出txt标签文件的目录路径，默认为输入图片所在目录')
    
    parser.add_argument('--visualize', '-v', action='store_true',
                       help='是否生成可视化图片')
    
    parser.add_argument('--vis_output', '-vo', default=None,
                       help='可视化图片保存路径，默认与标签文件同目录')
    
    parser.add_argument('--class_id', '-c', type=int, default=0,
                       help='类别ID，默认为0')
    
    parser.add_argument('--batch', '-b', action='store_true',
                       help='批量处理模式（处理目录中的所有图片）')
    
    args = parser.parse_args()
    
    # 检查输入路径是否存在
    if not os.path.exists(args.image):
        print(f"错误: 输入路径 {args.image} 不存在")
        return
    
    # 判断是批量处理还是单张图片处理
    if args.batch or os.path.isdir(args.image):
        # 批量处理
        if not os.path.isdir(args.image):
            print(f"错误: 批量处理模式需要输入目录路径，但 {args.image} 不是目录")
            return
        
        # 设置输出目录
        if args.output is None:
            output_dir = os.path.join(args.image, "labels")
        else:
            output_dir = args.output
        
        # 设置可视化输出目录
        vis_output_dir = args.vis_output
        if args.visualize and vis_output_dir is None:
            vis_output_dir = os.path.join(output_dir, "visualized")
        
        print(f"批量处理模式:")
        print(f"输入目录: {args.image}")
        print(f"标签输出目录: {output_dir}")
        if args.visualize:
            print(f"可视化输出目录: {vis_output_dir}")
        
        batch_process_images(args.image, output_dir, args.class_id, args.visualize, vis_output_dir)
        
    else:
        # 单张图片处理
        if not os.path.isfile(args.image):
            print(f"错误: {args.image} 不是有效的图片文件")
            return
        
        # 设置输出目录
        if args.output is None:
            output_dir = os.path.dirname(args.image)
        else:
            output_dir = args.output
        
        # 设置可视化路径
        vis_save_path = None
        if args.visualize:
            if args.vis_output is None:
                image_name = os.path.splitext(os.path.basename(args.image))[0]
                vis_save_path = os.path.join(output_dir, f"{image_name}_visualized.jpg")
            else:
                vis_save_path = args.vis_output
        
        print(f"单张图片处理模式:")
        print(f"输入图片: {args.image}")
        print(f"标签输出目录: {output_dir}")
        if args.visualize:
            print(f"可视化图片路径: {vis_save_path}")
        
        yolo_lines, label_path = process_image_to_yolo_pose(
            args.image, output_dir, args.class_id, args.visualize, vis_save_path
        )
        
        # 打印结果
        print(f"\n生成的YOLO pose格式标签:")
        for line in yolo_lines:
            print(line)

if __name__ == "__main__":
    # 如果有命令行参数则使用main函数，否则使用默认测试
    if len(sys.argv) > 1:
        main()
    else:
        # 默认测试代码
        print("使用默认测试模式...")
        print("使用 --help 查看命令行参数说明")
        print()
        
        # 测试单张图片
        image_path = "/data/home/libo/work/DataFactory/.cache/images/608_block_circuit_train_15k_0321_000858.jpg"
        
        # 处理单张图片（带可视化）
        yolo_lines, label_path = process_image_to_yolo_pose(image_path, visualize=True)
        
        # 打印结果
        print("\n生成的YOLO pose格式标签:")
        for line in yolo_lines:
            print(line)
        
        # 示例：从已有标签文件生成可视化
        print("\n示例：从标签文件生成可视化...")
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        label_vis_path = os.path.join(os.path.dirname(image_path), f"{image_name}_from_label.jpg")
        visualize_from_label_file(image_path, label_path, label_vis_path)
        print(f"从标签文件生成的可视化图片: {label_vis_path}")
        
        print("\n命令行使用示例:")
        print("# 处理单张图片并生成可视化")
        print("python get_keypoint_train_data.py -i /path/to/image.jpg -v")
        print("# 批量处理图片目录")
        print("python get_keypoint_train_data.py -i /path/to/images/ -o /path/to/labels/ -v -b")
        print("# 指定可视化输出路径")
        print("python get_keypoint_train_data.py -i /path/to/image.jpg -o /path/to/labels/ -v -vo /path/to/vis.jpg")