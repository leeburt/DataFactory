#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from convert_node_connection import process_json_file

def test_with_sample_data():
    """使用示例数据测试脚本功能"""
    
    # 创建测试数据
    test_data = {
        "620_block_circuit_train_15k_0321_000858.jpg": {
            "components": {
                "[467, 130, 665, 213]": {
                    "input": [
                        [653, 166, 679, 186]
                    ],
                    "output": [
                        [462, 163, 481, 180]
                    ]
                },
                "[303, 130, 411, 212]": {
                    "input": [
                        [400, 164, 423, 182]
                    ],
                    "output": [
                        [297, 168, 315, 184]
                    ]
                },
                "[318, 18, 425, 100]": {
                    "input": [
                        [306, 48, 328, 67]
                    ],
                    "output": [
                        [413, 50, 430, 67]
                    ]
                },
                "[699, 18, 806, 100]": {
                    "input": [
                        [683, 49, 707, 68]
                    ],
                    "output": [
                        [795, 49, 812, 66]
                    ]
                },
                "[508, 18, 615, 100]": {
                    "input": [
                        [493, 49, 517, 68]
                    ],
                    "output": [
                        [602, 49, 620, 67]
                    ]
                },
                "[165, 42, 199, 75]": {
                    "input": [
                        [151, 49, 171, 65],
                        [173, 68, 188, 87]
                    ],
                    "output": [
                        [192, 53, 204, 64]
                    ]
                }
            },
            "component_details": {
                "[508, 18, 615, 100]": {
                    "description": {
                        "component_name": "D/A",
                        "box": "(508, 18, 615, 100)",
                        "connections": {
                            "input": [
                                {
                                    "name": "PID",
                                    "box": "(320, 18, 430, 100)",
                                    "visual_position": "(493, 49, 517, 68)"
                                }
                            ],
                            "output": [
                                {
                                    "name": "System",
                                    "box": "(674, 17, 784, 100)",
                                    "visual_position": "(602, 49, 620, 67)"
                                }
                            ],
                            "bidirectional": []
                        }
                    }
                },
                "[467, 130, 665, 213]": {
                    "description": {
                        "component_name": "Detection",
                        "box": "(467, 130, 665, 213)",
                        "connections": {
                            "input": [
                                {
                                    "name": "System",
                                    "box": "(669, 16, 779, 100)",
                                    "visual_position": "(653, 166, 679, 186)"
                                }
                            ],
                            "output": [
                                {
                                    "name": "A/D",
                                    "box": "(304, 131, 411, 212)",
                                    "visual_position": "(462, 163, 481, 180)"
                                }
                            ],
                            "bidirectional": []
                        }
                    }
                },
                "[303, 130, 411, 212]": {
                    "description": {
                        "component_name": "A/D",
                        "box": "(303, 130, 411, 212)",
                        "connections": {
                            "input": [
                                {
                                    "name": "Detection",
                                    "box": "(439, 130, 607, 212)",
                                    "visual_position": "(400, 164, 423, 182)"
                                }
                            ],
                            "output": [
                                {
                                    "name": "Summing junction",
                                    "box": "(162, 40, 199, 77)",
                                    "visual_position": "(297, 168, 315, 184)"
                                }
                            ],
                            "bidirectional": []
                        }
                    }
                },
                "[318, 18, 425, 100]": {
                    "description": {
                        "component_name": "PID",
                        "box": "(318, 18, 425, 100)",
                        "connections": {
                            "input": [
                                {
                                    "name": "Summing junction",
                                    "box": "(162, 40, 198, 76)",
                                    "visual_position": "(306, 48, 328, 67)"
                                }
                            ],
                            "output": [
                                {
                                    "name": "D/A",
                                    "box": "(479, 17, 587, 100)",
                                    "visual_position": "(413, 50, 430, 67)"
                                }
                            ],
                            "bidirectional": []
                        }
                    }
                },
                "[699, 18, 806, 100]": {
                    "description": {
                        "component_name": "System",
                        "box": "(699, 18, 806, 100)",
                        "connections": {
                            "input": [
                                {
                                    "name": "D/A",
                                    "box": "(510, 17, 616, 100)",
                                    "visual_position": "(683, 49, 707, 68)"
                                }
                            ],
                            "output": [
                                {
                                    "name": "Detection",
                                    "box": "(439, 158, 635, 242)",
                                    "visual_position": "(795, 49, 812, 66)"
                                },
                                {
                                    "name": "Summing junction",
                                    "box": "(162, 40, 199, 77)"
                                }
                            ],
                            "bidirectional": []
                        }
                    }
                },
                "[165, 42, 199, 75]": {
                    "description": {
                        "component_name": "Summing junction",
                        "box": "(165, 42, 199, 75)",
                        "connections": {
                            "input": [
                                {
                                    "name": "r",
                                    "box": "()",
                                    "visual_position": "(151, 49, 171, 65)"
                                },
                                {
                                    "name": "A/D",
                                    "box": "(305, 131, 413, 242)",
                                    "visual_position": "(173, 68, 188, 87)"
                                }
                            ],
                            "output": [
                                {
                                    "name": "PID",
                                    "box": "(292, 18, 401, 100)",
                                    "visual_position": "(192, 53, 204, 64)"
                                }
                            ],
                            "bidirectional": []
                        }
                    }
                }
            }
        }
    }
    
    # 保存测试数据
    test_input_file = "test_input.json"
    test_output_file = "test_output.json"
    
    with open(test_input_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print("测试数据已创建，开始处理...")
    
    # 处理数据
    try:
        process_json_file(test_input_file, test_output_file)
        
        # 读取处理后的数据
        with open(test_output_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
        
        # 显示结果
        print("\n=== 处理结果 ===")
        image_data = result_data["620_block_circuit_train_15k_0321_000858.jpg"]
        
        print("\n1. Components中添加的名字:")
        for comp_key, comp_value in image_data["components"].items():
            print(f"  {comp_key}: {comp_value.get('name', 'Unknown')}")
        
        print("\n2. Component_details中的连接映射结果:")
        for detail_key, detail_value in image_data["component_details"].items():
            comp_name = detail_value["description"]["component_name"]
            print(f"\n  组件: {comp_name} ({detail_key})")
            
            connections = detail_value["description"]["connections"]
            
            # 显示所有类型的连接
            for conn_type in ['input', 'output', 'bidirectional']:
                if conn_type in connections and connections[conn_type]:
                    print(f"    {conn_type}连接:")
                    for i, conn in enumerate(connections[conn_type]):
                        if conn:  # 如果连接不为空
                            mapped_name = conn.get('name', '未知')
                            mapped_box = conn.get('box', '未映射')
                            print(f"      [{i}] {mapped_name} -> {mapped_box}")
                        else:
                            print(f"      [{i}] 未映射")
        
        print(f"\n完整结果已保存到 {test_output_file}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试文件
        if os.path.exists(test_input_file):
            os.remove(test_input_file)
        print(f"测试文件 {test_input_file} 已清理")

if __name__ == "__main__":
    test_with_sample_data() 