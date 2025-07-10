# 组件分析器 V2 版本更新说明

## 主要更改

本次更新在原有的组件检测和连接关系分析基础上，增加了一个新的流程来获取所有组件的名字。**关键改进**：基于目标检测结果，逐个询问每个组件的名字，然后在分析连接关系时使用这些统一的组件名称。

## 新增功能

### 1. 单个组件名字获取
- **新增方法**: `_get_component_name()` 
- **功能**: 基于目标检测框，使用大模型识别单个组件的名字
- **工作方式**: 将检测框绘制在图像上，询问大模型红色框中的组件名字
- **返回格式**: 直接返回组件名称字符串

### 2. 批量组件名字获取
- **新增方法**: `_get_all_component_names()` 
- **功能**: 基于目标检测结果，并行获取所有组件的名字
- **工作方式**: 为每个检测到的组件创建并发任务，逐个询问名字
- **返回格式**: `{"[x1, y1, x2, y2]": "组件名称"}`

### 3. 增强的连接关系分析
- **修改方法**: `_get_component_io()` 
- **新增参数**: `component_names` - 传入所有组件的名字信息
- **功能增强**: 在分析单个组件连接关系时，会将所有组件的名字和坐标信息加入到prompt中

### 4. 组件信息文本生成
- **新增方法**: `_create_component_info_text()`
- **功能**: 创建包含所有组件名字和坐标的信息文本，用于增强prompt

## 修改的文件

### 1. `node_connections/get_node_info_from_det_v2.py`
- 新增 `_get_component_name()` 方法 - 获取单个组件名字
- 新增 `_get_all_component_names()` 方法 - 批量获取组件名字
- 新增 `_create_component_info_text()` 方法 - 生成组件信息文本
- 修改 `_get_component_io()` 方法，添加组件名字参数
- 修改 `_process_image()` 方法，增加获取组件名字的步骤
- 修改 `_draw_box_to_image()` 方法，优化绘制逻辑
- 修改数据结构，在结果中保存 `component_names` 字段

### 2. `config/prompts_node.py`
- 新增 `COMPONENT_NAME_PROMPT` 提示词
- 用于指导模型识别红色框中单个组件的名字
- 修改 `COMPONENT_IO_PROMPT_MODEL` 提示词，优化格式

### 3. `run_get_node_conections.py`
- 导入新的 `ComponentAnalyzerV2` 类
- 导入新的 `COMPONENT_NAME_PROMPT` 提示词
- 更新 prompts 配置，添加单个组件名字获取提示词
- 修改主程序使用新的 V2 版本分析器

## 工作流程

新的分析流程如下：

1. **目标检测**: 使用 `NodeIO` 获取组件位置和IO信息
2. **组件名字获取**: 基于检测结果，逐个询问每个组件的名字 (**新增**)
   - 为每个检测框绘制红色边界
   - 并发询问大模型识别组件名字
   - 建立坐标到名字的映射
3. **连接关系分析**: 分析每个组件的连接关系，使用统一的组件名字 (**增强**)

## 关键技术实现

### 单个组件名字获取流程
```python
# 1. 绘制检测框
image_base64 = self._draw_box_to_image(full_image_path, node_box)

# 2. 询问模型
result = await self.model_client.generate(
    session,
    self.prompts_data["COMPONENT_NAME_PROMPT"],
    "请识别红色框中组件的名字",
    image_base64
)

# 3. 解析结果
component_name = result["content"].strip()
```

### 批量并发获取
```python
# 创建并发任务
tasks = [get_single_component_name(key) for key in components.keys()]
results = await asyncio.gather(*tasks)
```

## 输出数据结构

```json
{
  "image_id": {
    "components": {...},           // 目标检测结果
    "component_names": {           // 新增：组件名字映射
      "[x1, y1, x2, y2]": "组件名"
    },
    "component_details": {         // 连接关系分析结果
      "[x1, y1, x2, y2]": {
        "description": {...},
        "warning": "JSON格式正确",
        "io_num_match": true,
        "det_io_info": {...}
      }
    }
  }
}
```

## 使用方法

### 运行新版本分析器
```bash
python run_get_node_conections.py --config config.json
```

### 测试新功能
```bash
python test_component_analyzer_v2.py
```

## 关键改进

1. **可行性**: 基于目标检测结果逐个询问，避免了让模型直接输出精确坐标的困难
2. **名称一致性**: 确保在分析连接关系时，所有组件都使用统一的名称
3. **并发效率**: 使用异步并发获取所有组件名字，提高处理效率
4. **上下文增强**: 在分析单个组件时，提供全图组件信息作为上下文
5. **错误处理**: 完善的错误处理机制，确保单个组件失败不影响整体流程
6. **可追溯性**: 保存组件名字映射，便于后续分析和调试

## 注意事项

1. 需要确保 `COMPONENT_NAME_PROMPT` 在配置中正确设置
2. 大模型需要支持图像输入，能够识别红色框中的组件
3. 新增的组件名字获取步骤会增加处理时间（每个组件需要单独询问）
4. 建议在测试环境中先验证新功能的效果
5. 组件名字获取采用并发处理，可以通过 `num_workers` 参数控制并发数量

## 性能考虑

- **并发处理**: 组件名字获取使用异步并发，减少总体处理时间
- **缓存机制**: 已处理的图像会被缓存，避免重复处理
- **错误恢复**: 单个组件名字获取失败时，会使用"未知组件"作为默认名称
- **内存优化**: 及时释放图像资源，避免内存泄漏 