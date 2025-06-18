# CircuitEval

电路图解析一致性评估工具。采用两步评估法评估不同大模型对电路图解析的一致性。

## 项目结构

```
CircuitEval/
  ├── config/              # 配置文件目录
  │   ├── prompts.json     # 提示词配置
  │   └── run_config.json  # 运行配置
  ├── src/                 # 源代码目录
  │   ├── __init__.py
  │   ├── config.py        # 配置类
  │   ├── image_processor.py # 图像处理
  │   ├── model_client.py  # 模型客户端
  │   ├── step1_generate.py # 第一步：组件识别和IO分析
  │   ├── step2_evaluate.py # 第二步：一致性评估
  │   └── utils.py         # 工具函数
  ├── images/              # 图像目录
  ├── results/             # 结果输出目录
  ├── main.py              # 主程序
  ├── run.bat              # Windows运行脚本
  └── run.sh               # Linux/Mac运行脚本
```

## 新特性：组件级别一致性评估

最新版本增加了组件级别一致性评估功能，不再只是比较整张图片的一致性，而是：

1. **智能组件匹配**：
   - 使用评估模型匹配两个不同模型识别出的同一组件（即使名称不同）
   - 基于组件类型、ID和电路中的位置进行匹配
   - 处理组件命名差异，如"电阻R1"和"R1"能被正确匹配

2. **逐组件评估**：
   - 对每对匹配的组件单独进行一致性评估
   - 分析每个组件的连接关系和功能描述
   - 给出0-100分的一致性评分

3. **详细不一致分析**：
   - 列出每个组件对的具体不一致点
   - 提供明确的一致性评估理由
   - 帮助工程师快速定位问题组件

## 两步评估流程

该工具实现了两步评估流程：

1. **第一步**：组件识别和IO分析
   - 分别询问两个大模型电路图中有哪些部件，获取组件列表
   - 对每个识别出的组件，询问其输入输出线及连接关系（使用统一的英文JSON格式）
   - 将每个模型的分析结果组装成结构化JSON文件

2. **第二步**：一致性评估
   - 使用评估模型将两个模型识别的组件进行配对匹配
   - 对每对匹配的组件进行详细的连接关系和功能一致性评估
   - 同时提供整体图像级别和细粒度组件级别的一致性结果

## 使用方法

### 1. 准备配置文件

#### 提示词配置 (config/prompts.json)

提示词配置中新增了两个关键项：

1. **组件匹配提示词** (`component_matching_prompt`)：
   - 用于指导评估模型如何匹配两个模型识别的组件
   - 考虑组件类型、标识符等因素进行智能匹配

2. **组件一致性评估提示词** (`component_consistency_prompt`)：
   - 指导评估模型评估单个组件对的分析一致性
   - 比较连接、功能和角色描述的一致性

#### 运行配置 (config/run_config.json)

```json
{
  "image_root": "./images",
  "prompts_file": "./config/prompts.json",
  "output_dir": "./results",
  
  "model1_api": "https://api.openai.com/v1",
  "model1_key": "sk-your-openai-api-key",
  "model1_model": "gpt-4-vision-preview",
  
  "model2_api": "https://api.anthropic.com/v1",
  "model2_key": "sk-your-anthropic-api-key",
  "model2_model": "claude-3-opus-20240229",
  
  "evaluator_api": "https://api.openai.com/v1",
  "evaluator_key": "sk-your-openai-api-key",
  "evaluator_model": "gpt-4-vision-preview",
  
  "workers": 4,
  "temperature": 0.1,
  "max_tokens": 2048
}
```

**注意**：确保evaluator_model设置为支持视觉的模型，如gpt-4-vision-preview或claude-3-opus，以便能处理图像辅助评估。

### 2. 准备图像

将电路图图像放入`images/`目录中。

### 3. 运行评估

#### Windows
```
run.bat
```

#### Linux/Mac
```
bash run.sh
```

### 4. 手动运行
```bash
python main.py --config ./config/run_config.json
```

可以使用以下参数覆盖配置文件中的设置：
```bash
python main.py --config ./config/run_config.json --image-root ./custom_images --output-dir ./custom_results --workers 2
```

## 组件级评估输出结果

评估过程会在指定的输出目录（默认为`./results/`）生成以下文件：

- `model1_analysis.json`: 模型1的完整分析结果(组件及IO关系)
- `model2_analysis.json`: 模型2的完整分析结果(组件及IO关系)
- `component_consistency_results.json`: 组件级一致性评估详细结果
- `component_consistency_stats.json`: 组件级一致性统计数据

### 组件级评估结果格式

每个图像的组件级评估结果包含以下字段：

```json
{
  "image_id": "example.jpg",
  "overall_consistent": true,
  "overall_score": 85,
  "component_count": 10,
  "consistent_count": 8,
  "component_results": [
    {
      "component_pair": "电阻R1 (模型1) & R1 (模型2)",
      "is_consistent": true,
      "consistency_score": 95,
      "inconsistencies": [],
      "reasoning": "两个模型对R1的分析高度一致..."
    },
    {
      "component_pair": "电容C1 (模型1) & 电容器C1 (模型2)",
      "is_consistent": false,
      "consistency_score": 60,
      "inconsistencies": [
        "连接到的组件描述不一致",
        "功能描述存在差异"
      ],
      "reasoning": "两个模型对C1的连接描述存在明显差异..."
    }
  ],
  "reason": "8/10 组件分析一致"
}
```

### 组件级统计结果格式

```json
{
  "total_images": 5,
  "consistent_images": 3,
  "inconsistent_images": 2,
  "image_consistency_rate": 0.6,
  "total_components": 35,
  "consistent_components": 28,
  "component_consistency_rate": 0.8,
  "average_consistency_score": 82.5
}
```

## 解决常见问题

### 组件匹配问题

如果出现以下警告：
```
警告: 未能匹配任何组件对
```

可能的原因：
1. 两个模型识别的组件命名差异太大
2. 两个模型识别出的组件集合差异太大
3. 评估模型无法确定组件对应关系

解决方法：
1. 调整`component_matching_prompt`以提供更多匹配线索
2. 增加温度参数使匹配更灵活
3. 检查两个模型的组件识别结果，确保基本一致

### 组件评估错误

如果组件评估结果不准确，可能的原因：
1. 组件细节数据格式不一致
2. 评估提示词不够明确
3. 组件描述缺乏足够细节

解决方法：
1. 确保两个模型的组件IO描述格式一致
2. 调整`component_consistency_prompt`以提供更清晰的评估标准
3. 调整第一阶段的提示词，获取更详细的组件描述

## 依赖项

- Python 3.6+
- aiohttp
- tqdm

安装依赖：
```bash
pip install aiohttp tqdm
``` 