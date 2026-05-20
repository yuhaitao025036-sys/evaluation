"""
Task Worker - 单任务执行模式
执行单个评估任务（--instance-id）

核心流程：
1. 从数据库加载任务信息
2. 更新任务状态为 running
3. 调用评估脚本（单个 instance）
4. 解析输出结果
5. 更新任务状态和结果
6. 通知调度器继续调度
"""
import os
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 数据库连接
from app.database import SessionLocal
from app.models import BatchResult, Batch, Script, Dataset, DatasetInstance


def execute_single_task(task_id: int):
    """
    执行单个任务
    
    Args:
        task_id: BatchResult 的 ID
        
    这是 RQ Worker 的入口函数
    """
    db = SessionLocal()
    
    try:
        # 1. 加载任务信息
        task = db.query(BatchResult).filter(BatchResult.id == task_id).first()
        if not task:
            print(f"Error: Task {task_id} not found")
            return
        
        batch = db.query(Batch).filter(Batch.id == task.batch_id).first()
        if not batch:
            print(f"Error: Batch {task.batch_id} not found")
            return
        
        script = db.query(Script).filter(Script.id == batch.script_id).first()
        if not script:
            print(f"Error: Script {batch.script_id} not found")
            return
        
        dataset_instance = db.query(DatasetInstance).filter(
            DatasetInstance.id == task.dataset_instance_id
        ).first()
        if not dataset_instance:
            print(f"Error: Dataset instance {task.dataset_instance_id} not found")
            return
        
        # 2. 更新任务状态为 running
        task.status = 'running'
        task.started_at = datetime.utcnow()
        task.worker_id = os.getenv('WORKER_ID', 'worker-1')
        db.commit()
        
        print(f"[Task {task_id}] Starting: {task.instance_id}")
        print(f"[Task {task_id}] Model: {task.model}, Tag: {task.tag}")
        
        dataset = db.query(Dataset).filter(Dataset.id == batch.dataset_id).first()
        if not dataset:
            print(f"Error: Dataset {batch.dataset_id} not found")
            return

        # 3. 执行评估脚本
        start_time = time.time()
        result = _execute_script(
            script_path=script.file_path,
            instance_id=task.instance_id,
            output_dir=task.output_dir,
            model=task.model,
            tag=task.tag,
            execution_config=batch.execution_config or {},
            dataset=dataset,
            dataset_instance=dataset_instance
        )
        duration = time.time() - start_time
        
        # 4. 解析结果
        if result['success']:
            # 读取 task_summary.json
            summary = _parse_task_summary(task.output_dir)
            
            task.status = 'completed'
            task.validation_success = summary.get('validation', {}).get('success')
            task.tests_passed = summary.get('validation', {}).get('tests_passed', 0)
            task.tests_failed = summary.get('validation', {}).get('tests_failed', 0)
            task.tests_total = summary.get('validation', {}).get('tests_total', 0)
            task.duration_seconds = summary.get('duration_seconds', duration)
            task.result_summary = summary
            
            # 检查 patch 文件
            patch_path = os.path.join(task.output_dir, 'extracted_patch.diff')
            if os.path.exists(patch_path):
                task.patch_path = patch_path
            
            # 检查轨迹文件
            trace_path = os.path.join(task.output_dir, 'execution_trace.jsonl')
            if os.path.exists(trace_path):
                task.trace_file_path = trace_path
            
            # 检查详细验证结果文件
            validation_detail_path = os.path.join(task.output_dir, 'validation_detail.json')
            if os.path.exists(validation_detail_path):
                task.validation_detail_path = validation_detail_path
            
            print(f"[Task {task_id}] ✓ Completed in {duration:.2f}s")
        else:
            # 执行失败
            summary = _parse_task_summary(task.output_dir)

            task.status = 'failed'
            task.error_message = summary.get('error_message') or summary.get('error') or result.get('error', 'Unknown error')
            task.duration_seconds = summary.get('duration_seconds', duration)
            task.result_summary = summary
            task.validation_success = summary.get('validation', {}).get('success')
            task.tests_passed = summary.get('validation', {}).get('tests_passed', 0)
            task.tests_failed = summary.get('validation', {}).get('tests_failed', 0)
            task.tests_total = summary.get('validation', {}).get('tests_total', 0)

            patch_path = os.path.join(task.output_dir, 'extracted_patch.diff')
            if os.path.exists(patch_path):
                task.patch_path = patch_path

            trace_path = os.path.join(task.output_dir, 'execution_trace.jsonl')
            if os.path.exists(trace_path):
                task.trace_file_path = trace_path

            validation_detail_path = os.path.join(task.output_dir, 'validation_detail.json')
            if os.path.exists(validation_detail_path):
                task.validation_detail_path = validation_detail_path

            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = 'pending'  # 重置为 pending，等待重试
                print(f"[Task {task_id}] Failed, will retry ({task.retry_count}/{task.max_retries})")
            else:
                print(f"[Task {task_id}] ✗ Failed: {task.error_message}")
        
        task.completed_at = datetime.utcnow()
        db.commit()
        
        # 5. 通知调度器继续调度
        # ✅ 确保即使通知失败也不影响任务状态
        try:
            from app.services.scheduler_service import SchedulerService
            scheduler = SchedulerService(db)
            scheduler.on_task_completed(task_id)
        except Exception as e:
            print(f"Warning: Failed to notify scheduler: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"[Task {task_id}] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
        # ✅ 更新任务状态为失败
        try:
            task = db.query(BatchResult).filter(BatchResult.id == task_id).first()
            if task:
                task.status = 'failed'
                task.error_message = f"Worker error: {str(e)}"
                task.completed_at = datetime.utcnow()
                db.commit()
                
                # ✅ 即使发生异常，也要通知调度器继续调度下一个任务
                try:
                    from app.services.scheduler_service import SchedulerService
                    scheduler = SchedulerService(db)
                    scheduler.on_task_completed(task_id)
                except Exception as scheduler_error:
                    print(f"Warning: Failed to notify scheduler after error: {scheduler_error}")
        except Exception as update_error:
            print(f"Critical: Failed to update task status: {update_error}")
            traceback.print_exc()
    
    finally:
        db.close()


def _execute_script(
    script_path: str,
    instance_id: str,
    output_dir: str,
    model: str,
    tag: str,
    execution_config: Dict[str, Any],
    dataset: Dataset,
    dataset_instance: DatasetInstance
) -> Dict[str, Any]:
    """
    执行评估脚本
    
    调用方式：
    python script.py --instance-id "xxx" --output-dir "xxx" --model "xxx" --tag "xxx" [自定义参数]
    
    Returns:
        {'success': bool, 'stdout': str, 'stderr': str, 'error': str}
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        input_path = os.path.join(output_dir, 'input_instance.json')
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump({
                'dataset_id': dataset.id,
                'dataset_name': dataset.name,
                'dataset_file_path': dataset.file_path,
                'dataset_instance_id': dataset_instance.id,
                'instance_id': dataset_instance.instance_id,
                'data': dataset_instance.data,
            }, f, ensure_ascii=False, indent=2, default=str)

        # 构建命令
        cmd = [
            'python',
            script_path,
            '--instance-id', instance_id,
            '--instance-data-path', input_path,
            '--dataset-id', str(dataset.id),
            '--dataset-name', dataset.name,
            '--dataset-path', dataset.file_path,
            '--output-dir', output_dir,
            '--model', model,
            '--tag', tag
        ]
        
        # 添加自定义参数
        for key, value in execution_config.items():
            if value is None or value == '' or value is False:
                continue

            arg_name = key if key.startswith('--') else f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                cmd.append(arg_name)
            elif isinstance(value, list):
                for item in value:
                    cmd.append(arg_name)
                    cmd.append(str(item))
            else:
                cmd.append(arg_name)
                cmd.append(str(value))
        
        print(f"Executing: {' '.join(cmd)}")
        
        # 执行脚本
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,  # 2 小时超时
            check=False
        )
        
        success = process.returncode == 0
        
        return {
            'success': success,
            'stdout': process.stdout,
            'stderr': process.stderr,
            'returncode': process.returncode,
            'error': None if success else f"Script exited with code {process.returncode}"
        }
    
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Script execution timeout (2 hours)'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Script execution error: {str(e)}"
        }


def _parse_task_summary(output_dir: str) -> Dict[str, Any]:
    """
    解析 task_summary.json
    
    Args:
        output_dir: 任务输出目录
        
    Returns:
        task_summary 内容
    """
    summary_path = os.path.join(output_dir, 'task_summary.json')
    
    if not os.path.exists(summary_path):
        return {
            'instance_id': None,
            'status': 'completed',
            'error': 'task_summary.json not found'
        }
    
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        return summary
    except Exception as e:
        return {
            'instance_id': None,
            'status': 'failed',
            'error': f"Failed to parse task_summary.json: {str(e)}"
        }


# ============================================================================
# RQ Worker 入口
# ============================================================================

if __name__ == '__main__':
    """
    直接运行此文件作为 Worker
    
    使用方法：
    python -m app.workers.task_worker
    
    或使用 RQ：
    rq worker ducc_tasks --url redis://localhost:6379
    """
    print("DUCC Task Worker - Single Task Execution Mode")
    print("Listening for tasks...")
    
    # RQ Worker 会自动调用 execute_single_task 函数
