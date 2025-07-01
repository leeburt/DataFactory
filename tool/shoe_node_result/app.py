from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
import os
import glob
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io

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
            
            # 画组件边框（蓝色）
            draw.rectangle([x1, y1, x2, y2], outline='blue', width=3)
            
            # 获取组件名称
            description = detail_info.get('description', {})
            if isinstance(description, dict):
                component_name = description.get('component_name', '未知组件')
            else:
                component_name = '未知组件'
            
            # 在组件上方写组件名称
            name_x = x1
            name_y = max(0, y1 - 20)
            draw.text((name_x, name_y), component_name, fill='blue', font=font)
            
            # 获取det_io_info
            det_io_info = detail_info.get('det_io_info', {})
            
            # 画输入端口（绿色）
            input_ports = det_io_info.get('input', [])
            for input_port in input_ports:
                if len(input_port) == 4:
                    ix1, iy1, ix2, iy2 = input_port
                    draw.rectangle([ix1, iy1, ix2, iy2], outline='green', width=2)
                    # 在端口旁边标注"IN"
                    draw.text((ix1, iy1-15), "IN", fill='green', font=font)
            
            # 画输出端口（红色）
            output_ports = det_io_info.get('output', [])
            for output_port in output_ports:
                if len(output_port) == 4:
                    ox1, oy1, ox2, oy2 = output_port
                    draw.rectangle([ox1, oy1, ox2, oy2], outline='red', width=2)
                    # 在端口旁边标注"OUT"
                    draw.text((ox1, oy1-15), "OUT", fill='red', font=font)
        
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
    
    html_content = f"""
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
        }}
        
        .container {{
            max-width: 1400px;
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
        
        .image-section {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .image-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }}
        
        .image-title {{
            font-size: 1.8em;
            color: #2c3e50;
            font-weight: bold;
        }}
        
        .image-display {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        
        .annotated-image {{
            max-width: 100%;
            height: auto;
            border: 2px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 3px;
            border-radius: 2px;
        }}
        
        .legend-blue {{ background-color: blue; }}
        .legend-green {{ background-color: green; }}
        .legend-red {{ background-color: red; }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .components-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }}
        
        .component-card {{
            background: white;
            border-radius: 8px;
            padding: 25px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #3498db;
            transition: transform 0.2s ease;
        }}
        
        .component-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }}
        
        .component-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        
        .component-name {{
            font-size: 1.4em;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .component-coords {{
            background: #e3f2fd;
            color: #1976d2;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-family: monospace;
        }}
        
        .status-badges {{
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }}
        
        .badge {{
            padding: 4px 8px;
            border-radius: 12px;
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
            margin-bottom: 20px;
        }}
        
        .detail-title {{
            font-weight: bold;
            color: #34495e;
            margin-bottom: 10px;
            font-size: 1em;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .detail-content {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.5;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e9ecef;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .coordinates-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }}
        
        .coordinates-section {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        
        .coordinates-title {{
            font-weight: bold;
            color: #495057;
            margin-bottom: 10px;
            font-size: 0.9em;
        }}
        
        .coordinate-item {{
            background: white;
            padding: 8px;
            border-radius: 4px;
            margin-bottom: 5px;
            font-family: monospace;
            font-size: 0.8em;
            border: 1px solid #dee2e6;
        }}
        
        .coordinate-item.input {{
            border-left: 4px solid green;
        }}
        
        .coordinate-item.output {{
            border-left: 4px solid red;
        }}
        
        @media (max-width: 1024px) {{
            .components-grid {{
                grid-template-columns: 1fr;
            }}
            
            .coordinates-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media (max-width: 768px) {{
            .image-header {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
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
            <a href="/view_image/{image_name.replace('.jpg', '')}" class="nav-btn">← 上一个</a>
            <a href="/" class="nav-btn">🏠 返回首页</a>
            <a href="/view_image/{image_name.replace('.jpg', '')}" class="nav-btn">下一个 →</a>
        </div>
        
        <div class="image-section">
            <div class="image-header">
                <div class="image-title">📷 {image_name}</div>
            </div>
            
            {f'''
            <div class="image-display">
                <img src="data:image/png;base64,{annotated_image_base64}" alt="Annotated {image_name}" class="annotated-image">
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color legend-blue"></div>
                        <span>组件边框</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color legend-green"></div>
                        <span>输入端口</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color legend-red"></div>
                        <span>输出端口</span>
                    </div>
                </div>
            </div>
            ''' if annotated_image_base64 else '<div class="image-display"><p>图片加载失败</p></div>'}
            
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{total_components}</div>
                    <div class="stat-label">检测到的组件</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{json_format_correct}</div>
                    <div class="stat-label">JSON格式正确</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{io_matches}</div>
                    <div class="stat-label">IO匹配</div>
                </div>
            </div>
            
            <div class="components-grid">
"""
    
    # 遍历每个组件
    for component_coords, detail_info in component_details.items():
        # 获取组件详细信息
        description = detail_info.get('description', {})
        warning = detail_info.get('warning', '')
        io_num_match = detail_info.get('io_num_match', False)
        det_io_info = detail_info.get('det_io_info', {})
        
        # 获取组件名称
        if isinstance(description, dict):
            component_name = description.get('component_name', '未知组件')
        else:
            component_name = '未知组件'
        
        # 格式化描述信息
        description_formatted = format_description(description)
        
        # 确定状态徽章
        status_badges = []
        if warning == 'JSON格式正确':
            status_badges.append('<span class="badge badge-success">✓ JSON格式正确</span>')
        else:
            status_badges.append('<span class="badge badge-danger">✗ JSON格式错误</span>')
        
        if io_num_match:
            status_badges.append('<span class="badge badge-success">✓ IO端口匹配</span>')
        else:
            status_badges.append('<span class="badge badge-warning">⚠ IO端口不匹配</span>')
        
        # 获取坐标信息（只显示det_io_info）
        det_inputs = det_io_info.get('input', [])
        det_outputs = det_io_info.get('output', [])
        
        html_content += f"""
            <div class="component-card">
                <div class="component-header">
                    <div>
                        <div class="component-name">🔧 {component_name}</div>
                        <div class="component-coords">{component_coords}</div>
                        <div class="status-badges">
                            {''.join(status_badges)}
                        </div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <div class="detail-title">
                        📝 组件描述
                    </div>
                    <div class="detail-content">{description_formatted}</div>
                </div>
                
                <div class="coordinates-grid">
                    <div class="coordinates-section">
                        <div class="coordinates-title">🎯 检测的输入端口 ({len(det_inputs)})</div>
                        {''.join([f'<div class="coordinate-item input">[{coord[0]}, {coord[1]}, {coord[2]}, {coord[3]}]</div>' for coord in det_inputs])}
                    </div>
                    <div class="coordinates-section">
                        <div class="coordinates-title">🎯 检测的输出端口 ({len(det_outputs)})</div>
                        {''.join([f'<div class="coordinate-item output">[{coord[0]}, {coord[1]}, {coord[2]}, {coord[3]}]</div>' for coord in det_outputs])}
                    </div>
                </div>
            </div>
"""
    
    html_content += """
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    return html_content

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

if __name__ == '__main__':
    app.run(debug=True, host='192.168.99.119', port=5001) 