import datetime
import os 


class Config:
    """配置类，存储运行时所需的各种参数"""
    
    def __init__(self, **kwargs):
        # 基本配置
        self.image_root_dir = kwargs.get('image_root_dir', '')
        self.prompts_path = kwargs.get('prompts_path', '')
        self.output_dir = kwargs.get('output_dir', '')
        
        # 模型配置
        self.model1_api = kwargs.get('model1_api', '')
        self.model1_key = kwargs.get('model1_key', '')
        self.model1_model = kwargs.get('model1_model', '')
        
        self.model2_api = kwargs.get('model2_api', '')
        self.model2_key = kwargs.get('model2_key', '')
        self.model2_model = kwargs.get('model2_model', '')
        
        self.evaluator_api = kwargs.get('evaluator_api', '')
        self.evaluator_key = kwargs.get('evaluator_key', '')
        self.evaluator_model = kwargs.get('evaluator_model', '')
        
        # 并发与生成参数
        self.num_workers = kwargs.get('num_workers', 4)
        self.temperature = kwargs.get('temperature', 0.1)
        self.max_tokens = kwargs.get('max_tokens', 2048)
