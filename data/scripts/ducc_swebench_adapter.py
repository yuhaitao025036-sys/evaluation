#!/usr/bin/env python3
"""
DUCC SWE-Bench 脚本适配器 - v2.0 单任务执行模式

本脚本是对现有 test_tmux_cc_experience.py 的适配器,使其符合 DUCC 评估系统的接口规范。

适配说明:
- 原始脚本: /Users/yuhaitao01/dev/baidu/explore/test/test_tmux_cc_experience.py
- 原始功能: SWE-bench Pro 评测,支持 tmux 模式
- 适配方式: 封装原始脚本,将参数转换为系统标准接口

遵循规范:
- 脚本接口规范 v2.0 (.agents/rules/script-interface.md)
- 输出目录结构规范 (.agents/rules/output-structure.md)

使用方法（v2.0 单任务模式）:
    python ducc_swebench_adapter.py \
        --instance-id "django__django-11099" \
        --output-dir ./data/outputs/batch_1/tasks/django__django-11099 \
        --model gpt-4-turbo \
        --tag baseline \
        --use-tmux \
        --validate
"""

import argparse
import json
import os
import sys
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 数据集路径配置
DATASET_BASE_PATH = os.getenv('DUCC_DATASET_PATH', '/Users/yuhaitao01/dev/baidu/explore/evaluation/data/datasets')


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
    for ext in ['.parquet', '.jsonl']:
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
        
        elif ext == '.jsonl':
            with open(dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    instance = json.loads(line)
                    if instance.get('instance_id') == instance_id:
                        return instance
    
    raise ValueError(f"Instance '{instance_id}' not found in dataset '{dataset_name}'")


def call_original_script(
    instance_id: str,
    dataset_path: str,
    output_dir: str,
    model: str,
    use_tmux: bool,
    validate: bool,
    timeout: int
) -> Dict[str, Any]:
    """
    调用原始 SWE-Bench 脚本
    
    注意: 这里假设原始脚本已支持 --instance-id 参数
    如果不支持，需要修改原始脚本或使用其他调用方式
    
    Args:
        instance_id: 实例 ID
        dataset_path: 数据集路径
        output_dir: 输出目录
        model: 模型 ID
        use_tmux: 是否使用 tmux 模式
        validate: 是否验证
        timeout: 超时时间
    
    Returns:
        执行结果字典
    """
    import subprocess
    
    print(f"Calling original SWE-Bench script...")
    
    # 构建命令
    cmd = [
        sys.executable,  # Python 解释器
        '/Users/yuhaitao01/dev/baidu/explore/test/test_tmux_cc_experience.py',
        '--instance-id', instance_id,  # v2.0: 使用实例 ID 而不是索引
        '--dataset-file', dataset_path,
        '--output-dir', output_dir,
        '--model', model,
        '--timeout', str(timeout),
    ]
    
    if use_tmux:
        cmd.append('--use-tmux')
    
    if validate:
        cmd.append('--validate')
    else:
        cmd.append('--no-validate')
    
    # 执行命令
    start_time = time.time()
    try:
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 60,  # 额外 60 秒缓冲
            check=False
        )
        
        duration = time.time() - start_time
        
        print(f"Script finished with return code: {result.returncode}")
        print(f"Duration: {duration:.2f}s")
        
        return {
            'success': result.returncode == 0,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
        }
    
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"✗ Script timeout after {timeout}s")
        
        return {
            'success': False,
            'duration': duration,
            'error': f'Timeout after {timeout}s',
            'returncode': -1,
        }
    
    except Exception as e:
        duration = time.time() - start_time
        print(f"✗ Script error: {e}")
        
        return {
            'success': False,
            'duration': duration,
            'error': str(e),
            'returncode': -1,
        }


def parse_original_output(
    instance_id: str,
    original_output_dir: str,
    execution_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    解析原始脚本的输出，转换为标准格式
    
    Args:
        instance_id: 实例 ID
        original_output_dir: 原始脚本输出目录
        execution_result: 原始脚本执行结果
    
    Returns:
        标准格式的 task_summary
    """
    safe_id = instance_id.replace('/', '_').replace(':', '_')
    original_task_dir = Path(original_output_dir) / 'tasks' / safe_id
    
    # 查找生成的 patch
    patch_path = original_task_dir / 'extracted_patch.diff'
    patch_generated = patch_path.exists()
    
    # 查找验证结果
    validation_result = None
    validation_file = original_task_dir / 'validation_result.json'
    
    if validation_file.exists():
        try:
            with open(validation_file, 'r') as f:
                val_data = json.load(f)
                validation_result = {
                    'success': val_data.get('success', False),
                    'tests_passed': val_data.get('tests_passed', 0),
                    'tests_failed': val_data.get('tests_failed', 0),
                    'tests_total': val_data.get('tests_total', 0),
                }
        except Exception as e:
            print(f"Warning: Failed to parse validation result: {e}")
    
    # 构建标准 task_summary
    summary = {
        'instance_id': instance_id,
        'status': 'completed' if execution_result['success'] else 'failed',
        'duration_seconds': round(execution_result['duration'], 2),
        'patch_generated': patch_generated,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    
    if validation_result:
        summary['validation'] = validation_result
    
    if not execution_result['success']:
        summary['error_message'] = execution_result.get('error', 'Unknown error')
    
    return summary


def copy_outputs_to_standard(
    instance_id: str,
    original_output_dir: str,
    standard_output_dir: str
):
    """
    将原始脚本的输出文件复制到标准输出目录
    
    Args:
        instance_id: 实例 ID
        original_output_dir: 原始脚本输出目录
        standard_output_dir: 标准输出目录
    """
    safe_id = instance_id.replace('/', '_').replace(':', '_')
    original_task_dir = Path(original_output_dir) / 'tasks' / safe_id
    standard_task_dir = Path(standard_output_dir)
    
    # 确保标准输出目录存在
    standard_task_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制关键文件
    files_to_copy = [
        'extracted_patch.diff',
        'execution_trace.jsonl',
        'validation_detail.json',
        'agent_logs.txt',
        'test_output.log',
    ]
    
    for filename in files_to_copy:
        src = original_task_dir / filename
        if src.exists():
            dst = standard_task_dir / filename
            shutil.copy2(src, dst)
            print(f"Copied: {filename}")


def evaluate_instance(instance: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """
    评估单个实例（适配器主函数）
    
    Args:
        instance: 数据集实例
        args: 命令行参数
    
    Returns:
        标准格式的 task_summary
    """
    instance_id = instance['instance_id']
    
    print(f"{'='*60}")
    print(f"Processing instance: {instance_id}")
    print(f"Model: {args.model}")
    print(f"Tag: {args.tag}")
    print(f"{'='*60}")
    
    # 创建临时输出目录（原始脚本使用）
    temp_output_dir = Path(args.output_dir).parent / f'.temp_{safe_instance_id(instance_id)}'
    temp_output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 准备数据集路径
        dataset_path = os.path.join(DATASET_BASE_PATH, f"{args.dataset}.parquet")
        if not os.path.exists(dataset_path):
            dataset_path = os.path.join(DATASET_BASE_PATH, f"{args.dataset}.jsonl")
        
        # 调用原始脚本
        execution_result = call_original_script(
            instance_id=instance_id,
            dataset_path=dataset_path,
            output_dir=str(temp_output_dir),
            model=args.model,
            use_tmux=args.use_tmux,
            validate=args.validate,
            timeout=args.timeout
        )
        
        # 解析输出
        summary = parse_original_output(
            instance_id=instance_id,
            original_output_dir=str(temp_output_dir),
            execution_result=execution_result
        )
        
        # 添加模型和标签信息
        summary['model'] = args.model
        summary['tag'] = args.tag
        
        # 复制输出文件到标准目录
        copy_outputs_to_standard(
            instance_id=instance_id,
            original_output_dir=str(temp_output_dir),
            standard_output_dir=args.output_dir
        )
        
        # 保存标准 task_summary
        summary_path = Path(args.output_dir) / 'task_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"Saved: task_summary.json")
        
        # 保存数据集信息
        dataset_info = {
            'instance_id': instance_id,
            'problem_statement': instance.get('problem_statement', ''),
            'repo': instance.get('repo', ''),
            'base_commit': instance.get('base_commit', ''),
            'patch': instance.get('patch', ''),
            'test_patch': instance.get('test_patch', ''),
            'repo_language': instance.get('repo_language', ''),
        }
        
        info_path = Path(args.output_dir) / 'dataset_info.json'
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(dataset_info, f, indent=2, ensure_ascii=False)
        print(f"Saved: dataset_info.json")
        
        print(f"\n{'='*60}")
        print(f"Status: {summary['status']}")
        print(f"Duration: {summary['duration_seconds']}s")
        print(f"Patch Generated: {summary['patch_generated']}")
        if 'validation' in summary:
            val = summary['validation']
            print(f"Validation: {val['tests_passed']}/{val['tests_total']} tests passed")
        print(f"{'='*60}")
        
        return summary
    
    finally:
        # 清理临时目录
        if temp_output_dir.exists():
            try:
                shutil.rmtree(temp_output_dir)
                print(f"Cleaned up temporary directory")
            except Exception as e:
                print(f"Warning: Failed to clean up temp directory: {e}")


def safe_instance_id(instance_id: str) -> str:
    """转换实例 ID 为安全的文件名"""
    return instance_id.replace('/', '_').replace(':', '_')


def main():
    parser = argparse.ArgumentParser(
        description='DUCC SWE-Bench 脚本适配器 - v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # 必需参数（系统传递）
    parser.add_argument('--instance-id', required=True, help='实例 ID')
    parser.add_argument('--output-dir', required=True, help='输出目录')
    parser.add_argument('--model', required=True, help='模型标识符')
    parser.add_argument('--tag', required=True, help='批次标签')
    
    # 自定义参数（SWE-Bench 特定）
    parser.add_argument('--dataset', default='swebench-lite', help='数据集名称')
    parser.add_argument('--timeout', type=int, default=1800, help='超时时间（秒）')
    parser.add_argument('--use-tmux', action='store_true', help='启用 tmux 模式')
    parser.add_argument('--validate', action='store_true', default=True, help='启用验证')
    parser.add_argument('--no-validate', dest='validate', action='store_false', help='禁用验证')
    
    args = parser.parse_args()
    
    try:
        print(f"\n{'='*60}")
        print("DUCC SWE-Bench Adapter v2.0")
        print(f"{'='*60}")
        print(f"Instance ID:  {args.instance_id}")
        print(f"Output Dir:   {args.output_dir}")
        print(f"Model:        {args.model}")
        print(f"Tag:          {args.tag}")
        print(f"Dataset:      {args.dataset}")
        print(f"Timeout:      {args.timeout}s")
        print(f"Use tmux:     {args.use_tmux}")
        print(f"Validate:     {args.validate}")
        print(f"{'='*60}\n")
        
        # 加载实例
        print(f"[Step 1/2] Loading instance...")
        instance = load_instance_by_id(args.dataset, args.instance_id)
        print(f"✓ Instance loaded\n")
        
        # 执行评估
        print(f"[Step 2/2] Running evaluation...")
        summary = evaluate_instance(instance, args)
        
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
