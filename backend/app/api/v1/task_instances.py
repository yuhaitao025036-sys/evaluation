"""Task instances API endpoints"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models import TaskInstance, Task, Dataset
from app.schemas import TaskInstanceResponse, TaskInstanceDetail

router = APIRouter()


@router.get("", response_model=List[TaskInstanceResponse])
def list_task_instances(
    task_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    instance_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List task instances with filtering
    
    Supports filtering by:
    - task_id: Parent task
    - tag: Comparison tag
    - model: Model used
    - status: Execution status
    - instance_id: Specific instance
    """
    query = db.query(TaskInstance)
    
    if task_id:
        query = query.filter(TaskInstance.task_id == task_id)
    
    if tag:
        query = query.filter(TaskInstance.tag == tag)
    
    if model:
        query = query.filter(TaskInstance.model == model)
    
    if status:
        query = query.filter(TaskInstance.status == status)
    
    if instance_id:
        query = query.filter(TaskInstance.instance_id.like(f"%{instance_id}%"))
    
    # Order by creation time (most recent first)
    query = query.order_by(TaskInstance.id.desc())
    
    total = query.count()
    instances = query.offset(offset).limit(limit).all()
    
    return instances


@router.get("/{instance_id}", response_model=TaskInstanceDetail)
def get_task_instance(
    instance_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific task instance
    
    Includes:
    - Full execution details
    - Generated patch
    - Test results
    - Summary data
    """
    instance = db.query(TaskInstance).filter(TaskInstance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Task instance not found")
    
    # Load related task information
    task = db.query(Task).filter(Task.id == instance.task_id).first()
    dataset = None
    if task:
        dataset = db.query(Dataset).filter(Dataset.id == task.dataset_id).first()
    
    return {
        "id": instance.id,
        "task_id": instance.task_id,
        "instance_id": instance.instance_id,
        "tag": instance.tag,
        "model": instance.model,
        "model_params": instance.model_params,
        "status": instance.status,
        "validation_success": instance.validation_success,
        "test_passed": instance.test_passed,
        "test_failed": instance.test_failed,
        "test_errors": instance.test_errors,
        "generated_patch": instance.generated_patch,
        "summary": instance.summary,
        "started_at": instance.started_at,
        "completed_at": instance.completed_at,
        "duration_seconds": instance.duration_seconds,
        "task_dir": instance.task_dir,
        "task_name": task.name if task else None,
        "dataset_name": dataset.name if dataset else None
    }


@router.get("/by-instance-id/{instance_id}", response_model=List[TaskInstanceResponse])
def get_instances_by_instance_id(
    instance_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all runs for a specific instance_id (across different tags/models)
    
    This is useful for comparing how the same instance performed
    with different models or configurations
    """
    instances = db.query(TaskInstance).filter(
        TaskInstance.instance_id == instance_id
    ).order_by(TaskInstance.tag, TaskInstance.model).all()
    
    if not instances:
        raise HTTPException(
            status_code=404, 
            detail=f"No task instances found for instance_id: {instance_id}"
        )
    
    return instances


@router.post("/{instance_id}/retry")
def retry_task_instance(
    instance_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark a task instance for retry
    
    Resets status to 'pending' so it can be picked up by workers again
    """
    instance = db.query(TaskInstance).filter(TaskInstance.id == instance_id).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Task instance not found")
    
    if instance.status in ['running']:
        raise HTTPException(
            status_code=400, 
            detail="Cannot retry a running task instance"
        )
    
    # Reset instance status
    instance.status = 'pending'
    instance.started_at = None
    instance.completed_at = None
    instance.duration_seconds = None
    instance.summary = None
    instance.generated_patch = None
    instance.validation_success = None
    instance.test_passed = 0
    instance.test_failed = 0
    instance.test_errors = 0
    
    db.commit()
    db.refresh(instance)
    
    return {
        "message": "Task instance marked for retry",
        "instance_id": instance_id,
        "status": instance.status
    }


@router.get("/stats/summary")
def get_instances_summary(
    tag: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    dataset_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for task instances
    
    Returns aggregated stats filtered by tag, model, and/or dataset
    """
    query = db.query(TaskInstance)
    
    if tag:
        query = query.filter(TaskInstance.tag == tag)
    
    if model:
        query = query.filter(TaskInstance.model == model)
    
    if dataset_id:
        query = query.join(TaskInstance.task).filter(
            TaskInstance.task.has(dataset_id=dataset_id)
        )
    
    instances = query.all()
    
    total = len(instances)
    completed = sum(1 for i in instances if i.status == 'completed')
    failed = sum(1 for i in instances if i.status == 'failed')
    running = sum(1 for i in instances if i.status == 'running')
    pending = sum(1 for i in instances if i.status == 'pending')
    success = sum(1 for i in instances if i.validation_success)
    
    # Calculate average duration for completed tasks
    avg_duration = None
    if completed > 0:
        durations = [i.duration_seconds for i in instances if i.duration_seconds]
        if durations:
            avg_duration = sum(durations) / len(durations)
    
    return {
        "total_instances": total,
        "status_breakdown": {
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending
        },
        "success_count": success,
        "success_rate": success / total if total > 0 else 0,
        "avg_duration_seconds": avg_duration,
        "filters": {
            "tag": tag,
            "model": model,
            "dataset_id": dataset_id
        }
    }
