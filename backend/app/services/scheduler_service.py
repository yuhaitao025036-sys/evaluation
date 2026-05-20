"""
Task Scheduler Service
任务调度服务 - 系统级任务调度和并发控制

核心功能：
1. 根据批次的 max_concurrency 控制并发
2. 将 pending 任务加入 RQ 队列
3. 监控任务状态，自动调度下一个任务
4. 支持暂停/恢复/重试
"""
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Batch, BatchResult
from app.services.batch_service import BatchService
from app.workers.task_worker import execute_single_task  # Worker 函数

try:
    from rq import Queue
    from redis import Redis
    RQ_AVAILABLE = True
except ImportError:
    RQ_AVAILABLE = False
    print("Warning: RQ not available, tasks will run synchronously")


class SchedulerService:
    """任务调度服务"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 初始化 RQ
        if RQ_AVAILABLE:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            self.redis_conn = Redis(host=redis_host, port=redis_port)
            self.queue = Queue('ducc_tasks', connection=self.redis_conn)
        else:
            self.redis_conn = None
            self.queue = None
    
    def start_batch(self, batch_id: int, force: bool = False) -> Dict[str, Any]:
        """
        启动批次
        
        Args:
            batch_id: 批次 ID
            force: 强制启动（即使有失败任务）
            
        Returns:
            启动结果统计
        """
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"批次 ID {batch_id} 不存在")
        
        # 检查批次状态
        if batch.status == 'running':
            raise ValueError(f"批次 '{batch.batch_name}' 已在运行中")
        
        if batch.status == 'completed' and not force:
            raise ValueError(f"批次 '{batch.batch_name}' 已完成，使用 force=True 强制重启")
        
        # 更新批次状态
        batch.status = 'running'
        batch.started_at = datetime.utcnow()
        self.db.commit()
        
        # 调度任务
        scheduled_count = self._schedule_pending_tasks(batch_id)
        
        return {
            'batch_id': batch_id,
            'batch_name': batch.batch_name,
            'scheduled_tasks': scheduled_count,
            'max_concurrency': batch.max_concurrency
        }
    
    def pause_batch(self, batch_id: int, wait_for_running: bool = True) -> Dict[str, Any]:
        """
        暂停批次
        
        Args:
            batch_id: 批次 ID
            wait_for_running: 是否等待正在运行的任务完成
            
        Returns:
            暂停结果
        """
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"批次 ID {batch_id} 不存在")
        
        if batch.status != 'running':
            raise ValueError(f"批次 '{batch.batch_name}' 未在运行中")
        
        # 更新批次状态
        batch.status = 'paused'
        batch.paused_at = datetime.utcnow()
        self.db.commit()
        
        # 取消队列中的任务（queued 状态）
        cancelled_count = self._cancel_queued_tasks(batch_id)
        
        return {
            'batch_id': batch_id,
            'batch_name': batch.batch_name,
            'cancelled_tasks': cancelled_count,
            'running_tasks': batch.running_tasks,
            'wait_for_running': wait_for_running
        }
    
    def resume_batch(self, batch_id: int) -> Dict[str, Any]:
        """恢复批次"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"批次 ID {batch_id} 不存在")
        
        if batch.status != 'paused':
            raise ValueError(f"批次 '{batch.batch_name}' 未处于暂停状态")
        
        # 更新批次状态
        batch.status = 'running'
        batch.paused_at = None
        self.db.commit()
        
        # 重新调度任务
        scheduled_count = self._schedule_pending_tasks(batch_id)
        
        return {
            'batch_id': batch_id,
            'batch_name': batch.batch_name,
            'scheduled_tasks': scheduled_count
        }
    
    def retry_failed_tasks(
        self,
        batch_id: int,
        instance_ids: Optional[List[str]] = None,
        reset_retry_count: bool = True
    ) -> Dict[str, Any]:
        """
        重试失败任务
        
        Args:
            batch_id: 批次 ID
            instance_ids: 指定实例 ID 列表，None 表示重试所有失败任务
            reset_retry_count: 是否重置重试计数
            
        Returns:
            重试结果统计
        """
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"批次 ID {batch_id} 不存在")
        
        # 查询失败任务
        query = self.db.query(BatchResult).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.status == 'failed'
            )
        )
        
        if instance_ids:
            query = query.filter(BatchResult.instance_id.in_(instance_ids))
        
        failed_tasks = query.all()
        
        # 重置任务状态
        retried_count = 0
        for task in failed_tasks:
            task.status = 'pending'
            task.error_message = None
            task.job_id = None
            
            if reset_retry_count:
                task.retry_count = 0
            
            retried_count += 1
        
        BatchService(self.db).refresh_batch_rollup(batch_id)
        self.db.commit()

        # 如果批次正在运行，立即调度
        if batch.status == 'running':
            scheduled_count = self._schedule_pending_tasks(batch_id)
        else:
            scheduled_count = 0
        
        return {
            'batch_id': batch_id,
            'retried_count': retried_count,
            'scheduled_count': scheduled_count
        }
    
    def run_single_task(self, batch_id: int, instance_id: str) -> Dict[str, Any]:
        """只调度一个 pending 子任务，不触发批次级 pending 调度。"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"批次 ID {batch_id} 不存在")
        if batch.status == 'running':
            raise ValueError("批次正在运行中，请先暂停批次后再单独执行子任务")

        task = BatchService(self.db).get_batch_task(batch_id, instance_id)
        if not task:
            raise ValueError(f"批次 {batch_id} 中不存在实例 {instance_id} 的任务")
        if task.status != 'pending':
            raise ValueError(f"只有 pending 子任务可以单独执行，当前状态: {task.status}")

        if not self._enqueue_task(task):
            raise ValueError(task.error_message or "子任务入队失败")

        return {
            'batch_id': batch_id,
            'task_id': task.id,
            'instance_id': task.instance_id,
            'status': task.status,
            'job_id': task.job_id,
        }

    def rerun_single_task(
        self,
        batch_id: int,
        instance_id: str,
        reset_retry_count: bool = True,
    ) -> Dict[str, Any]:
        """强制重跑一个非 pending 子任务，不触发批次级 pending 调度。"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"批次 ID {batch_id} 不存在")
        if batch.status == 'running':
            raise ValueError("批次正在运行中，请先暂停批次后再强制重跑子任务")

        task = BatchService(self.db).get_batch_task(batch_id, instance_id)
        if not task:
            raise ValueError(f"批次 {batch_id} 中不存在实例 {instance_id} 的任务")
        if task.status == 'pending':
            raise ValueError("pending 子任务无需强制重跑，请使用执行此任务")
        if task.status not in ('queued', 'running', 'retrying', 'completed', 'failed'):
            raise ValueError(f"当前状态不支持强制重跑: {task.status}")

        task.status = 'pending'
        task.job_id = None
        task.worker_id = None
        task.queued_at = None
        task.started_at = None
        task.completed_at = None
        task.duration_seconds = None
        task.error_message = None
        task.validation_success = None
        task.tests_passed = 0
        task.tests_failed = 0
        task.tests_total = 0
        task.result_summary = None
        task.patch_path = None
        task.trace_file_path = None
        task.validation_detail_path = None
        if reset_retry_count:
            task.retry_count = 0

        self.db.flush()
        BatchService(self.db).refresh_batch_rollup(batch_id)
        self.db.commit()

        if not self._enqueue_task(task):
            raise ValueError(task.error_message or "子任务入队失败")

        return {
            'batch_id': batch_id,
            'task_id': task.id,
            'instance_id': task.instance_id,
            'status': task.status,
            'job_id': task.job_id,
        }

    # ========== 核心调度逻辑 ==========

    def _schedule_pending_tasks(self, batch_id: int) -> int:
        """
        调度 pending 任务到队列
        
        根据批次的 max_concurrency 控制并发数
        使用数据库行锁防止并发调度冲突
        
        Returns:
            调度的任务数量
        """
        # ✅ 使用行锁锁定批次记录，防止并发调度冲突
        from sqlalchemy import text
        
        # 使用 SELECT ... FOR UPDATE 获取行锁
        batch = self.db.query(Batch).filter(Batch.id == batch_id).with_for_update().first()
        if not batch:
            return 0
        
        # ✅ 检查批次状态：只有 running 状态才能调度
        if batch.status != 'running':
            return 0
        
        rollup = BatchService(self.db).refresh_batch_rollup(batch_id) or {}
        available_slots = batch.max_concurrency - rollup.get('active_tasks', 0)
        if available_slots <= 0:
            return 0
        
        # 查询 pending 任务（按优先级）
        pending_tasks = self.db.query(BatchResult).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.status == 'pending'
            )
        ).order_by(BatchResult.created_at).limit(available_slots).all()
        
        scheduled_count = 0
        for task in pending_tasks:
            success = self._enqueue_task(task)
            if success:
                scheduled_count += 1
        
        return scheduled_count
    
    def _enqueue_task(self, task: BatchResult) -> bool:
        """
        将任务加入队列
        
        Args:
            task: BatchResult 对象
            
        Returns:
            是否成功加入队列
        """
        try:
            if RQ_AVAILABLE and self.queue:
                # 使用 RQ 加入队列
                job = self.queue.enqueue(
                    execute_single_task,
                    task_id=task.id,
                    job_timeout='2h',
                    result_ttl=86400  # 结果保留 24 小时
                )
                
                # 更新任务状态
                task.status = 'queued'
                task.job_id = job.id
                task.queued_at = datetime.utcnow()
                self.db.flush()
                BatchService(self.db).refresh_batch_rollup(task.batch_id)
                self.db.commit()

                return True
            else:
                # 同步执行（开发模式）
                print(f"Warning: RQ not available, executing task {task.id} synchronously")
                execute_single_task(task.id)
                return True
        except Exception as e:
            print(f"Error enqueueing task {task.id}: {e}")
            task.status = 'failed'
            task.error_message = f"入队失败: {str(e)}"
            self.db.flush()
            BatchService(self.db).refresh_batch_rollup(task.batch_id)
            self.db.commit()
            return False
    
    def _cancel_queued_tasks(self, batch_id: int) -> int:
        """
        取消队列中的任务
        
        将 queued 状态的任务改回 pending
        
        Returns:
            取消的任务数量
        """
        queued_tasks = self.db.query(BatchResult).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.status == 'queued'
            )
        ).all()
        
        cancelled_count = 0
        for task in queued_tasks:
            # 尝试取消 RQ job
            if RQ_AVAILABLE and self.queue and task.job_id:
                try:
                    from rq.job import Job
                    job = Job.fetch(task.job_id, connection=self.redis_conn)
                    job.cancel()
                except:
                    pass
            
            # 重置任务状态
            task.status = 'pending'
            task.job_id = None
            task.queued_at = None
            cancelled_count += 1
        
        BatchService(self.db).refresh_batch_rollup(batch_id)
        self.db.commit()
        return cancelled_count
    
    # ========== 任务完成回调 ==========
    
    def on_task_completed(self, task_id: int):
        """
        任务完成回调
        
        由 Worker 调用，用于：
        1. 调度下一个任务
        2. 检查批次是否完成
        """
        task = self.db.query(BatchResult).filter(BatchResult.id == task_id).first()
        if not task:
            return
        
        batch_id = task.batch_id
        
        # 1. 调度下一个任务（会自动检查批次状态）
        self._schedule_pending_tasks(batch_id)
        
        # 2. 检查批次是否完成（以 batch_results 实时聚合为准）
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return

        rollup = BatchService(self.db).refresh_batch_rollup(batch_id) or {}
        if (
            batch.status == 'running' and
            rollup.get('pending_tasks', 0) == 0 and
            rollup.get('active_tasks', 0) == 0
        ):
            batch.status = 'completed'
            batch.completed_at = datetime.utcnow()
            self.db.commit()
            print(f"[Batch {batch_id}] Completed: {batch.batch_name}")
        else:
            self.db.commit()
