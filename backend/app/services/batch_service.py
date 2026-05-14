"""
Batch Management Service for DUCC Evaluation System v2.0
批次管理服务 - 核心业务逻辑
"""
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

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
                execution_config=batch_create.execution_config,
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
            raise ValueError("未找到符合条件的数据集实例")
        
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
        return self.db.query(Batch).filter(Batch.id == batch_id).first()
    
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
        
        return query.order_by(Batch.created_at.desc()).offset(skip).limit(limit).all()
    
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
        from sqlalchemy import func
        
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return None
        
        # 计算成功率
        success_rate = batch.completed_tasks / batch.total_tasks if batch.total_tasks > 0 else 0
        
        # 计算验证通过率
        validation_success_count = self.db.query(func.count(BatchResult.id)).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.status == 'completed',
                BatchResult.validation_success == True
            )
        ).scalar()
        
        validation_success_rate = validation_success_count / batch.completed_tasks if batch.completed_tasks > 0 else None
        
        # 计算平均耗时
        avg_duration = self.db.query(func.avg(BatchResult.duration_seconds)).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.status == 'completed'
            )
        ).scalar()
        
        total_duration = self.db.query(func.sum(BatchResult.duration_seconds)).filter(
            and_(
                BatchResult.batch_id == batch_id,
                BatchResult.status == 'completed'
            )
        ).scalar()
        
        return {
            'batch_id': batch_id,
            'batch_name': batch.batch_name,
            'status': batch.status,
            'total_tasks': batch.total_tasks,
            'pending_tasks': batch.pending_tasks,
            'queued_tasks': batch.queued_tasks,
            'running_tasks': batch.running_tasks,
            'completed_tasks': batch.completed_tasks,
            'failed_tasks': batch.failed_tasks,
            'success_rate': success_rate,
            'validation_success_rate': validation_success_rate,
            'avg_duration': float(avg_duration) if avg_duration else None,
            'total_duration': float(total_duration) if total_duration else None
        }
    
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
        base_dir = os.getenv('DUCC_OUTPUT_BASE_DIR', '/path/to/evaluation/data/outputs')
        safe_batch_name = batch_name.replace('/', '_').replace(':', '_')
        return os.path.join(base_dir, f"{safe_batch_name}_{batch_id}")
    
    def _generate_task_output_dir(self, batch_output_dir: str, instance_id: str) -> str:
        """生成任务输出目录"""
        safe_instance_id = instance_id.replace('/', '_').replace(':', '_')
        return os.path.join(batch_output_dir, 'tasks', safe_instance_id)
