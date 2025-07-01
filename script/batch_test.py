#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量测试脚本
用于测试多种不同的提示和使用场景
"""

from openai import OpenAI
import json
import time
import csv
from datetime import datetime

# API配置
API_BASE = "https://jeniya.top/v1"
API_KEY = "sk-EWCvOoyOvpl53kI3hYgFyq9vbyVWuefsWp9ODk2cYnIleDhA"
MODEL_NAME = "o4-mini"

# 初始化客户端
client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE
)

# 测试用例集合
TEST_PROMPTS = [
    {
        "category": "基础对话",
        "prompts": [
            "你好，请介绍一下你自己",
            "今天天气真不错",
            "你能帮我做什么？",
            "谢谢你的帮助",
            "再见"
        ]
    },
    {
        "category": "知识问答",
        "prompts": [
            "什么是人工智能？",
            "Python和Java有什么区别？",
            "解释一下机器学习的基本概念",
            "什么是深度学习？",
            "区块链技术的原理是什么？"
        ]
    },
    {
        "category": "创意写作",
        "prompts": [
            "写一首关于春天的诗",
            "编一个小故事，主角是一只猫",
            "为一家咖啡店写一段广告文案",
            "写一段关于友谊的感悟",
            "创作一个科幻小说的开头"
        ]
    },
    {
        "category": "编程相关",
        "prompts": [
            "用Python写一个计算斐波那契数列的函数",
            "解释什么是递归",
            "如何优化数据库查询性能？",
            "什么是RESTful API？",
            "Git的基本命令有哪些？"
        ]
    },
    {
        "category": "逻辑推理",
        "prompts": [
            "如果所有的猫都怕水，而汤姆是一只猫，那么汤姆怕水吗？",
            "一个数字序列：2, 4, 8, 16, ?，下一个数字是什么？",
            "有3个开关和3个灯泡，你只能上楼一次，如何确定哪个开关控制哪个灯泡？",
            "如果今天是星期三，那么100天后是星期几？",
            "一个池塘里的荷花每天翻倍，30天后铺满整个池塘，问第几天铺满一半？"
        ]
    },
    {
        "category": "生活建议",
        "prompts": [
            "如何保持健康的生活方式？",
            "推荐几本值得阅读的书籍",
            "如何管理时间更有效率？",
            "学习新技能的最佳方法是什么？",
            "如何处理工作压力？"
        ]
    }
]

def test_single_prompt(prompt, category, max_tokens=150, temperature=0.7):
    """测试单个提示"""
    try:
        start_time = time.time()
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        result = {
            "category": category,
            "prompt": prompt,
            "response": response.choices[0].message.content,
            "response_time": response_time,
            "tokens_used": response.usage.total_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "success": True,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        result = {
            "category": category,
            "prompt": prompt,
            "response": None,
            "response_time": None,
            "tokens_used": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        return result

def run_batch_test():
    """运行批量测试"""
    print("="*60)
    print("  OpenAI API 批量测试")
    print("="*60)
    
    all_results = []
    total_prompts = sum(len(category["prompts"]) for category in TEST_PROMPTS)
    current_prompt = 0
    
    for category_data in TEST_PROMPTS:
        category = category_data["category"]
        prompts = category_data["prompts"]
        
        print(f"\n📝 测试类别: {category}")
        print("-" * 40)
        
        category_results = []
        
        for prompt in prompts:
            current_prompt += 1
            print(f"[{current_prompt}/{total_prompts}] 测试: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            
            result = test_single_prompt(prompt, category)
            all_results.append(result)
            category_results.append(result)
            
            if result["success"]:
                print(f"  ✅ 成功 | 用时: {result['response_time']:.2f}s | Token: {result['tokens_used']}")
                print(f"  回复: {result['response'][:100]}{'...' if len(result['response']) > 100 else ''}")
            else:
                print(f"  ❌ 失败: {result['error']}")
            
            print()
            time.sleep(0.5)  # 避免请求过快
        
        # 类别统计
        successful = sum(1 for r in category_results if r["success"])
        print(f"📊 {category} 类别统计: {successful}/{len(prompts)} 成功")
        
        if successful > 0:
            avg_time = sum(r["response_time"] for r in category_results if r["success"]) / successful
            avg_tokens = sum(r["tokens_used"] for r in category_results if r["success"]) / successful
            print(f"   平均响应时间: {avg_time:.2f}秒")
            print(f"   平均Token使用: {avg_tokens:.1f}")
    
    return all_results

def generate_report(results):
    """生成测试报告"""
    print("\n" + "="*60)
    print("  测试报告")
    print("="*60)
    
    # 总体统计
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - successful_tests
    
    print(f"\n📈 总体统计:")
    print(f"  总测试数: {total_tests}")
    print(f"  成功: {successful_tests}")
    print(f"  失败: {failed_tests}")
    print(f"  成功率: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests > 0:
        # 性能统计
        successful_results = [r for r in results if r["success"]]
        avg_response_time = sum(r["response_time"] for r in successful_results) / len(successful_results)
        avg_tokens = sum(r["tokens_used"] for r in successful_results) / len(successful_results)
        total_tokens = sum(r["tokens_used"] for r in successful_results)
        
        print(f"\n⚡ 性能统计:")
        print(f"  平均响应时间: {avg_response_time:.2f}秒")
        print(f"  平均Token使用: {avg_tokens:.1f}")
        print(f"  总Token消耗: {total_tokens}")
        
        # 按类别统计
        print(f"\n📊 分类别统计:")
        categories = {}
        for result in results:
            category = result["category"]
            if category not in categories:
                categories[category] = {"total": 0, "success": 0}
            categories[category]["total"] += 1
            if result["success"]:
                categories[category]["success"] += 1
        
        for category, stats in categories.items():
            success_rate = (stats["success"] / stats["total"]) * 100
            print(f"  {category}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
    
    # 失败分析
    if failed_tests > 0:
        print(f"\n❌ 失败分析:")
        failed_results = [r for r in results if not r["success"]]
        error_types = {}
        for result in failed_results:
            error = result["error"]
            if error not in error_types:
                error_types[error] = 0
            error_types[error] += 1
        
        for error, count in error_types.items():
            print(f"  {error}: {count}次")

def save_results_to_csv(results, filename=None):
    """保存结果到CSV文件"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_test_results_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'timestamp', 'category', 'prompt', 'response', 
            'success', 'error', 'response_time', 'tokens_used',
            'prompt_tokens', 'completion_tokens'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow(result)
    
    print(f"\n💾 结果已保存到: {filename}")

def save_results_to_json(results, filename=None):
    """保存结果到JSON文件"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(results, jsonfile, ensure_ascii=False, indent=2)
    
    print(f"💾 结果已保存到: {filename}")

def main():
    """主函数"""
    print("开始批量测试...")
    
    # 运行测试
    results = run_batch_test()
    
    # 生成报告
    generate_report(results)
    
    # 保存结果
    save_results_to_csv(results)
    save_results_to_json(results)
    
    print(f"\n🎉 批量测试完成！")

if __name__ == "__main__":
    main() 