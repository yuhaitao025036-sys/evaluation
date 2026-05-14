"""Task Group service - handles task group creation and management"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models import TaskGroup, Task, TaskInstance, Dataset, Script
from app.services.dataset_service import DatasetService
from app.config import validate_model_id, get_model_by_id
from datetime import datetime
import math


class TaskGroupService:
    """Service for managing task groups"""
    
    @staticmethod
    def create_task_group(
        db: Session,
        name: str,
        dataset_id: int,
        script_id: int,
        model: str,
        tag: str,
        concurrency: int = 1,
        model_params: Optional[Dict[str, Any]] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
        script_args: Optional[str] = None,
        start_index: int = 0,
        end_index: Optional[int] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> TaskGroup:
        """
        Create a new task group with automatic batch splitting
        
        Args:
            name: Task group name
            dataset_id: Dataset ID
            script_id: Script ID
            model: Model ID (e.g., 'gpt-4-turbo')
            tag: Experiment tag (e.g., 'baseline')
            concurrency: Number of concurrent workers
            model_params: Model parameters
            filter_conditions: Filter conditions for dataset
            script_args: Script arguments
            start_index: Start index
            end_index: End index
            description: Task group description
            created_by: Creator name
        
        Returns:
            Created TaskGroup
        """
        # Validate model
        if not validate_model_id(model):
            raise ValueError(f"Invalid model ID: {model}")
        
        # Validate dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Validate script
        script = db.query(Script).filter(Script.id == script_id).first()
        if not script:
            raise ValueError(f"Script {script_id} not found")
        
        # Get filtered instance IDs
        instance_ids = DatasetService.get_filtered_instance_ids(
            db=db,
            dataset_id=dataset_id,
            filter_conditions=filter_conditions,
            start_index=start_index,
            end_index=end_index
        )
        
        total_instances = len(instance_ids)
        if total_instances == 0:
            raise ValueError("No instances match the filter conditions")
        
        # Calculate batch size (distribute evenly across concurrent workers)
        batch_size = math.ceil(total_instances / concurrency)
        total_batches = concurrency
        
        # Create task group
        task_group = TaskGroup(
            name=name,
            description=description,
            dataset_id=dataset_id,
            script_id=script_id,
            model=model,
            model_params=model_params,
            tag=tag,
            script_args=script_args,
            batch_size=batch_size,
            total_batches=total_batches,
            concurrency=concurrency,
            filter_conditions=filter_conditions,
            start_index=start_index,
            end_index=end_index or start_index + total_instances,
            total_instances=total_instances,
            status='created',
            completed_batches=0,
            completed_instances=0,
            failed_instances=0,
            created_by=created_by
        )
        
        db.add(task_group)
        db.flush()  # Get task_group.id
        
        # Create concurrent tasks (batches)
        tasks_created = []
        for i in range(concurrency):
            batch_start = i * batch_size
            batch_end = min((i + 1) * batch_size, total_instances)
            
            if batch_start >= total_instances:
                break
            
            task = Task(
                name=f"{name} - Batch {i+1}/{concurrency}",
                description=f"Batch {i+1} of {concurrency} concurrent tasks",
                dataset_id=dataset_id,
                script_id=script_id,
                group_id=task_group.id,
                tag=tag,
                script_args=script_args,
                start_index=start_index + batch_start,
                end_index=start_index + batch_end,
                status='created',
                total_instances=batch_end - batch_start,
                completed_instances=0,
                failed_instances=0,
                created_by=created_by
            )
            
            db.add(task)
            db.flush()
            
            # Create task instances for this batch
            batch_instance_ids = instance_ids[batch_start:batch_end]
            for inst_id in batch_instance_ids:
                task_instance = TaskInstance(
                    task_id=task.id,
                    instance_id=inst_id,
                    tag=tag,
                    model=model,
                    model_params=model_params,
                    status='pending'
                )
                db.add(task_instance)
            
            tasks_created.append(task)
        
        db.commit()
        db.refresh(task_group)
        
        return task_group
    
    @staticmethod
    def get_task_group_progress(db: Session, group_id: int) -> Dict[str, Any]:
        """Get task group progress statistics"""
        group = db.query(TaskGroup).filter(TaskGroup.id == group_id).first()
        if not group:
            raise ValueError(f"Task group {group_id} not found")
        
        # Get instance statistics
        instances = db.query(TaskInstance).join(Task).filter(
            Task.group_id == group_id
        ).all()
        
        stats = {
            "total": len(instances),
            "pending": sum(1 for i in instances if i.status == 'pending'),
            "running": sum(1 for i in instances if i.status == 'running'),
            "completed": sum(1 for i in instances if i.status == 'completed'),
            "failed": sum(1 for i in instances if i.status == 'failed'),
            "success_count": sum(1 for i in instances if i.validation_success == True),
            "progress_percentage": 0.0
        }
        
        if stats["total"] > 0:
            stats["progress_percentage"] = (stats["completed"] + stats["failed"]) / stats["total"] * 100
        
        return stats
    
    @staticmethod
    def update_task_group_status(db: Session, group_id: int):
        """Update task group status based on task instances"""
        group = db.query(TaskGroup).filter(TaskGroup.id == group_id).first()
        if not group:
            return
        
        stats = TaskGroupService.get_task_group_progress(db, group_id)
        
        # Update counts
        group.completed_instances = stats["completed"]
        group.failed_instances = stats["failed"]
        
        # Update status
        if stats["completed"] + stats["failed"] >= stats["total"]:
            group.status = 'completed'
            if not group.completed_at:
                group.completed_at = datetime.now()
        elif stats["running"] > 0:
            group.status = 'running'
            if not group.started_at:
                group.started_at = datetime.now()
        
        db.commit()
