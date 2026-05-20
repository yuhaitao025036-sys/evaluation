"""Task Groups API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas import TaskGroup, TaskGroupCreate, TaskGroupWithDetails
from app.services.task_group_service import TaskGroupService
from app.config import get_model_by_id
from app import models

router = APIRouter()


@router.post("", response_model=TaskGroup)
async def create_task_group(
    request: TaskGroupCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new task group
    
    This will:
    1. Validate the model, dataset, and script
    2. Apply filter conditions to get matching instances
    3. Create concurrent tasks based on the concurrency setting
    4. Create task instances for each data instance
    """
    try:
        task_group = TaskGroupService.create_task_group(
            db=db,
            name=request.name,
            dataset_id=request.dataset_id,
            script_id=request.script_id,
            model=request.model,
            tag=request.tag,
            concurrency=request.concurrency,
            model_params=request.model_params,
            filter_conditions=request.filter_conditions,
            script_args=request.script_args,
            start_index=request.start_index,
            end_index=request.end_index,
            description=request.description
        )
        
        return task_group
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating task group: {str(e)}")


@router.get("", response_model=List[TaskGroup])
async def list_task_groups(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    model: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all task groups with optional filters"""
    query = db.query(models.TaskGroup)
    
    if status:
        query = query.filter(models.TaskGroup.status == status)
    if model:
        query = query.filter(models.TaskGroup.model == model)
    if tag:
        query = query.filter(models.TaskGroup.tag == tag)
    
    task_groups = query.offset(skip).limit(limit).all()
    return task_groups


@router.get("/{group_id}", response_model=TaskGroupWithDetails)
async def get_task_group(group_id: int, db: Session = Depends(get_db)):
    """Get task group by ID with details"""
    task_group = db.query(models.TaskGroup).filter(
        models.TaskGroup.id == group_id
    ).first()
    
    if not task_group:
        raise HTTPException(status_code=404, detail="Task group not found")
    
    # Get related information
    dataset = db.query(models.Dataset).filter(
        models.Dataset.id == task_group.dataset_id
    ).first()
    
    script = db.query(models.Script).filter(
        models.Script.id == task_group.script_id
    ).first()
    
    model_info = get_model_by_id(task_group.model)
    
    # Convert to dict and add details
    result = task_group.__dict__.copy()
    result['dataset'] = dataset
    result['script'] = script
    result['model_info'] = model_info
    
    return result


@router.get("/{group_id}/progress")
async def get_task_group_progress(group_id: int, db: Session = Depends(get_db)):
    """Get task group progress statistics"""
    try:
        stats = TaskGroupService.get_task_group_progress(db, group_id)
        
        task_group = db.query(models.TaskGroup).filter(
            models.TaskGroup.id == group_id
        ).first()
        
        return {
            "task_group_id": group_id,
            "name": task_group.name if task_group else None,
            "status": task_group.status if task_group else None,
            "statistics": stats
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{group_id}/instances")
async def get_task_group_instances(
    group_id: int,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get task instances from a task group"""
    # Verify task group exists
    task_group = db.query(models.TaskGroup).filter(
        models.TaskGroup.id == group_id
    ).first()
    
    if not task_group:
        raise HTTPException(status_code=404, detail="Task group not found")
    
    # Query task instances
    query = db.query(models.TaskInstance).join(models.Task).filter(
        models.Task.group_id == group_id
    )
    
    if status:
        query = query.filter(models.TaskInstance.status == status)
    
    instances = query.offset(skip).limit(limit).all()
    
    return {
        "task_group_id": group_id,
        "total": query.count(),
        "instances": instances
    }


@router.post("/{group_id}/start")
async def start_task_group(group_id: int, db: Session = Depends(get_db)):
    """Start a task group (enqueue tasks to RQ)"""
    from redis import Redis
    from rq import Queue
    from app.config import settings
    from app.worker import execute_task_instance
    from datetime import datetime
    
    task_group = db.query(models.TaskGroup).filter(
        models.TaskGroup.id == group_id
    ).first()
    
    if not task_group:
        raise HTTPException(status_code=404, detail="Task group not found")
    
    if task_group.status not in ['created', 'paused']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start task group with status: {task_group.status}"
        )
    
    # Connect to Redis and create queue
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue(settings.RQ_QUEUE_NAME, connection=redis_conn)
    
    # Get all task instances for this task group
    tasks = db.query(models.Task).filter(models.Task.group_id == group_id).all()
    enqueued_count = 0
    
    for task in tasks:
        # Update task status
        task.status = 'queued'
        
        # Get all pending task instances
        instances = db.query(models.TaskInstance).filter(
            models.TaskInstance.task_id == task.id,
            models.TaskInstance.status == 'pending'
        ).all()
        
        # Enqueue each instance
        for instance in instances:
            queue.enqueue(
                execute_task_instance,
                instance.id,
                job_timeout=settings.TASK_TIMEOUT_SECONDS,
                result_ttl=86400  # Keep results for 24 hours
            )
            enqueued_count += 1
    
    # Update task group status
    task_group.status = 'queued'
    task_group.started_at = datetime.now()
    db.commit()
    
    return {
        "message": f"Task group {group_id} started, {enqueued_count} instances enqueued",
        "status": task_group.status,
        "enqueued_count": enqueued_count
    }


@router.post("/{group_id}/pause")
async def pause_task_group(group_id: int, db: Session = Depends(get_db)):
    """Pause a running task group"""
    task_group = db.query(models.TaskGroup).filter(
        models.TaskGroup.id == group_id
    ).first()
    
    if not task_group:
        raise HTTPException(status_code=404, detail="Task group not found")
    
    if task_group.status not in ['running', 'queued']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause task group with status: {task_group.status}"
        )
    
    # Note: This doesn't cancel already-running jobs in RQ
    # It just prevents new ones from being started
    task_group.status = 'paused'
    db.commit()
    
    return {
        "message": f"Task group {group_id} paused (running jobs will complete)",
        "status": task_group.status
    }
