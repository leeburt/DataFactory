from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
import os
import glob
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import html

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

DEFAULT_JSON_DATA_FILE = '../../results/test_det_node_v2/model_analysis.json'
DEFAULT_IMAGE_ROOT_DIR = '../../input_images'

def get_json_data_file():
    """获取当前设置的JSON数据文件路径"""
    return session.get('json_data_file', DEFAULT_JSON_DATA_FILE)

def get_image_root_dir():
    """获取当前设置的图片根目录路径"""
    return session.get('image_root_dir', DEFAULT_IMAGE_ROOT_DIR)

def load_json_data():
    """加载JSON数据"""
    json_file = get_json_data_file()
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON文件时出错: {e}")
        return {}

def format_description(description):
    """格式化描述内容，如果是JSON则美化显示，否则原样显示"""
    if isinstance(description, dict):
        return json.dumps(description, indent=2, ensure_ascii=False)
    else:
        return str(description)

def escape_html_attr(text):
    """转义HTML属性中的特殊字符"""
    return html.escape(str(text), quote=True)

def get_image_list():
    """获取图像列表"""
    data = load_json_data()
    image_list = []
    
    for image_name, image_data in data.items():
        component_details = image_data.get('component_details', {})
        
        # 计算统计信息
        total_components = len(component_details)
        json_format_correct = sum(1 for detail in component_details.values() 
                                 if detail.get('warning') == 'JSON格式正确')
        io_matches = sum(1 for detail in component_details.values() 
                        if detail.get('io_num_match', False))
        
        image_list.append({
            'name': image_name,
            'total_components': total_components,
            'json_format_correct': json_format_correct,
            'io_matches': io_matches
        })
    
    return sorted(image_list, key=lambda x: x['name'])

def get_image_index(image_name):
    """获取图像在列表中的索引"""
    image_list = get_image_list()
    for i, image in enumerate(image_list):
        if image['name'] == image_name:
            return i
    return -1

def draw_boxes_on_image(image_path, component_details):
    """在图片上画出组件和IO的box"""
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            print(f"图像不存在: {image_path}")
            return None
        
        # 打开图像
        image = Image.open(image_path)
        
        # 如果是RGBA模式，转换为RGB
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        # 创建绘图对象
        draw = ImageDraw.Draw(image)
        
        # 尝试加载字体
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
        
        # 为每个组件画框
        for component_coords, detail_info in component_details.items():
            # 解析组件坐标
            coords = eval(component_coords)  # [x1, y1, x2, y2]
            x1, y1, x2, y2 = coords
            
            # 根据IO是否匹配设置组件颜色
            io_num_match = detail_info.get('io_num_match', False)
            component_color = 'blue' if io_num_match else 'goldenrod'

            # 画组件边框
            draw.rectangle([x1, y1, x2, y2], outline=component_color, width=3)
            
            # 获取组件名称
            description = detail_info.get('description', {})
            if isinstance(description, dict):
                component_name = description.get('component_name', '未知组件')
            else:
                component_name = '未知组件'
            
            # 在组件上方写组件名称
            name_x = x1
            name_y = max(0, y1 - 20)
            draw.text((name_x, name_y), component_name, fill=component_color, font=font)
            
            # 获取det_io_info
            det_io_info = detail_info.get('det_io_info', {})
            
            # 画输入端口（紫色）
            input_ports = det_io_info.get('input', [])
            for input_port in input_ports:
                if len(input_port) == 4:
                    ix1, iy1, ix2, iy2 = input_port
                    draw.rectangle([ix1, iy1, ix2, iy2], outline='purple', width=2)
                    # 在端口旁边标注"IN"
                    draw.text((ix1, iy1-15), "IN", fill='purple', font=font)
            
            # 画输出端口（青色）
            output_ports = det_io_info.get('output', [])
            for output_port in output_ports:
                if len(output_port) == 4:
                    ox1, oy1, ox2, oy2 = output_port
                    draw.rectangle([ox1, oy1, ox2, oy2], outline='cyan', width=2)
                    # 在端口旁边标注"OUT"
                    draw.text((ox1, oy1-15), "OUT", fill='cyan', font=font)
        
        # 将图像转换为base64编码
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return img_str
    
    except Exception as e:
        print(f"绘制图像时出错: {e}")
        return None

def create_image_html(image_name, image_data):
    """为单个图像创建HTML内容"""
    component_details = image_data.get('component_details', {})
    
    # 计算统计信息
    total_components = len(component_details)
    json_format_correct = sum(1 for detail in component_details.values() 
                             if detail.get('warning') == 'JSON格式正确')
    io_matches = sum(1 for detail in component_details.values() 
                    if detail.get('io_num_match', False))
    
    # 获取带标注的图片
    image_root_dir = get_image_root_dir()
    image_path = os.path.join(image_root_dir, image_name)
    annotated_image_base64 = draw_boxes_on_image(image_path, component_details)
    
    # 为带标注的图像创建HTML
    annotated_image_html = f'''
    <div class="image-display">
        <img src="data:image/png;base64,{annotated_image_base64}" alt="Annotated {image_name}" class="annotated-image" id="main-image">
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background-color: blue;"></div>
                <span>IO匹配组件</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: goldenrod;"></div>
                <span>IO未匹配组件</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: purple;"></div>
                <span>输入端口</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: cyan;"></div>
                <span>输出端口</span>
            </div>
        </div>
    </div>
    ''' if annotated_image_base64 else '<div class="image-display"><p>图片加载失败</p></div>'

    # 为每个组件创建HTML卡片
    components_html_list = []
    component_index = 0
    for component_coords, detail_info in component_details.items():
        component_index += 1
        description = detail_info.get('description', {})
        warning = detail_info.get('warning', '')
        io_num_match = detail_info.get('io_num_match', False)
        det_io_info = detail_info.get('det_io_info', {})
        current_label = detail_info.get('label', 'correct')
        
        if isinstance(description, dict):
            component_name = description.get('component_name', '未知组件')
        else:
            component_name = '未知组件'
        
        description_formatted = format_description(description)
        
        status_badges = []
        if warning == 'JSON格式正确':
            status_badges.append('<span class="badge badge-success">✓ JSON格式正确</span>')
        else:
            status_badges.append('<span class="badge badge-danger">✗ JSON格式错误</span>')
        
        if io_num_match:
            status_badges.append('<span class="badge badge-success">✓ IO端口匹配</span>')
        else:
            status_badges.append('<span class="badge badge-warning">⚠ IO端口不匹配</span>')
            
        det_inputs = det_io_info.get('input', [])
        det_outputs = det_io_info.get('output', [])
        
        status_icons = {'correct': '✓', 'incorrect': '✗', 'pending': '?'}
        status_texts = {'correct': '正确', 'incorrect': '错误', 'pending': '待确定'}
        current_status_icon = status_icons[current_label]
        current_status_text = status_texts[current_label]

        components_html_list.append(f"""
            <div class="component-card" data-coords="{escape_html_attr(component_coords)}" data-label="{current_label}" id="component-{component_index}">
                <button class="expand-btn" onclick="toggleComponent(this)" title="展开/收起">−</button>
                <div class="component-header">
                    <div>
                        <div class="component-name">🔧 {component_name}</div>
                        <div class="component-coords">{escape_html_attr(component_coords)}</div>
                        <div class="status-badges">{''.join(status_badges)}</div>
                    </div>
                </div>
                <div class="annotation-section">
                    <div class="annotation-header">
                        <div class="annotation-title">🏷️ 人工标注</div>
                        <div class="annotation-status">
                            <div class="status-icon {current_label}" id="status-icon-{component_index}">{current_status_icon}</div>
                            <span id="status-text-{component_index}">{current_status_text}</span>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <select class="annotation-select {current_label}" 
                                data-component-index="{component_index}"
                                data-coords="{escape_html_attr(component_coords)}"
                                onchange="updateAnnotation(this)">
                            <option value="correct" {'selected' if current_label == 'correct' else ''}>正确</option>
                            <option value="incorrect" {'selected' if current_label == 'incorrect' else ''}>错误</option>
                            <option value="pending" {'selected' if current_label == 'pending' else ''}>待确定</option>
                        </select>
                        <div class="save-indicator" id="save-indicator-{component_index}">已保存</div>
                    </div>
                </div>
                <div class="detail-section">
                    <div class="detail-title">📝 组件描述</div>
                    <div class="detail-content">{description_formatted}</div>
                </div>
                <div class="coordinates-grid">
                    <div class="coordinates-section">
                        <div class="coordinates-title">🎯 输入端口 ({len(det_inputs)})</div>
                        {''.join([f'<div class="coordinate-item input">[{coord[0]}, {coord[1]}, {coord[2]}, {coord[3]}]</div>' for coord in det_inputs])}
                    </div>
                    <div class="coordinates-section">
                        <div class="coordinates-title">🎯 输出端口 ({len(det_outputs)})</div>
                        {''.join([f'<div class="coordinate-item output">[{coord[0]}, {coord[1]}, {coord[2]}, {coord[3]}]</div>' for coord in det_outputs])}
                    </div>
                </div>
            </div>
        """)
    
    components_html = "".join(components_html_list)

    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{image_name} - 组件检测分析</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            overflow-x: hidden;
        }}
        
        .container {{
            max-width: 100vw;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2em;
            margin-bottom: 5px;
        }}
        
        .header p {{
            font-size: 1em;
            opacity: 0.9;
        }}
        
        .navigation {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .nav-btn {{
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: transform 0.2s ease;
        }}
        
        .nav-btn:hover {{
            transform: translateY(-2px);
        }}
        
        .nav-btn.disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}
        
        .main-content {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            height: calc(100vh - 200px);
            min-height: 600px;
        }}
        
        .left-panel {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            position: sticky;
            top: 20px;
            height: fit-content;
            max-height: calc(100vh - 220px);
        }}
        
        .right-panel {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow-y: auto;
            max-height: calc(100vh - 220px);
        }}
        
        .image-section {{
            text-align: center;
            margin-bottom: 20px;
        }}
        
        .image-title {{
            font-size: 1.5em;
            color: #2c3e50;
            font-weight: bold;
            margin-bottom: 15px;
        }}
        
        .image-display {{
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        
        .annotated-image {{
            max-width: 100%;
            height: auto;
            border: 2px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            cursor: crosshair;
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 10px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.9em;
        }}
        
        .legend-color {{
            width: 16px;
            height: 3px;
            border-radius: 2px;
        }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            font-size: 0.8em;
            opacity: 0.9;
        }}
        
        .components-list {{
            padding-right: 10px;
        }}
        
        .components-header {{
            font-size: 1.4em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        
        .component-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }}
        
        .component-card:hover {{
            background: #e3f2fd;
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}
        
        .component-card.highlighted {{
            background: #fff3e0;
            border-left-color: #ff9800;
            box-shadow: 0 4px 12px rgba(255, 152, 0, 0.3);
        }}
        
        .component-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}
        
        .component-name {{
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        
        .component-coords {{
            background: #e3f2fd;
            color: #1976d2;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-family: monospace;
        }}
        
        .status-badges {{
            display: flex;
            gap: 6px;
            margin-top: 8px;
            flex-wrap: wrap;
        }}
        
        .badge {{
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 0.7em;
            font-weight: bold;
        }}
        
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .detail-section {{
            margin-bottom: 15px;
        }}
        
        .detail-title {{
            font-weight: bold;
            color: #34495e;
            margin-bottom: 8px;
            font-size: 0.9em;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .detail-content {{
            background-color: white;
            padding: 12px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.8em;
            line-height: 1.4;
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #e9ecef;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .coordinates-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }}
        
        .coordinates-section {{
            background: white;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #e9ecef;
        }}
        
        .coordinates-title {{
            font-weight: bold;
            color: #495057;
            margin-bottom: 8px;
            font-size: 0.8em;
        }}
        
        .coordinate-item {{
            background: #f8f9fa;
            padding: 6px 8px;
            border-radius: 4px;
            margin-bottom: 4px;
            font-family: monospace;
            font-size: 0.75em;
            border: 1px solid #dee2e6;
        }}
        
        .coordinate-item.input {{
            border-left: 3px solid purple;
        }}
        
        .coordinate-item.output {{
            border-left: 3px solid cyan;
        }}
        
        .expand-btn {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            cursor: pointer;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .component-card.collapsed .detail-section,
        .component-card.collapsed .coordinates-grid {{
            display: none;
        }}
        
        /* 响应式设计 */
        @media (max-width: 1200px) {{
            .main-content {{
                grid-template-columns: 1fr;
                height: auto;
            }}
            
            .left-panel {{
                position: static;
                max-height: none;
                margin-bottom: 20px;
            }}
            
            .right-panel {{
                max-height: none;
            }}
            
            .coordinates-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 1.5em;
            }}
            
            .navigation {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .summary-stats {{
                grid-template-columns: 1fr;
                gap: 8px;
            }}
        }}
        
        /* 滚动条样式 */
        .right-panel::-webkit-scrollbar,
        .detail-content::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .right-panel::-webkit-scrollbar-track,
        .detail-content::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 3px;
        }}
        
        .right-panel::-webkit-scrollbar-thumb,
        .detail-content::-webkit-scrollbar-thumb {{
            background: #c1c1c1;
            border-radius: 3px;
        }}
        
        .right-panel::-webkit-scrollbar-thumb:hover,
        .detail-content::-webkit-scrollbar-thumb:hover {{
            background: #a8a8a8;
        }}
        
        /* 标注功能样式 */
        .annotation-section {{
            background: #f0f8ff;
            border: 1px solid #b3d9ff;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 15px;
        }}
        
        .annotation-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .annotation-title {{
            font-weight: bold;
            color: #1976d2;
            font-size: 0.9em;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .annotation-select {{
            padding: 6px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            font-size: 0.8em;
            cursor: pointer;
            transition: border-color 0.3s ease;
        }}
        
        .annotation-select:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
        }}
        
        .annotation-select.correct {{
            border-color: #28a745;
            background-color: #f8fff9;
        }}
        
        .annotation-select.incorrect {{
            border-color: #dc3545;
            background-color: #fff8f8;
        }}
        
        .annotation-select.pending {{
            border-color: #ffc107;
            background-color: #fffdf5;
        }}
        
        .annotation-status {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.8em;
        }}
        
        .status-icon {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: bold;
        }}
        
        .status-icon.correct {{
            background: #28a745;
            color: white;
        }}
        
        .status-icon.incorrect {{
            background: #dc3545;
            color: white;
        }}
        
        .status-icon.pending {{
            background: #ffc107;
            color: #333;
        }}
        
        .save-indicator {{
            opacity: 0;
            transition: opacity 0.3s ease;
            color: #28a745;
            font-size: 0.7em;
            font-weight: bold;
        }}
        
        .save-indicator.show {{
            opacity: 1;
        }}
        
        .annotation-stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 15px;
        }}
        
        .annotation-stat {{
            background: white;
            padding: 8px;
            border-radius: 6px;
            text-align: center;
            border: 1px solid #e9ecef;
        }}
        
        .annotation-stat-number {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 2px;
        }}
        
        .annotation-stat-label {{
            font-size: 0.7em;
            color: #666;
        }}
        
        .annotation-stat.correct .annotation-stat-number {{
            color: #28a745;
        }}
        
        .annotation-stat.incorrect .annotation-stat-number {{
            color: #dc3545;
        }}
        
        .annotation-stat.pending .annotation-stat-number {{
            color: #ffc107;
        }}
        
        .annotation-stat.total .annotation-stat-number {{
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 组件IO检测分析结果</h1>
            <p>图像: {image_name}</p>
        </div>
        
        <div class="navigation">
            <a href="/view_image/{image_name_no_ext}" class="nav-btn">← 上一个</a>
            <a href="/" class="nav-btn">🏠 返回首页</a>
            <a href="/view_image/{image_name_no_ext}" class="nav-btn">下一个 →</a>
        </div>
        
        <div class="main-content">
            <div class="left-panel">
                <div class="image-section">
                    <div class="image-title">📷 {image_name}</div>
                    {annotated_image_html}
                </div>
                
                <div class="summary-stats">
                    <div class="stat-card">
                        <div class="stat-number">{total_components}</div>
                        <div class="stat-label">检测组件</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{json_format_correct}</div>
                        <div class="stat-label">格式正确</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{io_matches}</div>
                        <div class="stat-label">IO匹配</div>
                    </div>
                </div>
                
                <!-- 标注统计区域 -->
                <div class="annotation-stats" id="annotation-stats">
                    <div class="annotation-stat correct">
                        <div class="annotation-stat-number" id="correct-count">0</div>
                        <div class="annotation-stat-label">正确</div>
                    </div>
                    <div class="annotation-stat incorrect">
                        <div class="annotation-stat-number" id="incorrect-count">0</div>
                        <div class="annotation-stat-label">错误</div>
                    </div>
                    <div class="annotation-stat pending">
                        <div class="annotation-stat-number" id="pending-count">0</div>
                        <div class="annotation-stat-label">待确定</div>
                    </div>
                    <div class="annotation-stat total">
                        <div class="annotation-stat-number" id="total-count">{total_components}</div>
                        <div class="annotation-stat-label">总计</div>
                    </div>
                </div>
            </div>
            
            <div class="right-panel">
                <div class="components-list">
                    <div class="components-header">🔧 组件详情列表 ({total_components}个)</div>
                    {components_html}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 全局变量
        const IMAGE_NAME = '{image_name}';
        
        // 简化的updateAnnotation函数 - 确保在全局作用域
        function updateAnnotation(selectElement) {{
            console.log('=== updateAnnotation被调用 ===');
            console.log('selectElement:', selectElement);
            console.log('selectElement.value:', selectElement.value);
            
            try {{
                const componentIndex = selectElement.getAttribute('data-component-index');
                const coords = selectElement.getAttribute('data-coords');
                const newLabel = selectElement.value;
                
                console.log('componentIndex:', componentIndex);
                console.log('coords:', coords);
                console.log('newLabel:', newLabel);
                
                // 更新UI状态
                updateComponentUI(componentIndex, newLabel);
                
                // 保存到服务器
                saveAnnotation(coords, newLabel, componentIndex);
                
            }} catch (error) {{
                console.error('updateAnnotation执行出错:', error);
                alert('updateAnnotation执行出错: ' + error.message);
            }}
        }}
        
        // 确保函数在window对象上也可用
        window.updateAnnotation = updateAnnotation;
        
        // 更新组件UI状态
        function updateComponentUI(componentIndex, label) {{
            try {{
                console.log('updateComponentUI被调用:', componentIndex, label);
                
                const card = document.getElementById('component-' + componentIndex);
                if (!card) {{
                    console.error('找不到组件卡片:', componentIndex);
                    return;
                }}
                
                const select = card.querySelector('.annotation-select');
                const statusIcon = document.getElementById('status-icon-' + componentIndex);
                const statusText = document.getElementById('status-text-' + componentIndex);
                
                // 更新选择框样式
                if (select) {{
                    select.className = 'annotation-select ' + label;
                }}
                
                // 更新状态图标
                const icons = {{'correct': '✓', 'incorrect': '✗', 'pending': '?'}};
                const texts = {{'correct': '正确', 'incorrect': '错误', 'pending': '待确定'}};
                
                if (statusIcon) {{
                    statusIcon.className = 'status-icon ' + label;
                    statusIcon.textContent = icons[label];
                }}
                
                if (statusText) {{
                    statusText.textContent = texts[label];
                }}
                
                // 更新卡片的data-label属性
                card.setAttribute('data-label', label);
                
            }} catch (error) {{
                console.error('updateComponentUI执行出错:', error);
            }}
        }}
        
        // 保存标注到服务器
        function saveAnnotation(coords, label, componentIndex) {{
            console.log('=== saveAnnotation被调用 ===');
            console.log('图像名称:', IMAGE_NAME);
            console.log('组件坐标:', coords);
            console.log('标注标签:', label);
            console.log('组件索引:', componentIndex);
            
            try {{
                const saveIndicator = document.getElementById('save-indicator-' + componentIndex);
                
                const requestData = {{
                    image_name: IMAGE_NAME,
                    component_coords: coords,
                    label: label
                }};
                
                console.log('发送的请求数据:', requestData);
                
                fetch('/save_annotation', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify(requestData)
                }})
                .then(response => {{
                    console.log('收到响应状态:', response.status);
                    if (!response.ok) {{
                        throw new Error('HTTP ' + response.status);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    console.log('收到响应数据:', data);
                    if (data.success) {{
                        console.log('保存成功');
                        
                        // 显示保存成功指示器
                        if (saveIndicator) {{
                            saveIndicator.classList.add('show');
                            setTimeout(() => {{
                                saveIndicator.classList.remove('show');
                            }}, 2000);
                        }}
                        
                        // 更新统计信息
                        updateAnnotationStats();
                    }} else {{
                        console.error('保存失败:', data.message);
                        alert('保存失败: ' + data.message);
                    }}
                }})
                .catch(error => {{
                    console.error('网络错误:', error);
                    alert('保存失败: 网络错误 - ' + error.message);
                }});
                
            }} catch (error) {{
                console.error('saveAnnotation执行出错:', error);
                alert('saveAnnotation执行出错: ' + error.message);
            }}
        }}
        
        // 更新标注统计信息
        function updateAnnotationStats() {{
            try {{
                const imageNameForStats = IMAGE_NAME.replace('.jpg', '');
                fetch('/get_annotation_stats/' + imageNameForStats)
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error('HTTP ' + response.status);
                    }}
                    return response.json();
                }})
                .then(stats => {{
                    const correctCount = document.getElementById('correct-count');
                    const incorrectCount = document.getElementById('incorrect-count');
                    const pendingCount = document.getElementById('pending-count');
                    const totalCount = document.getElementById('total-count');
                    
                    if (correctCount) correctCount.textContent = stats.correct;
                    if (incorrectCount) incorrectCount.textContent = stats.incorrect;
                    if (pendingCount) pendingCount.textContent = stats.pending;
                    if (totalCount) totalCount.textContent = stats.total;
                }})
                .catch(error => {{
                    console.error('更新统计信息出错:', error);
                }});
            }} catch (error) {{
                console.error('updateAnnotationStats执行出错:', error);
            }}
        }}
        
        // 展开/收起组件详情
        function toggleComponent(btn) {{
            const card = btn.closest('.component-card');
            if (card.classList.contains('collapsed')) {{
                card.classList.remove('collapsed');
                btn.textContent = '−';
            }} else {{
                card.classList.add('collapsed');
                btn.textContent = '+';
            }}
        }}
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('=== 页面加载完成 ===');
            console.log('IMAGE_NAME:', IMAGE_NAME);
            
            try {{
                // 验证所有下拉框
                const selects = document.querySelectorAll('.annotation-select');
                console.log('找到', selects.length, '个下拉框');
                
                selects.forEach((select, index) => {{
                    console.log('下拉框', index + 1 + ':', select);
                    console.log('  - data-component-index:', select.getAttribute('data-component-index'));
                    console.log('  - data-coords:', select.getAttribute('data-coords'));
                    console.log('  - onchange属性:', select.getAttribute('onchange'));
                    
                    // 手动添加事件监听器作为备份
                    select.addEventListener('change', function(e) {{
                        console.log('addEventListener change事件触发');
                        updateAnnotation(this);
                    }});
                }});
                
                // 自动选中第一个组件
                const firstCard = document.querySelector('.component-card');
                if (firstCard) {{
                    firstCard.click();
                }}
                
                // 加载标注统计信息
                updateAnnotationStats();
                
                console.log('初始化完成');
                
            }} catch (error) {{
                console.error('初始化出错:', error);
                alert('页面初始化出错: ' + error.message);
            }}
        }});
        
        // 简化的卡片点击事件
        document.addEventListener('click', function(e) {{
            if (e.target.classList.contains('component-card') || 
                e.target.closest('.component-card')) {{
                
                const card = e.target.classList.contains('component-card') ? 
                           e.target : e.target.closest('.component-card');
                
                // 移除其他卡片的高亮
                document.querySelectorAll('.component-card').forEach(c => c.classList.remove('highlighted'));
                
                // 高亮当前卡片
                card.classList.add('highlighted');
            }}
        }});
        
        // 测试函数 - 可以在控制台中调用
        window.testUpdateAnnotation = function() {{
            const firstSelect = document.querySelector('.annotation-select');
            if (firstSelect) {{
                console.log('测试updateAnnotation函数');
                updateAnnotation(firstSelect);
            }} else {{
                console.log('没有找到下拉框');
            }}
        }};
        
        console.log('所有JavaScript代码加载完成');
    </script>
</body>
</html>
    """

    # 填充模板
    return html_template.format(
        image_name=image_name,
        image_name_no_ext=image_name.replace('.jpg', ''),
        annotated_image_html=annotated_image_html,
        total_components=total_components,
        json_format_correct=json_format_correct,
        io_matches=io_matches,
        components_html=components_html,
    )

@app.route('/set_json_path', methods=['POST'])
def set_json_path():
    """设置JSON数据文件路径"""
    json_path = request.form.get('json_path', '').strip()
    if json_path:
        session['json_data_file'] = json_path
        return jsonify({'success': True, 'message': f'已设置文件路径: {json_path}'})
    else:
        return jsonify({'success': False, 'message': '请输入有效的文件路径'})

@app.route('/set_image_path', methods=['POST'])
def set_image_path():
    """设置图片根目录路径"""
    image_path = request.form.get('image_path', '').strip()
    if image_path:
        session['image_root_dir'] = image_path
        return jsonify({'success': True, 'message': f'已设置图片路径: {image_path}'})
    else:
        return jsonify({'success': False, 'message': '请输入有效的图片路径'})

@app.route('/reset_json_path')
def reset_json_path():
    """重置为默认JSON数据文件路径"""
    session.pop('json_data_file', None)
    return redirect(url_for('index'))

@app.route('/reset_image_path')
def reset_image_path():
    """重置为默认图片根目录路径"""
    session.pop('image_root_dir', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    """主页，显示所有图像的分析结果"""
    image_list = get_image_list()
    current_json_path = get_json_data_file()
    current_image_path = get_image_root_dir()
    
    # 创建简单的HTML模板
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>组件IO检测分析 - 主页</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .config-section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .config-item {{
            margin-bottom: 20px;
        }}
        
        .config-item:last-child {{
            margin-bottom: 0;
        }}
        
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .image-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease;
        }}
        
        .image-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }}
        
        .image-name {{
            font-size: 1.3em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }}
        
        .stat {{
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        
        .stat-number {{
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-label {{
            font-size: 0.8em;
            color: #666;
        }}
        
        .view-btn {{
            display: block;
            width: 100%;
            padding: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            text-align: center;
            transition: transform 0.2s ease;
        }}
        
        .view-btn:hover {{
            transform: translateY(-2px);
        }}
        
        .config-form {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .config-input {{
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        
        .config-btn {{
            padding: 10px 20px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }}
        
        .reset-btn {{
            padding: 10px 20px;
            background: #dc3545;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 组件IO检测分析系统</h1>
            <p>可视化组件IO检测和分析结果</p>
        </div>
        
        <div class="config-section">
            <h3>配置数据源</h3>
            
            <div class="config-item">
                <h4>JSON数据文件</h4>
                <p>当前数据文件: <code>{current_json_path}</code></p>
                <form class="config-form" id="json-form">
                    <input type="text" name="json_path" class="config-input" placeholder="输入JSON文件路径..." value="{current_json_path}">
                    <button type="submit" class="config-btn">设置路径</button>
                    <a href="/reset_json_path" class="reset-btn">重置默认</a>
                </form>
            </div>
            
            <div class="config-item">
                <h4>图片根目录</h4>
                <p>当前图片目录: <code>{current_image_path}</code></p>
                <form class="config-form" id="image-form">
                    <input type="text" name="image_path" class="config-input" placeholder="输入图片根目录路径..." value="{current_image_path}">
                    <button type="submit" class="config-btn">设置路径</button>
                    <a href="/reset_image_path" class="reset-btn">重置默认</a>
                </form>
            </div>
        </div>
        
        <div class="image-grid">
"""
    
    for image in image_list:
        html_template += f"""
            <div class="image-card">
                <div class="image-name">📷 {image['name']}</div>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-number">{image['total_components']}</div>
                        <div class="stat-label">检测组件</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{image['json_format_correct']}</div>
                        <div class="stat-label">格式正确</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{image['io_matches']}</div>
                        <div class="stat-label">IO匹配</div>
                    </div>
                </div>
                <a href="/view_image/{image['name'].replace('.jpg', '')}" class="view-btn">查看详情</a>
            </div>
"""
    
    html_template += """
        </div>
    </div>
    
    <script>
        // 处理JSON路径表单提交
        document.getElementById('json-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            fetch('/set_json_path', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    window.location.reload();
                } else {
                    alert('错误: ' + data.message);
                }
            })
            .catch(error => {
                alert('请求失败: ' + error);
            });
        });
        
        // 处理图片路径表单提交
        document.getElementById('image-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            fetch('/set_image_path', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    window.location.reload();
                } else {
                    alert('错误: ' + data.message);
                }
            })
            .catch(error => {
                alert('请求失败: ' + error);
            });
        });
    </script>
</body>
</html>
"""
    
    return html_template

@app.route('/view_image/<image_name>')
def view_image(image_name):
    """查看指定图像的分析结果"""
    # 添加.jpg扩展名
    if not image_name.endswith('.jpg'):
        image_name += '.jpg'
    
    data = load_json_data()
    if image_name not in data:
        return redirect(url_for('index'))
    
    image_data = data[image_name]
    image_list = get_image_list()
    current_index = get_image_index(image_name)
    
    # 获取上一个和下一个图像
    prev_image = image_list[current_index - 1] if current_index > 0 else None
    next_image = image_list[current_index + 1] if current_index < len(image_list) - 1 else None
    
    # 生成HTML内容
    html_content = create_image_html(image_name, image_data)
    
    # 更新导航链接
    if prev_image:
        html_content = html_content.replace(
            '<a href="/view_image/' + image_name.replace('.jpg', '') + '" class="nav-btn">← 上一个</a>',
            '<a href="/view_image/' + prev_image["name"].replace('.jpg', '') + '" class="nav-btn">← 上一个</a>'
        )
    else:
        html_content = html_content.replace(
            '<a href="/view_image/' + image_name.replace('.jpg', '') + '" class="nav-btn">← 上一个</a>',
            '<a href="#" class="nav-btn disabled">← 上一个</a>'
        )
    
    if next_image:
        html_content = html_content.replace(
            '<a href="/view_image/' + image_name.replace('.jpg', '') + '" class="nav-btn">下一个 →</a>',
            '<a href="/view_image/' + next_image["name"].replace('.jpg', '') + '" class="nav-btn">下一个 →</a>'
        )
    else:
        html_content = html_content.replace(
            '<a href="/view_image/' + image_name.replace('.jpg', '') + '" class="nav-btn">下一个 →</a>',
            '<a href="#" class="nav-btn disabled">下一个 →</a>'
        )
    
    return html_content

@app.route('/api/images')
def api_images():
    """API端点，返回图像列表"""
    image_list = get_image_list()
    return jsonify(image_list)

@app.route('/search')
def search():
    """搜索图像"""
    query = request.args.get('query', '').strip()
    if not query:
        return redirect(url_for('index'))
    
    image_list = get_image_list()
    results = []
    
    for image in image_list:
        if query.lower() in image['name'].lower():
            results.append(image)
    
    # 返回简化的搜索结果页面
    return redirect(url_for('index'))

@app.route('/save_annotation', methods=['POST'])
def save_annotation():
    """保存组件标注结果"""
    try:
        print("=== 开始保存标注 ===")
        data = request.get_json()
        print(f"接收到的数据: {data}")
        
        image_name = data.get('image_name')
        component_coords = data.get('component_coords')
        label = data.get('label')
        
        print(f"图像名称: {image_name}")
        print(f"组件坐标: {component_coords}")
        print(f"标注标签: {label}")
        
        if not all([image_name, component_coords, label]):
            print("参数不完整")
            return jsonify({'success': False, 'message': '参数不完整'})
        
        # 加载当前JSON数据
        json_file = get_json_data_file()
        print(f"JSON文件路径: {json_file}")
        
        json_data = load_json_data()
        print(f"加载的JSON数据键: {list(json_data.keys())}")
        
        if image_name not in json_data:
            print(f"图像不存在: {image_name}")
            return jsonify({'success': False, 'message': '图像不存在'})
        
        component_details = json_data[image_name].get('component_details', {})
        print(f"组件详情键: {list(component_details.keys())}")
        
        if component_coords not in component_details:
            print(f"组件不存在: {component_coords}")
            return jsonify({'success': False, 'message': '组件不存在'})
        
        # 更新标注结果
        print(f"更新前的组件数据: {component_details[component_coords]}")
        component_details[component_coords]['label'] = label
        print(f"更新后的组件数据: {component_details[component_coords]}")
        
        # 保存到文件
        print(f"准备保存到文件: {json_file}")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print("文件保存成功")
        
        return jsonify({'success': True, 'message': f'已保存标注: {label}'})
        
    except Exception as e:
        print(f"保存失败，错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})

@app.route('/get_annotation_stats/<image_name>')
def get_annotation_stats(image_name):
    """获取图像的标注统计信息"""
    if not image_name.endswith('.jpg'):
        image_name += '.jpg'
    
    data = load_json_data()
    if image_name not in data:
        return jsonify({'error': '图像不存在'})
    
    component_details = data[image_name].get('component_details', {})
    stats = {
        'correct': 0,
        'incorrect': 0,
        'pending': 0,
        'total': len(component_details)
    }
    
    for detail in component_details.values():
        label = detail.get('label', 'correct')  # 默认为正确
        if label == 'correct':
            stats['correct'] += 1
        elif label == 'incorrect':
            stats['incorrect'] += 1
        else:
            stats['pending'] += 1
    
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True, host='192.168.99.119', port=5001) 