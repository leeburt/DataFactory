import os
import asyncio
import json
import traceback
from src.config import Config
from src.step1_generate import ComponentAnalyzer
from src.step2_evaluate import ConsistencyEvaluator
from src.utils import parse_args, create_config_from_args
from config.prompts import (COMPONENTS_LIST_PROMPT_MODEL1
                            , COMPONENTS_LIST_PROMPT_MODEL2
                            , COMPONENT_IO_PROMPT_MODEL1
                            , COMPONENT_IO_PROMPT_MODEL2
                            , CONSISTENCY_EVAL_PROMPT
                            , COMPONENT_CONSISTENCY_PROMPT
                            )


def get_prompts(config: Config):
    prompts = {
        "components_list_prompt_model1": COMPONENTS_LIST_PROMPT_MODEL1,
        "components_list_prompt_model2": COMPONENTS_LIST_PROMPT_MODEL2,
        "component_io_prompt_model1": COMPONENT_IO_PROMPT_MODEL1,
        "component_io_prompt_model2": COMPONENT_IO_PROMPT_MODEL2,
        "consistency_eval_prompt": CONSISTENCY_EVAL_PROMPT,
        "component_consistency_prompt": COMPONENT_CONSISTENCY_PROMPT
    }
    config.prompts = prompts
    return config

async def main():
    """主程序入口"""
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
    print(f"- 模型1: {config.model1_model}")
    print(f"- 模型2: {config.model2_model}")
    print(f"- 评估模型: {config.evaluator_model}")
    print("=" * 50)
    
    try:
        # 第一步：组件识别和IO分析
        print("\n第一步：组件识别和IO分析")
        print("-" * 50)
        analyzer = ComponentAnalyzer(config)
        result_paths = await analyzer.run()
        
        # 第二步：一致性评估
        print("\n第二步：一致性评估")
        print("-" * 50)
        evaluator = ConsistencyEvaluator(config, result_paths)
        await evaluator.run()
        
        print("\n两步评估流程执行完成!")
        
    except Exception as e:
        print(f"\n执行过程出错: {str(traceback.format_exc())}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Windows平台需要
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main()) 