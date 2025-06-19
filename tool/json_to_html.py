#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON到HTML可视化转换器
将component_consistency_results.json转换为HTML格式的可视化结果
"""

import json
import os
from datetime import datetime

def load_json_data(json_file_path):
    """加载JSON数据"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON文件时出错: {e}")
        return None

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

def create_html_content(data):
    """创建HTML内容"""
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>组件一致性分析结果</title>
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
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #e9ecef;
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
        
        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            font-size: 0.9em;
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
            <p>多模型组件识别一致性评估报告</p>
        </div>
"""
    
    # 遍历每个图像的结果
    for image_name, image_data in data.items():
        components = image_data.get('components', [])
        component_details = image_data.get('component_details', {})
        total_eval = image_data.get('total_eval_result', {})
        
        # 计算总体统计
        overall_score = total_eval.get('overall_score', 0)
        component_count = total_eval.get('component_count', 0)
        consistent_count = total_eval.get('consistent_count', 0)
        
        html_content += f"""
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
                
                # 获取模型描述并格式化
                model1_desc = component_data.get('Qwen2.5-VL-32B-Instruct', {}).get('description', 'N/A')
                model2_desc = component_data.get('Qwen2.5-VL-32B-Instruct_2', {}).get('description', 'N/A')
                
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
                                🤖 模型1描述
                                <span class="format-badge">{'JSON' if model1_is_json else 'TEXT'}</span>
                            </div>
                            <div class="detail-content {'json-content' if model1_is_json else 'text-content'}">{model1_formatted}</div>
                        </div>
                        
                        <div class="detail-section">
                            <div class="detail-title">
                                🤖 模型2描述
                                <span class="format-badge">{'JSON' if model2_is_json else 'TEXT'}</span>
                            </div>
                            <div class="detail-content {'json-content' if model2_is_json else 'text-content'}">{model2_formatted}</div>
                        </div>
                        
                        <div class="reasoning">
                            <strong>一致性分析:</strong> {reasoning}
                        </div>
                    </div>
                </div>
"""
        
        html_content += """
            </div>
        </div>
"""
    
    html_content += f"""
        <div class="timestamp">
            生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
    
    return html_content

def save_html_file(html_content, output_path):
    """保存HTML文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML文件已保存到: {output_path}")
        return True
    except Exception as e:
        print(f"保存HTML文件时出错: {e}")
        return False

def main():
    """主函数"""
    # 文件路径
    json_file = '../../results/component_consistency_results.json'
    output_dir = '../../.cache/results'
    output_file = os.path.join(output_dir, 'component_consistency_visualization.html')
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载JSON数据
    print("正在加载JSON数据...")
    data = load_json_data(json_file)
    
    if data is None:
        print("无法加载JSON数据，程序退出")
        return
    
    print(f"成功加载数据，包含 {len(data)} 个图像的分析结果")
    
    # 创建HTML内容
    print("正在生成HTML内容...")
    html_content = create_html_content(data)
    
    # 保存HTML文件
    print("正在保存HTML文件...")
    if save_html_file(html_content, output_file):
        print("✅ 转换完成！")
        print(f"📁 输出文件: {output_file}")
    else:
        print("❌ 转换失败")

if __name__ == "__main__":
    main() 