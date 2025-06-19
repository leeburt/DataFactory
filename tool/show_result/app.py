from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
import glob
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 添加session密钥

DEFAULT_JSON_DATA_FILE = '../../results/component_consistency_results.json'

def get_json_data_file():
    """获取当前设置的JSON数据文件路径"""
    return session.get('json_data_file', DEFAULT_JSON_DATA_FILE)

def load_json_data():
    """加载JSON数据"""
    json_file = get_json_data_file()
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON文件时出错: {e}")
        return {}

def is_valid_json(text):
    """检查文本是否为有效的JSON格式"""
    if not text or text.strip() == '':
        return False
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        return False

def format_description(description):
    """格式化描述内容，如果是JSON则美化显示，否则原样显示"""
    if is_valid_json(description):
        try:
            parsed = json.loads(description)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except:
            return description
    else:
        return description

def get_image_list():
    """获取图像列表"""
    data = load_json_data()
    image_list = []
    
    for image_name, image_data in data.items():
        total_eval = image_data.get('total_eval_result', {})
        overall_score = total_eval.get('overall_score', 0)
        component_count = total_eval.get('component_count', 0)
        consistent_count = total_eval.get('consistent_count', 0)
        
        image_list.append({
            'name': image_name,
            'overall_score': overall_score,
            'component_count': component_count,
            'consistent_count': consistent_count,
            'html_file': f"{image_name.replace('.jpg', '')}_consistency.html"
        })
    
    return sorted(image_list, key=lambda x: x['name'])

def get_image_index(image_name):
    """获取图像在列表中的索引"""
    image_list = get_image_list()
    for i, image in enumerate(image_list):
        if image['name'] == image_name:
            return i
    return -1

def create_image_html(image_name, image_data):
    """为单个图像创建HTML内容"""
    components = image_data.get('components', [])
    component_details = image_data.get('component_details', {})
    total_eval = image_data.get('total_eval_result', {})
    
    # 计算总体统计
    overall_score = total_eval.get('overall_score', 0)
    component_count = total_eval.get('component_count', 0)
    consistent_count = total_eval.get('consistent_count', 0)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{image_name} - 组件一致性分析</title>
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
        
        .overall-score {{
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .components-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
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
        }}
        
        .component-name {{
            font-size: 1.4em;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .consistency-score {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1em;
        }}
        
        .score-100 {{
            background-color: #d4edda;
            color: #155724;
        }}
        
        .score-95 {{
            background-color: #fff3cd;
            color: #856404;
        }}
        
        .score-90 {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        
        .component-details {{
            margin-top: 20px;
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
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #e9ecef;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .json-content {{
            background-color: #f8f9fa;
            color: #333;
        }}
        
        .text-content {{
            background-color: #fff;
            color: #666;
            font-style: italic;
        }}
        
        .reasoning {{
            background-color: #e8f4fd;
            border-left: 4px solid #3498db;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        
        .inconsistencies {{
            background-color: #fff5f5;
            border-left: 4px solid #e53e3e;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        
        .inconsistencies-title {{
            font-weight: bold;
            color: #c53030;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .inconsistency-item {{
            background-color: #fed7d7;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid #e53e3e;
        }}
        
        .inconsistency-item:last-child {{
            margin-bottom: 0;
        }}
        
        .inconsistency-item::before {{
            content: "⚠️ ";
            margin-right: 5px;
        }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
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
        
        .format-badge {{
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.7em;
            font-weight: bold;
        }}
        
        @media (max-width: 1024px) {{
            .components-grid {{
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
            <h1>🔍 组件一致性分析结果</h1>
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
                <div class="overall-score">总体一致性: {overall_score:.1f}%</div>
            </div>
            
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{component_count}</div>
                    <div class="stat-label">总组件数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{consistent_count}</div>
                    <div class="stat-label">一致组件数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{consistent_count}/{component_count}</div>
                    <div class="stat-label">一致性比例</div>
                </div>
            </div>
            
            <div class="components-grid">
"""
    
    # 遍历每个组件
    for component_name in components:
        if component_name in component_details:
            component_data = component_details[component_name]
            eval_result = component_data.get('eval_result', {})
            
            consistency_score = eval_result.get('consistency_score', 0)
            is_consistent = eval_result.get('is_consistent', False)
            reasoning = eval_result.get('reasoning', '')
            inconsistencies = eval_result.get('inconsistencies', [])
            better_model = eval_result.get('better_model', '')
            
            # 获取模型描述并格式化
            # 动态获取模型名称，排除eval_result键
            model_names = [key for key in component_data.keys() if key != 'eval_result']
            
            # 确保至少有两个模型
            if len(model_names) >= 2:
                model1_name = model_names[0]
                model2_name = model_names[1]
                model1_desc = component_data.get(model1_name, {}).get('description', 'N/A')
                model2_desc = component_data.get(model2_name, {}).get('description', 'N/A')
            else:
                # 如果模型数量不足，使用默认值
                model1_name = "模型1"
                model2_name = "模型2"
                model1_desc = 'N/A'
                model2_desc = 'N/A'
            
            model1_formatted = format_description(model1_desc)
            model2_formatted = format_description(model2_desc)
            
            model1_is_json = is_valid_json(model1_desc)
            model2_is_json = is_valid_json(model2_desc)
            
            # 确定分数样式
            if consistency_score == 100:
                score_class = 'score-100'
            elif consistency_score >= 95:
                score_class = 'score-95'
            else:
                score_class = 'score-90'
            
            html_content += f"""
            <div class="component-card">
                <div class="component-header">
                    <div class="component-name">🔧 {component_name}</div>
                    <div class="consistency-score {score_class}">{consistency_score}%</div>
                </div>
                
                <div class="component-details">
                    <div class="detail-section">
                        <div class="detail-title">
                            🤖 {model1_name}
                            <span class="format-badge">{'JSON' if model1_is_json else 'TEXT'}</span>
                        </div>
                        <div class="detail-content {'json-content' if model1_is_json else 'text-content'}">{model1_formatted}</div>
                    </div>
                    
                    <div class="detail-section">
                        <div class="detail-title">
                            🤖 {model2_name}
                            <span class="format-badge">{'JSON' if model2_is_json else 'TEXT'}</span>
                        </div>
                        <div class="detail-content {'json-content' if model2_is_json else 'text-content'}">{model2_formatted}</div>
                    </div>
                    
                    {f'''
                    <div class="better-model">
                        <div class="better-model-title">
                            🏆 更佳模型: {better_model}
                        </div>
                    </div>
                    ''' if better_model else ''}
                    
                    <div class="reasoning">
                        <strong>一致性分析:</strong> {reasoning}
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

@app.route('/reset_json_path')
def reset_json_path():
    """重置为默认JSON数据文件路径"""
    session.pop('json_data_file', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    """主页，显示所有图像的分析结果"""
    image_list = get_image_list()
    current_json_path = get_json_data_file()
    return render_template('index.html', images=image_list, current_json_path=current_json_path)

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
    
    # 更新导航链接 - 修复替换逻辑
    # 替换第一个链接（上一个按钮）
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
    
    # 替换第三个链接（下一个按钮）
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
    
    return render_template('index.html', images=results, search_query=query)

if __name__ == '__main__':
    app.run(debug=True, host='192.168.99.119', port=5001) 