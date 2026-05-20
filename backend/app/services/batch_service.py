"""
Batch Management Service for DUCC Evaluation System v2.0
批次管理服务 - 核心业务逻辑
"""
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.config import settings
from app.models import Batch, BatchResult, Dataset, DatasetInstance, Script
from app.schemas import BatchCreate, BatchUpdate, BatchAddTasksRequest


class BatchService:
    """批次管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_batch(self, batch_create: BatchCreate) -> Batch:
        """
        创建批次并生成任务实例
        
        工作流程：
        1. 检查批次是否已存在（如果追加模式）
        2. 查询数据集实例
        3. 创建/更新批次记录
        4. 创建 batch_results 记录（pending 状态）
        5. 返回批次信息
        """
        dataset = self.db.query(Dataset).filter(Dataset.id == batch_create.dataset_id).first()
        if not dataset:
            raise ValueError(f"数据集 {batch_create.dataset_id} 不存在")

        imported_count = self.db.query(DatasetInstance).filter(
            DatasetInstance.dataset_id == batch_create.dataset_id
        ).count()
        if imported_count == 0:
            raise ValueError("数据集已扫描但未导入实例，请先导入实例后再创建批次")

        execution_config = self._build_execution_config(
            script_id=batch_create.script_id,
            user_config=batch_create.execution_config or {}
        )

        # 1. 检查批次是否已存在
        existing_batch = self.db.query(Batch).filter(
            Batch.batch_name == batch_create.batch_name
        ).first()
        
        if existing_batch:
            if not batch_create.append_to_existing:
                raise ValueError(f"批次 '{batch_create.batch_name}' 已存在，如需追加请设置 append_to_existing=True")
            
            # 追加模式：检查 model 和 tag 是否一致
            if existing_batch.model != batch_create.model or existing_batch.tag != batch_create.tag:
                raise ValueError(
                    f"批次 '{batch_create.batch_name}' 的 model/tag 不一致。"
                    f"现有: {existing_batch.model}/{existing_batch.tag}, "
                    f"请求: {batch_create.model}/{batch_create.tag}"
                )
            
            batch = existing_batch
        else:
            # 创建新批次
            # 先创建临时 batch 获取 ID，然后生成 output_dir
            batch = Batch(
                batch_name=batch_create.batch_name,
                dataset_id=batch_create.dataset_id,
                script_id=batch_create.script_id,
                model=batch_create.model,
                tag=batch_create.tag,
                execution_config=execution_config,
                max_concurrency=batch_create.max_concurrency,
                priority=batch_create.priority,
                created_by=batch_create.created_by,
                status='created'
            )
            self.db.add(batch)
            self.db.flush()  # 获取 batch.id
            
            # 生成 output_dir（包含 batch_id）
            output_dir = self._generate_output_dir(batch_create.batch_name, batch.id)
            batch.output_dir = output_dir
        
        # 2. 查询数据集实例
        instances = self._query_instances(
            dataset_id=batch_create.dataset_id,
            instance_ids=batch_create.instance_ids,
            start_index=batch_create.start_index,
            end_index=batch_create.end_index,
            filter_conditions=batch_create.filter_conditions
        )
        
        if not instances:
            raise ValueError("未找到符合条件的数据集实例，请检查实例 ID、范围或筛选条件")
        
        # 3. 创建 batch_results 记录
        new_tasks_count = 0
        skipped_count = 0
        overwritten_count = 0
        
        for instance in instances:
            # 检查是否已存在
            existing_result = self.db.query(BatchResult).filter(
                and_(
                    BatchResult.batch_id == batch.id,
                    BatchResult.instance_id == instance.instance_id
                )
            ).first()
            
            if existing_result:
                if batch_create.overwrite_existing:
                    # 覆盖模式：重置状态
                    existing_result.status = 'pending'
                    existing_result.retry_count = 0
                    existing_result.max_retries = batch_create.max_retries
                    existing_result.error_message = None
                    existing_result.created_at = datetime.utcnow()
                    overwritten_count += 1
                else:
                    # 跳过已存在的实例
                    skipped_count += 1
                    continue
            else:
                # 创建新任务
                output_dir = self._generate_task_output_dir(batch.output_dir, instance.instance_id)
                
                batch_result = BatchResult(
                    batch_id=batch.id,
                    dataset_instance_id=instance.id,
                    instance_id=instance.instance_id,
                    model=batch_create.model,
                    tag=batch_create.tag,
                    status='pending',
                    max_retries=batch_create.max_retries,
                    output_dir=output_dir
                )
                self.db.add(batch_result)
                new_tasks_count += 1
        
        self.refresh_batch_rollup(batch.id)
        self.db.commit()
        self.db.refresh(batch)

        return batch, {
            'new_tasks': new_tasks_count,
            'skipped': skipped_count,
            'overwritten': overwritten_count,
            'total': new_tasks_count + overwritten_count
        }
    
    def add_tasks_to_batch(self, batch_id: int, request: BatchAddTasksRequest) -> Dict[str, int]:
        """向现有批次追加任务"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"批次 ID {batch_id} 不存在")
        
        # 查询实例
        instances = self._query_instances(
            dataset_id=batch.dataset_id,
            instance_ids=request.instance_ids,
            start_index=request.start_index,
            end_index=request.end_index,
            filter_conditions=request.filter_conditions
        )
        
        new_tasks_count = 0
        skipped_count = 0
        overwritten_count = 0
        
        for instance in instances:
            existing_result = self.db.query(BatchResult).filter(
                and_(
                    BatchResult.batch_id == batch_id,
                    BatchResult.instance_id == instance.instance_id
                )
            ).first()
            
            if existing_result:
                if request.overwrite_existing:
                    existing_result.status = 'pending'
                    existing_result.retry_count = 0
                    existing_result.error_message = None
                    overwritten_count += 1
                else:
                    skipped_count += 1
                    continue
            else:
                output_dir = self._generate_task_output_dir(batch.output_dir, instance.instance_id)
                
                batch_result = BatchResult(
                    batch_id=batch_id,
                    dataset_instance_id=instance.id,
                    instance_id=instance.instance_id,
                    model=batch.model,
                    tag=batch.tag,
                    status='pending',
                    max_retries=3,  # 默认重试次数
                    output_dir=output_dir
                )
                self.db.add(batch_result)
                new_tasks_count += 1
        
        self.refresh_batch_rollup(batch_id)
        self.db.commit()

        return {
            'new_tasks': new_tasks_count,
            'skipped': skipped_count,
            'overwritten': overwritten_count,
            'total': new_tasks_count + overwritten_count
        }
    
    def update_batch(self, batch_id: int, batch_update: BatchUpdate) -> Batch:
        """更新批次配置"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"批次 ID {batch_id} 不存在")
        
        update_data = batch_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(batch, key, value)
        
        batch.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(batch)
        
        return batch
    
    def get_batch(self, batch_id: int) -> Optional[Batch]:
        """获取批次信息"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            self.refresh_batch_rollup(batch_id)
        return batch
    
    def get_batch_by_name(self, batch_name: str) -> Optional[Batch]:
        """根据名称获取批次"""
        return self.db.query(Batch).filter(Batch.batch_name == batch_name).first()
    
    def list_batches(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        model: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[Batch]:
        """列出批次"""
        query = self.db.query(Batch)
        
        if status:
            query = query.filter(Batch.status == status)
        if model:
            query = query.filter(Batch.model == model)
        if tag:
            query = query.filter(Batch.tag == tag)
        
        batches = query.order_by(Batch.created_at.desc()).offset(skip).limit(limit).all()
        for batch in batches:
            self.refresh_batch_rollup(batch.id)
        return batches
    
    def delete_batch(self, batch_id: int) -> bool:
        """删除批次（级联删除所有 batch_results）"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return False
        
        self.db.delete(batch)
        self.db.commit()
        return True
    
    def get_batch_stats(self, batch_id: int) -> Optional[Dict[str, Any]]:
        """获取批次统计信息"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return None
        return self.build_batch_stats(batch)
    
    def get_batch_rollup(self, batch_id: int) -> Dict[str, Any]:
        """从 batch_results 实时聚合批次计数。"""
        status_rows = self.db.query(
            BatchResult.status,
            func.count(BatchResult.id)
        ).filter(
            BatchResult.batch_id == batch_id
        ).group_by(BatchResult.status).all()

        counts = {status: int(count) for status, count in status_rows}
        total_tasks = sum(counts.values())
        pending_tasks = counts.get('pending', 0)
        queued_tasks = counts.get('queued', 0)
        running_tasks = counts.get('running', 0)
        retrying_tasks = counts.get('retrying', 0)
        completed_tasks = counts.get('completed', 0)
        failed_tasks = counts.get('failed', 0)
        active_tasks = queued_tasks + running_tasks + retrying_tasks
        terminal_tasks = completed_tasks + failed_tasks

        validation_success_count = self.db.query(func.count(BatchResult.id)).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.status == 'completed',
                BatchResult.validation_success == True
            )
        ).scalar() or 0
        validation_failure_count = self.db.query(func.count(BatchResult.id)).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.status == 'completed',
                BatchResult.validation_success == False
            )
        ).scalar() or 0
        validation_unknown_count = max(completed_tasks - validation_success_count - validation_failure_count, 0)

        tests_passed = self.db.query(func.coalesce(func.sum(BatchResult.tests_passed), 0)).filter(
            BatchResult.batch_id == batch_id
        ).scalar() or 0
        tests_failed = self.db.query(func.coalesce(func.sum(BatchResult.tests_failed), 0)).filter(
            BatchResult.batch_id == batch_id
        ).scalar() or 0
        tests_total = self.db.query(func.coalesce(func.sum(BatchResult.tests_total), 0)).filter(
            BatchResult.batch_id == batch_id
        ).scalar() or 0
        avg_duration = self.db.query(func.avg(BatchResult.duration_seconds)).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.duration_seconds != None
            )
        ).scalar()
        total_duration = self.db.query(func.sum(BatchResult.duration_seconds)).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.duration_seconds != None
            )
        ).scalar()

        return {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'queued_tasks': queued_tasks,
            'running_tasks': running_tasks,
            'retrying_tasks': retrying_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'active_tasks': active_tasks,
            'terminal_tasks': terminal_tasks,
            'validation_success_count': validation_success_count,
            'validation_failure_count': validation_failure_count,
            'validation_unknown_count': validation_unknown_count,
            'tests_passed': int(tests_passed),
            'tests_failed': int(tests_failed),
            'tests_total': int(tests_total),
            'avg_duration': float(avg_duration) if avg_duration is not None else None,
            'total_duration': float(total_duration) if total_duration is not None else None,
        }

    def refresh_batch_rollup(self, batch_id: int, commit: bool = False) -> Optional[Dict[str, Any]]:
        """回写批次缓存计数字段，避免数据库 trigger 缺失导致调度不准。"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return None

        rollup = self.get_batch_rollup(batch_id)
        batch.total_tasks = rollup['total_tasks']
        batch.pending_tasks = rollup['pending_tasks']
        batch.queued_tasks = rollup['queued_tasks']
        batch.running_tasks = rollup['running_tasks']
        batch.completed_tasks = rollup['completed_tasks']
        batch.failed_tasks = rollup['failed_tasks']
        batch.current_running = rollup['active_tasks']
        batch.updated_at = datetime.utcnow()

        if commit:
            self.db.commit()
        return rollup

    def build_batch_stats(self, batch: Batch) -> Dict[str, Any]:
        """构造批次实时统计响应。"""
        rollup = self.refresh_batch_rollup(batch.id) or self.get_batch_rollup(batch.id)
        total_tasks = rollup['total_tasks']
        completed_tasks = rollup['completed_tasks']
        failed_tasks = rollup['failed_tasks']
        terminal_tasks = rollup['terminal_tasks']
        active_tasks = rollup['active_tasks']
        pending_tasks = rollup['pending_tasks']
        validation_success_count = rollup['validation_success_count']
        validation_failure_count = rollup['validation_failure_count']
        tests_total = rollup['tests_total']

        completion_rate = terminal_tasks / total_tasks if total_tasks else 0
        task_success_rate = completed_tasks / total_tasks if total_tasks else 0
        task_failure_rate = failed_tasks / total_tasks if total_tasks else 0
        validation_success_rate = validation_success_count / completed_tasks if completed_tasks else None
        validation_failure_rate = validation_failure_count / completed_tasks if completed_tasks else None
        evaluation_success_rate = validation_success_count / total_tasks if total_tasks else 0
        evaluation_failure_rate = (failed_tasks + validation_failure_count) / total_tasks if total_tasks else 0
        test_pass_rate = rollup['tests_passed'] / tests_total if tests_total else None

        effective_status = self._compute_effective_status(batch, rollup)
        outcome = self._compute_outcome(batch, rollup)

        return {
            'batch_id': batch.id,
            'batch_name': batch.batch_name,
            'status': batch.status,
            'effective_status': effective_status,
            'outcome': outcome,
            **rollup,
            'completion_rate': completion_rate,
            'task_success_rate': task_success_rate,
            'task_failure_rate': task_failure_rate,
            'success_rate': task_success_rate,
            'failure_rate': task_failure_rate,
            'validation_success_rate': validation_success_rate,
            'validation_failure_rate': validation_failure_rate,
            'evaluation_success_rate': evaluation_success_rate,
            'evaluation_failure_rate': evaluation_failure_rate,
            'test_pass_rate': test_pass_rate,
        }

    def _compute_effective_status(self, batch: Batch, rollup: Dict[str, Any]) -> str:
        if batch.status == 'paused':
            return 'paused'
        if rollup['active_tasks'] > 0:
            return 'running'
        if rollup['total_tasks'] > 0 and rollup['terminal_tasks'] == rollup['total_tasks']:
            return 'completed'
        if rollup['pending_tasks'] > 0:
            return 'created'
        return batch.status

    def _compute_outcome(self, batch: Batch, rollup: Dict[str, Any]) -> str:
        if batch.status == 'paused':
            return 'paused'
        if rollup['active_tasks'] > 0 or rollup['pending_tasks'] > 0:
            return 'in_progress'
        if rollup['total_tasks'] == 0:
            return 'not_started'
        if rollup['terminal_tasks'] == rollup['total_tasks']:
            if rollup['failed_tasks'] == 0 and rollup['validation_failure_count'] == 0:
                return 'completed_successfully'
            return 'completed_with_failures'
        return 'unknown'

    def get_batch_tasks(
        self,
        batch_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[BatchResult]:
        """获取批次的任务列表"""
        query = self.db.query(BatchResult).filter(BatchResult.batch_id == batch_id)
        
        if status:
            query = query.filter(BatchResult.status == status)
        
        return query.order_by(BatchResult.created_at).offset(skip).limit(limit).all()
    
    def get_batch_task(self, batch_id: int, instance_id: str) -> Optional[BatchResult]:
        """获取批次中指定实例的任务"""
        return self.db.query(BatchResult).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.instance_id == instance_id
            )
        ).first()
    
    # ========== 私有方法 ==========
    
    def _build_execution_config(self, script_id: int, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge script argument defaults with user-provided values."""
        script = self.db.query(Script).filter(Script.id == script_id).first()
        if not script:
            raise ValueError(f"脚本 {script_id} 不存在")

        reserved_config = self._extract_reserved_execution_config(user_config)
        argument_schema = script.argument_schema or []
        if not argument_schema:
            config = {
                key: value
                for key, value in user_config.items()
                if self._normalize_execution_config_key(key) not in {'ducc-api-provider', 'anthropic-model'}
            }
            config.update(reserved_config)
            return config

        allowed_names = {arg.get('name') for arg in argument_schema if arg.get('name')}
        config = {}
        for arg in argument_schema:
            name = arg.get('name')
            if not name:
                continue
            if 'default' in arg:
                config[name] = arg.get('default')

        for key, value in user_config.items():
            normalized_key = self._normalize_execution_config_key(key)
            if normalized_key in allowed_names:
                config[normalized_key] = value

        config.update(reserved_config)
        return config

    def _extract_reserved_execution_config(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        reserved: Dict[str, Any] = {}
        for key, value in user_config.items():
            normalized_key = self._normalize_execution_config_key(key)
            self._reject_secret_execution_config(normalized_key, value)

            if normalized_key == 'ducc-api-provider':
                if value not in ('comate', 'xinghe', 'qianfan'):
                    raise ValueError(f"不支持的 API 来源: {value}")
                if value != 'comate':
                    reserved[normalized_key] = value
            elif normalized_key == 'anthropic-model' and value:
                reserved[normalized_key] = value
        return reserved

    def _normalize_execution_config_key(self, key: str) -> str:
        normalized_key = key[2:] if key.startswith('--') else key
        return normalized_key.replace('_', '-')

    def _reject_secret_execution_config(self, key: str, value: Any):
        if key in {'anthropic-auth-token', 'api-key', 'api_key', 'token'}:
            raise ValueError("API token 不允许通过批次参数提交，请放到 data/config/model_providers.json")
        if isinstance(value, str) and re.match(r'^(sk-|bce-v3/)', value):
            raise ValueError("API token 不允许通过批次参数提交，请放到 data/config/model_providers.json")

    def _query_instances(
        self,
        dataset_id: int,
        instance_ids: Optional[List[str]] = None,
        start_index: Optional[int] = None,
        end_index: Optional[int] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[DatasetInstance]:
        """查询数据集实例"""
        query = self.db.query(DatasetInstance).filter(
            DatasetInstance.dataset_id == dataset_id
        )
        
        # 1. 按 instance_ids 过滤（优先级最高）
        if instance_ids:
            query = query.filter(DatasetInstance.instance_id.in_(instance_ids))
        else:
            # 2. 按索引范围过滤
            if start_index is not None or end_index is not None:
                # 这里简化处理，实际应该根据数据集顺序
                query = query.order_by(DatasetInstance.id)
                if start_index is not None:
                    query = query.offset(start_index)
                if end_index is not None and start_index is not None:
                    query = query.limit(end_index - start_index)
        
        # 3. 按 JSONB 字段过滤
        if filter_conditions:
            for key, value in filter_conditions.items():
                if key == 'repo_language':
                    # 直接字段过滤
                    query = query.filter(DatasetInstance.repo_language == value)
                else:
                    # JSONB 字段过滤
                    query = query.filter(DatasetInstance.data[key].astext == str(value))
        
        return query.all()
    
    def _generate_output_dir(self, batch_name: str, batch_id: int) -> str:
        """生成批次输出目录（包含 batch_id 避免冲突）"""
        base_dir = os.getenv('DUCC_OUTPUT_BASE_DIR', settings.OUTPUTS_DIR)
        os.makedirs(base_dir, exist_ok=True)
        safe_batch_name = batch_name.replace('/', '_').replace(':', '_')
        return os.path.abspath(os.path.join(base_dir, f"{safe_batch_name}_{batch_id}"))
    
    def _generate_task_output_dir(self, batch_output_dir: str, instance_id: str) -> str:
        """生成任务输出目录"""
        safe_instance_id = instance_id.replace('/', '_').replace(':', '_')
        return os.path.join(batch_output_dir, 'tasks', safe_instance_id)
