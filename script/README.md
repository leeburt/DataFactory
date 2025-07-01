# OpenAI API 测试脚本

这个目录包含了用于测试OpenAI API的各种脚本。

## 文件说明

### 1. `test_api.py` - 主要测试脚本
功能完整的API测试脚本，包含多种测试场景。

**使用方法:**
```bash
# 快速测试（默认）
python test_api.py

# 快速测试（显式指定）
python test_api.py quick

# 完整测试套件
python test_api.py full
```

**测试内容:**
- ✅ 基本对话功能
- ✅ 多轮对话功能  
- ✅ 流式响应功能
- ✅ 不同参数设置
- ✅ 错误处理测试
- ✅ 性能测试

### 2. `batch_test.py` - 批量测试脚本
用于批量测试多种不同类型的提示。

**使用方法:**
```bash
python batch_test.py
```

**测试类别:**
- 📝 基础对话
- 🧠 知识问答
- ✍️ 创意写作
- 💻 编程相关
- 🤔 逻辑推理
- 💡 生活建议

**输出文件:**
- `batch_test_results_YYYYMMDD_HHMMSS.csv` - CSV格式结果
- `batch_test_results_YYYYMMDD_HHMMSS.json` - JSON格式结果

### 3. `test_api.ipynb` - Jupyter Notebook版本
交互式测试环境，适合逐步测试和调试。

## API配置

在使用前，请确认以下配置信息：

```python
API_BASE = "https://jeniya.top/v1"
API_KEY = "sk-EWCvOoyOvpl53kI3hYgFyq9vbyVWuefsWp9ODk2cYnIleDhA"
MODEL_NAME = "o4-mini"
```

## 依赖安装

```bash
pip install openai
```

## 使用建议

1. **首次使用**: 先运行快速测试确认API连接正常
   ```bash
   python test_api.py quick
   ```

2. **全面测试**: 运行完整测试套件
   ```bash
   python test_api.py full
   ```

3. **批量评估**: 使用批量测试脚本评估不同场景下的表现
   ```bash
   python batch_test.py
   ```

4. **交互式测试**: 使用Jupyter Notebook进行逐步测试
   ```bash
   jupyter notebook test_api.ipynb
   ```

## 测试结果说明

### 成功指标
- ✅ API连接成功
- ✅ 响应内容合理
- ✅ Token统计正确
- ✅ 响应时间合理

### 性能参考
- 响应时间: 通常在1-5秒之间
- Token使用: 根据输入和输出长度变化
- 成功率: 应该达到95%以上

## 故障排除

### 常见问题

1. **连接失败**
   - 检查网络连接
   - 验证API密钥
   - 确认API地址正确

2. **模型不存在**
   - 检查模型名称是否正确
   - 确认账户有权限使用该模型

3. **请求过于频繁**
   - 脚本已内置延迟机制
   - 如仍有问题，可增加延迟时间

4. **Token超限**
   - 检查max_tokens设置
   - 确认账户余额充足

### 调试模式

如需详细调试信息，可在脚本中添加：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展功能

### 添加新测试
在`TEST_PROMPTS`中添加新的测试类别和提示：

```python
{
    "category": "新类别",
    "prompts": [
        "测试提示1",
        "测试提示2"
    ]
}
```

### 自定义参数
修改测试参数：

```python
def test_single_prompt(prompt, category, max_tokens=200, temperature=0.8):
    # 自定义参数
```

## 注意事项

1. **API密钥安全**: 不要将API密钥提交到版本控制系统
2. **成本控制**: 批量测试会消耗较多Token，注意成本
3. **频率限制**: 遵守API的频率限制，避免请求过快
4. **结果保存**: 测试结果会自动保存，注意磁盘空间

## 联系支持

如遇到问题，请检查：
1. API文档和限制
2. 网络连接状态  
3. 账户状态和余额
4. 模型可用性 