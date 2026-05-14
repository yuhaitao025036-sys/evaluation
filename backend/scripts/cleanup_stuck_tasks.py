"""
任务超时清理脚本
定期清理卡住的任务（running 状态超过指定时间）

运行方式：
1. 直接运行：python cleanup_stuck_tasks.py
2. Cron 任务：*/10 * * * * cd /path/to/backend && python cleanup_stuck_tasks.py
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.models import Batch, BatchResult
from app.services.scheduler_service import SchedulerService


def cleanup_stuck_tasks(timeout_hours: int = 3, use_heartbeat: bool = True):
    """
    清理卡住的任务
    
    Args:
        timeout_hours: 超时时间（小时），默认 3 小时
        use_heartbeat: 是否使用心跳检测（默认 True）
    """
    db = SessionLocal()
    
    try:
        timeout = datetime.utcnow() - timedelta(hours=timeout_hours)
        
        # 查询卡住的任务
        if use_heartbeat:
            # ✅ 优先使用心跳检测：last_heartbeat 超时
            # 如果 last_heartbeat 为 NULL，回退到 started_at
            stuck_tasks = db.query(BatchResult).filter(
                BatchResult.status == 'running'
            ).all()
            
            # 过滤出真正卡住的任务
            stuck_tasks = [
                task for task in stuck_tasks
                if (task.last_heartbeat and task.last_heartbeat < timeout) or
                   (not task.last_heartbeat and task.started_at and task.started_at < timeout)
            ]
        else:
            # 使用 started_at 检测
            stuck_tasks = db.query(BatchResult).filter(
                BatchResult.status == 'running',
                BatchResult.started_at < timeout
            ).all()
        
        if not stuck_tasks:
            print(f"[{datetime.now()}] No stuck tasks found")
            return
        
        print(f"[{datetime.now()}] Found {len(stuck_tasks)} stuck tasks")
        
        cleaned_count = 0
        for task in stuck_tasks:
            print(f"  - Task {task.id} ({task.instance_id}): stuck since {task.started_at}")
            
            # 标记为失败
            task.status = 'failed'
            task.error_message = f'Task timeout: no update for {timeout_hours} hours (possible worker crash)'
            task.completed_at = datetime.utcnow()
            
            cleaned_count += 1
        
        db.commit()
        print(f"[{datetime.now()}] Cleaned {cleaned_count} stuck tasks")
        
        # 触发调度器继续调度（为每个受影响的批次）
        affected_batches = set(task.batch_id for task in stuck_tasks)
        scheduler = SchedulerService(db)
        
        for batch_id in affected_batches:
            try:
                batch = db.query(Batch).filter(Batch.id == batch_id).first()
                if batch and batch.status == 'running':
                    print(f"  - Rescheduling batch {batch_id} ({batch.batch_name})")
                    scheduler._schedule_pending_tasks(batch_id)
            except Exception as e:
                print(f"  - Warning: Failed to reschedule batch {batch_id}: {e}")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error cleaning stuck tasks: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def cleanup_orphaned_queued_tasks(timeout_minutes: int = 30):
    """
    清理孤立的队列任务
    
    queued 状态超过 N 分钟但没有变成 running 的任务
    可能是 RQ Worker 没有启动或任务丢失
    
    Args:
        timeout_minutes: 超时时间（分钟），默认 30 分钟
    """
    db = SessionLocal()
    
    try:
        timeout = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        # 查询孤立的队列任务
        orphaned_tasks = db.query(BatchResult).filter(
            BatchResult.status == 'queued',
            BatchResult.queued_at < timeout
        ).all()
        
        if not orphaned_tasks:
            print(f"[{datetime.now()}] No orphaned queued tasks found")
            return
        
        print(f"[{datetime.now()}] Found {len(orphaned_tasks)} orphaned queued tasks")
        
        cleaned_count = 0
        for task in orphaned_tasks:
            print(f"  - Task {task.id} ({task.instance_id}): queued since {task.queued_at}")
            
            # 重置为 pending，让调度器重新调度
            task.status = 'pending'
            task.job_id = None
            task.queued_at = None
            
            cleaned_count += 1
        
        db.commit()
        print(f"[{datetime.now()}] Reset {cleaned_count} orphaned tasks to pending")
        
        # 触发调度器
        affected_batches = set(task.batch_id for task in orphaned_tasks)
        scheduler = SchedulerService(db)
        
        for batch_id in affected_batches:
            try:
                batch = db.query(Batch).filter(Batch.id == batch_id).first()
                if batch and batch.status == 'running':
                    print(f"  - Rescheduling batch {batch_id} ({batch.batch_name})")
                    scheduler._schedule_pending_tasks(batch_id)
            except Exception as e:
                print(f"  - Warning: Failed to reschedule batch {batch_id}: {e}")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error cleaning orphaned tasks: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == '__main__':
    print("=" * 60)
    print(f"DUCC Task Cleanup - {datetime.now()}")
    print("=" * 60)
    
    # 清理卡住的任务（running 超过 3 小时）
    cleanup_stuck_tasks(timeout_hours=3)
    
    print()
    
    # 清理孤立的队列任务（queued 超过 30 分钟）
    cleanup_orphaned_queued_tasks(timeout_minutes=30)
    
    print("=" * 60)
    print("Cleanup completed")
    print("=" * 60)
