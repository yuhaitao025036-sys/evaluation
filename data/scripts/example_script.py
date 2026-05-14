#!/usr/bin/env python3
"""
DUCC 评估脚本示例模板 - v2.0 单任务执行模式

本脚本展示了如何编写符合 DUCC 评估系统规范的评估脚本。

遵循规范：
- 脚本接口规范 v2.0 (.agents/rules/script-interface.md)
- 输出目录结构规范 (.agents/rules/output-structure.md)

使用方法：
    # 单实例执行（v2.0 模式）
    python example_script.py \
        --instance-id "django__django-11099" \
        --output-dir ./data/outputs/batch_1/tasks/django__django-11099 \
        --model gpt-4-turbo \
        --tag baseline \
        --timeout 1800
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 数据集路径配置
# 方式1：通过环境变量
DATASET_BASE_PATH = os.getenv('DUCC_DATASET_PATH', '/path/to/datasets')

# 方式2：硬编码（仅用于开发测试）
# DATASET_BASE_PATH = './data/datasets'


def load_instance_by_id(dataset_name: str, instance_id: str) -> Dict[str, Any]:
    """
    从数据集中加载指定实例
    
    Args:
        dataset_name: 数据集名称（如 'swebench-lite'）
        instance_id: 实例 ID（如 'django__django-11099'）
    
    Returns:
        实例数据字典
    
    Raises:
        ValueError: 如果实例不存在
    """
    print(f"Loading instance {instance_id} from {dataset_name}")
    
    # 支持多种数据集格式
    for ext in ['.parquet', '.csv', '.jsonl', '.json']:
        dataset_path = os.path.join(DATASET_BASE_PATH, f"{dataset_name}{ext}")
        
        if not os.path.exists(dataset_path):
            continue
        
        if ext == '.parquet':
            try:
                import pandas as pd
                df = pd.read_parquet(dataset_path)
                instance = df[df['instance_id'] == instance_id]
                
                if instance.empty:
                    continue
                
                return instance.iloc[0].to_dict()
            except ImportError:
                print("Warning: pandas and pyarrow required for .parquet files")
                continue
        
        elif ext == '.csv':
            try:
                import pandas as pd
                df = pd.read_csv(dataset_path)
                instance = df[df['instance_id'] == instance_id]
                
                if instance.empty:
                    continue
                
                return instance.iloc[0].to_dict()
            except ImportError:
                print("Warning: pandas required for .csv files")
                continue
        
        elif ext == '.jsonl':
            with open(dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    instance = json.loads(line)
                    if instance.get('instance_id') == instance_id:
                        return instance
        
        elif ext == '.json':
            with open(dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for instance in data:
                    if instance.get('instance_id') == instance_id:
                        return instance
    
    raise ValueError(f"Instance '{instance_id}' not found in dataset '{dataset_name}'")


def evaluate_instance(instance: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """
    评估单个实例
    
    这是核心评估逻辑，需要根据具体任务实现：
    - 调用 AI 模型生成解决方案
    - 应用补丁到代码库
    - 运行测试验证（可选）
    - 收集执行轨迹和结果
    
    Args:
        instance: 数据集实例
        args: 命令行参数
    
    Returns:
        任务摘要字典（必须包含 instance_id, status, duration_seconds 等字段）
    """
    instance_id = instance['instance_id']
    
    print(f"{'='*60}")
    print(f"Evaluating instance: {instance_id}")
    print(f"Model: {args.model}")
    print(f"Tag: {args.tag}")
    print(f"{'='*60}")
    
    # 开始计时
    start_time = time.time()
    
    # 初始化执行轨迹
    trace = []
    
    try:
        # ==============================
        # 步骤 1: 读取问题描述
        # ==============================
        trace.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'step': 1,
            'action': 'read_problem',
            'target': instance_id,
        })
        
        problem_statement = instance.get('problem_statement', 'No problem statement provided')
        print(f"\n[1/4] Problem Statement:")
        print(f"  {problem_statement[:200]}...")
        
        # ==============================
        # 步骤 2: 生成解决方案（模拟）
        # ==============================
        print(f"\n[2/4] Generating solution with {args.model}...")
        
        trace.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'step': 2,
            'action': 'llm_call',
            'model': args.model,
            'tokens': 3500,  # 示例
        })
        
        # TODO: 在这里实现你的评估逻辑
        # 例如：patch = generate_patch_with_model(instance, args.model)
        time.sleep(0.5)  # 模拟处理时间
        
        # 模拟生成的补丁
        generated_patch = f"""diff --git a/example.py b/example.py
--- a/example.py
+++ b/example.py
@@ -10,7 +10,10 @@ def example_function():
-    return old_implementation()
+    # Fixed implementation for {instance_id}
+    return new_implementation()
"""
        
        print(f"  ✓ Patch generated ({len(generated_patch)} bytes)")
        
        # ==============================
        # 步骤 3: 应用补丁
        # ==============================
        print(f"\n[3/4] Applying patch...")
        
        trace.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'step': 3,
            'action': 'apply_patch',
            'success': True,
        })
        
        print(f"  ✓ Patch applied successfully")
        
        # ==============================
        # 步骤 4: 运行测试验证（可选）
        # ==============================
        validation_result = None
        
        if args.validate:
            print(f"\n[4/4] Running validation tests...")
            
            trace.append({
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'step': 4,
                'action': 'run_tests',
            })
            
            # TODO: 在这里实现验证逻辑
            # validation_result = run_tests(instance)
            time.sleep(0.3)  # 模拟测试运行
            
            # 模拟验证结果
            validation_result = {
                'success': True,
                'tests_passed': 10,
                'tests_failed': 0,
                'tests_total': 10,
                'error_message': None,
            }
            
            print(f"  ✓ Tests: {validation_result['tests_passed']}/{validation_result['tests_total']} passed")
        else:
            print(f"\n[4/4] Validation skipped (use --validate to enable)")
        
        # 计算耗时
        duration = time.time() - start_time
        
        # 构建任务摘要
        summary = {
            'instance_id': instance_id,
            'model': args.model,
            'tag': args.tag,
            'status': 'completed',
            'duration_seconds': round(duration, 2),
            'patch_generated': True,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }
        
        if validation_result:
            summary['validation'] = validation_result
        
        print(f"\n{'='*60}")
        print(f"✓ SUCCESS - Completed in {duration:.2f}s")
        print(f"{'='*60}")
        
        return summary, generated_patch, trace
    
    except Exception as e:
        # 失败处理
        duration = time.time() - start_time
        
        error_summary = {
            'instance_id': instance_id,
            'model': args.model,
            'tag': args.tag,
            'status': 'failed',
            'duration_seconds': round(duration, 2),
            'patch_generated': False,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error_message': str(e),
        }
        
        print(f"\n{'='*60}")
        print(f"✗ FAILED - {e}")
        print(f"{'='*60}")
        
        return error_summary, None, trace


def save_outputs(summary: Dict[str, Any], patch: Optional[str], trace: list, output_dir: str):
    """
    保存评估输出
    
    遵循输出目录结构规范：
    - task_summary.json (必需)
    - extracted_patch.diff (推荐)
    - execution_trace.jsonl (推荐)
    - validation_detail.json (推荐)
    
    Args:
        summary: 任务摘要
        patch: 生成的补丁内容（可选）
        trace: 执行轨迹列表
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 必需：保存任务摘要
    summary_path = os.path.join(output_dir, 'task_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved: {summary_path}")
    
    # 2. 推荐：保存生成的补丁
    if patch:
        patch_path = os.path.join(output_dir, 'extracted_patch.diff')
        with open(patch_path, 'w', encoding='utf-8') as f:
            f.write(patch)
        print(f"Saved: {patch_path}")
    
    # 3. 推荐：保存执行轨迹
    if trace:
        trace_path = os.path.join(output_dir, 'execution_trace.jsonl')
        with open(trace_path, 'w', encoding='utf-8') as f:
            for entry in trace:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"Saved: {trace_path}")
    
    # 4. 推荐：保存验证详情（如果有）
    if 'validation' in summary and summary['validation']:
        validation_detail = {
            'instance_id': summary['instance_id'],
            'validation_success': summary['validation']['success'],
            'tests_total': summary['validation']['tests_total'],
            'tests_passed': summary['validation']['tests_passed'],
            'tests_failed': summary['validation']['tests_failed'],
            'error_message': summary['validation'].get('error_message'),
            'timestamp': summary['timestamp'],
        }
        
        validation_path = os.path.join(output_dir, 'validation_detail.json')
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation_detail, f, indent=2, ensure_ascii=False)
        print(f"Saved: {validation_path}")


def main():
    parser = argparse.ArgumentParser(
        description='DUCC 评估脚本示例 - v2.0 单任务执行模式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # 必需参数（系统传递）
    parser.add_argument('--instance-id', required=True, help='实例 ID')
    parser.add_argument('--output-dir', required=True, help='输出目录')
    parser.add_argument('--model', required=True, help='模型标识符')
    parser.add_argument('--tag', required=True, help='批次标签')
    
    # 自定义参数（示例）
    parser.add_argument('--dataset', default='swebench-lite', help='数据集名称（默认: swebench-lite）')
    parser.add_argument('--timeout', type=int, default=1800, help='超时时间（秒，默认: 1800）')
    parser.add_argument('--validate', action='store_true', help='启用验证（运行测试）')
    parser.add_argument('--use-tmux', action='store_true', help='使用 tmux 模式（实时查看）')
    
    args = parser.parse_args()
    
    try:
        print(f"\n{'='*60}")
        print("DUCC Evaluation Script v2.0")
        print(f"{'='*60}")
        print(f"Instance ID:  {args.instance_id}")
        print(f"Output Dir:   {args.output_dir}")
        print(f"Model:        {args.model}")
        print(f"Tag:          {args.tag}")
        print(f"Dataset:      {args.dataset}")
        print(f"Timeout:      {args.timeout}s")
        print(f"Validate:     {args.validate}")
        print(f"{'='*60}\n")
        
        # 1. 加载数据集实例
        print(f"[Step 1/3] Loading instance...")
        instance = load_instance_by_id(args.dataset, args.instance_id)
        print(f"✓ Instance loaded\n")
        
        # 2. 执行评估
        print(f"[Step 2/3] Running evaluation...")
        summary, patch, trace = evaluate_instance(instance, args)
        print()
        
        # 3. 保存输出
        print(f"[Step 3/3] Saving outputs...")
        save_outputs(summary, patch, trace, args.output_dir)
        
        print(f"\n{'='*60}")
        if summary['status'] == 'completed':
            print("✓ Evaluation completed successfully")
            sys.exit(0)
        else:
            print("✗ Evaluation failed")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"✗ Fatal error: {e}")
        print(f"{'='*60}\n")
        
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
