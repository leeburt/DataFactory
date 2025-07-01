import os
import json
import argparse
from src.config import Config

def load_config(config_path: str) -> dict:
    """从JSON文件加载配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"加载配置文件失败: {str(e)}")

def get_image_files(image_root: str) -> list:
    """获取图像目录中的所有图像文件"""
    image_files = []
    
    # 支持的图像文件扩展名
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff']
    
    # 遍历图像目录
    for root, _, files in os.walk(image_root):
        for file in files:
            # 检查文件扩展名
            if any(file.lower().endswith(ext) for ext in image_extensions):
                # 获取相对路径
                rel_path = os.path.relpath(os.path.join(root, file), image_root)
                image_files.append(rel_path)
    
    return image_files

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="电路图两步评估工具")
    
    # 配置文件参数
    parser.add_argument("--config", type=str, default="./config/run_config.json",
                      help="配置文件路径")
    
    # 可选参数，用于覆盖配置文件中的设置
    parser.add_argument("--image-root", type=str,
                      help="图像根目录路径")
    parser.add_argument("--output-dir", type=str,
                      help="输出目录路径")
    parser.add_argument("--workers", type=int,
                      help="并发工作线程数")

    parser.add_argument("--old-results-path", type=str,
                      help="旧结果路径")    
    parser.add_argument("--rerun", type=bool,
                      help="是否重新运行")
    
    return parser.parse_args()

def create_config_from_args(args):
    """从命令行参数和配置文件创建配置对象"""
    # 首先从配置文件加载
    config_data = load_config(args.config)
    
    # 命令行参数覆盖配置文件
    if args.image_root:
        config_data["image_root"] = args.image_root
    
    if args.output_dir:
        config_data["output_dir"] = args.output_dir
    
    if args.workers:
        config_data["workers"] = args.workers

    if args.old_results_path:
        config_data["old_results_path"] = args.old_results_path

    if args.rerun:
        config_data["rerun"] = args.rerun
    
    # 创建配置对象
    config = Config(
        # 基本配置
        image_root_dir=config_data["image_root"],
        prompts_path=config_data["prompts_file"],
        output_dir=config_data["output_dir"],
        
        # 模型配置
        model1_api=config_data["model1_api"],
        model1_key=config_data["model1_key"],
        model1_model=config_data["model1_model"],
        
        model2_api=config_data["model2_api"],
        model2_key=config_data["model2_key"],
        model2_model=config_data["model2_model"],
        
        evaluator_api=config_data["evaluator_api"],
        evaluator_key=config_data["evaluator_key"],
        evaluator_model=config_data["evaluator_model"],
        
        # 并发配置
        num_workers=config_data["workers"],
        
        # 生成参数
        temperature=config_data["temperature"],
        max_tokens=config_data["max_tokens"],

        ##sample node rate 
        node_sample_rate=config_data["node_sample_rate"],
    )
    
    # 创建输出目录
    os.makedirs(config.output_dir, exist_ok=True)
    
    return config 