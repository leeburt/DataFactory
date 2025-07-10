import os
import asyncio
import json
import traceback
from src.config import Config
from node_connections.get_node_info_from_det import ComponentAnalyzer
from node_connections.get_node_info_from_det_qwen import ComponentAnalyzer as ComponentAnalyzerQwen
from node_connections.get_node_info_from_det_v2 import ComponentAnalyzer as ComponentAnalyzerV2
from src.utils import parse_args, create_config_from_args
from config.prompts_node import (COMPONENT_IO_PROMPT_MODEL,COMPONENT_IO_PROMPT_MODEL_QWEN,COMPONENT_NAME_PROMPT,COMPONENT_IO_PROMPT_MODE_WITH_BOX)



def get_prompts(config: Config):
    prompts = {
        "COMPONENT_IO_PROMPT_MODEL": COMPONENT_IO_PROMPT_MODEL,
        "COMPONENT_IO_PROMPT_MODEL_QWEN": COMPONENT_IO_PROMPT_MODEL_QWEN,
        "COMPONENT_NAME_PROMPT": COMPONENT_NAME_PROMPT,
        "COMPONENT_IO_PROMPT_MODE_WITH_BOX": COMPONENT_IO_PROMPT_MODE_WITH_BOX
    }
    config.prompts = prompts
    return config

async def main():
    """主程序入口"""
    import time 
    st = time.time()
    print("电路图两步评估工具")
    print("=" * 50)
    
    # 解析命令行参数并创建配置
    args = parse_args()
    config = create_config_from_args(args)
    config = get_prompts(config)
    
    print("配置信息:")
    print(f"- 图像目录: {config.image_root_dir}")
    print(f"- 提示词文件: {config.prompts_path}")
    print(f"- 输出目录: {config.output_dir}")
    print(f"- 并发工作线程: {config.num_workers}")
    print(f"- 模型: {config.model1_model}")
    print("=" * 50)
    
    try:
        # 第一步：组件识别和IO分析
        print("\n第一步：组件识别和IO分析")
        print("-" * 50)
        print(config.rerun)
        # 使用新的 V2 版本分析器，包含组件名字获取功能
        analyzer = ComponentAnalyzerQwen(config)
        result_paths = await analyzer.run()

        
    except Exception as e:
        print(f"\n执行过程出错: {str(traceback.format_exc())}")
        return 1
    
    print(f"执行时间: {round(time.time() - st, 2)}秒")
    
    return 0

if __name__ == "__main__":
    # Windows平台需要
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main()) 