"""Comparisons API endpoints"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.database import get_db
from app.models import TaskInstance, Dataset, TaskGroup
from app.schemas import (
    CompareModelsRequest,
    CompareTagsRequest,
    InstanceComparisonRequest,
    TaskInstanceComparison,
    ModelComparisonResult,
    TagComparisonResult,
    InstanceComparisonDetail
)

router = APIRouter()


@router.post("/compare-by-models", response_model=ModelComparisonResult)
def compare_by_models(
    request: CompareModelsRequest,
    db: Session = Depends(get_db)
):
    """
    Compare results across different models for the same tag
    
    Key use case: Compare how different models perform on same baseline data
    """
    # Validate models exist
    instances_by_model = {}
    
    for model_id in request.model_ids:
        # Query task instances filtered by tag and model
        query = db.query(TaskInstance).filter(
            TaskInstance.tag == request.tag,
            TaskInstance.model == model_id
        )
        
        # Optional dataset filter
        if request.dataset_id:
            query = query.join(TaskInstance.task).filter(
                TaskInstance.task.has(dataset_id=request.dataset_id)
            )
        
        instances = query.all()
        instances_by_model[model_id] = instances
    
    # Build comparison stats
    comparison_stats = {}
    for model_id, instances in instances_by_model.items():
        total = len(instances)
        completed = sum(1 for i in instances if i.status == 'completed')
        failed = sum(1 for i in instances if i.status == 'failed')
        success = sum(1 for i in instances if i.validation_success)
        
        avg_duration = None
        if completed > 0:
            durations = [i.duration_seconds for i in instances if i.duration_seconds]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        comparison_stats[model_id] = {
            "total_instances": total,
            "completed": completed,
            "failed": failed,
            "success_count": success,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration_seconds": avg_duration
        }
    
    # Get instance-level comparisons
    instance_comparisons = []
    
    # Find common instance_ids across all models
    if instances_by_model:
        first_model = list(instances_by_model.keys())[0]
        common_instance_ids = {i.instance_id for i in instances_by_model[first_model]}
        
        for model_id in request.model_ids[1:]:
            model_instance_ids = {i.instance_id for i in instances_by_model[model_id]}
            common_instance_ids &= model_instance_ids
        
        # Build comparisons for common instances
        for instance_id in sorted(common_instance_ids):
            instance_data = {
                "instance_id": instance_id,
                "results_by_model": {}
            }
            
            for model_id in request.model_ids:
                instance = next(
                    (i for i in instances_by_model[model_id] if i.instance_id == instance_id),
                    None
                )
                if instance:
                    instance_data["results_by_model"][model_id] = {
                        "status": instance.status,
                        "validation_success": instance.validation_success,
                        "duration_seconds": instance.duration_seconds,
                        "test_passed": instance.test_passed,
                        "test_failed": instance.test_failed
                    }
            
            instance_comparisons.append(instance_data)
    
    return {
        "tag": request.tag,
        "model_ids": request.model_ids,
        "dataset_id": request.dataset_id,
        "comparison_stats": comparison_stats,
        "instance_comparisons": instance_comparisons[:100]  # Limit to 100 for performance
    }


@router.post("/compare-by-tags", response_model=TagComparisonResult)
def compare_by_tags(
    request: CompareTagsRequest,
    db: Session = Depends(get_db)
):
    """
    Compare results across different tags for the same model
    
    Key use case: Compare baseline vs experiment runs with same model
    """
    instances_by_tag = {}
    
    for tag in request.tags:
        # Query task instances filtered by model and tag
        query = db.query(TaskInstance).filter(
            TaskInstance.tag == tag
        )
        
        # Model filter
        if request.model_id:
            query = query.filter(TaskInstance.model == request.model_id)
        
        # Optional dataset filter
        if request.dataset_id:
            query = query.join(TaskInstance.task).filter(
                TaskInstance.task.has(dataset_id=request.dataset_id)
            )
        
        instances = query.all()
        instances_by_tag[tag] = instances
    
    # Build comparison stats
    comparison_stats = {}
    for tag, instances in instances_by_tag.items():
        total = len(instances)
        completed = sum(1 for i in instances if i.status == 'completed')
        failed = sum(1 for i in instances if i.status == 'failed')
        success = sum(1 for i in instances if i.validation_success)
        
        avg_duration = None
        if completed > 0:
            durations = [i.duration_seconds for i in instances if i.duration_seconds]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        comparison_stats[tag] = {
            "total_instances": total,
            "completed": completed,
            "failed": failed,
            "success_count": success,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration_seconds": avg_duration
        }
    
    # Get instance-level comparisons
    instance_comparisons = []
    
    # Find common instance_ids across all tags
    if instances_by_tag:
        first_tag = list(instances_by_tag.keys())[0]
        common_instance_ids = {i.instance_id for i in instances_by_tag[first_tag]}
        
        for tag in request.tags[1:]:
            tag_instance_ids = {i.instance_id for i in instances_by_tag[tag]}
            common_instance_ids &= tag_instance_ids
        
        # Build comparisons for common instances
        for instance_id in sorted(common_instance_ids):
            instance_data = {
                "instance_id": instance_id,
                "results_by_tag": {}
            }
            
            for tag in request.tags:
                instance = next(
                    (i for i in instances_by_tag[tag] if i.instance_id == instance_id),
                    None
                )
                if instance:
                    instance_data["results_by_tag"][tag] = {
                        "status": instance.status,
                        "validation_success": instance.validation_success,
                        "duration_seconds": instance.duration_seconds,
                        "test_passed": instance.test_passed,
                        "test_failed": instance.test_failed
                    }
            
            instance_comparisons.append(instance_data)
    
    return {
        "model_id": request.model_id,
        "tags": request.tags,
        "dataset_id": request.dataset_id,
        "comparison_stats": comparison_stats,
        "instance_comparisons": instance_comparisons[:100]  # Limit to 100 for performance
    }


@router.post("/compare-instance", response_model=InstanceComparisonDetail)
def compare_single_instance(
    request: InstanceComparisonRequest,
    db: Session = Depends(get_db)
):
    """
    Compare a single instance across different tags and/or models
    
    Returns detailed information including patches and test results
    """
    query = db.query(TaskInstance).filter(
        TaskInstance.instance_id == request.instance_id
    )
    
    # Filter by tags if provided
    if request.tags:
        query = query.filter(TaskInstance.tag.in_(request.tags))
    
    # Filter by models if provided
    if request.model_ids:
        query = query.filter(TaskInstance.model.in_(request.model_ids))
    
    instances = query.all()
    
    if not instances:
        raise HTTPException(status_code=404, detail="No instances found matching criteria")
    
    # Build detailed comparison
    results = []
    for instance in instances:
        results.append({
            "tag": instance.tag,
            "model": instance.model,
            "status": instance.status,
            "validation_success": instance.validation_success,
            "duration_seconds": instance.duration_seconds,
            "test_passed": instance.test_passed,
            "test_failed": instance.test_failed,
            "test_errors": instance.test_errors,
            "generated_patch": instance.generated_patch,
            "summary": instance.summary,
            "started_at": instance.started_at,
            "completed_at": instance.completed_at,
            "task_dir": instance.task_dir
        })
    
    return {
        "instance_id": request.instance_id,
        "total_runs": len(results),
        "results": results
    }


@router.get("/tags", response_model=List[str])
def list_available_tags(
    dataset_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """List all unique tags available for comparison"""
    query = db.query(TaskInstance.tag).distinct()
    
    if dataset_id:
        query = query.join(TaskInstance.task).filter(
            TaskInstance.task.has(dataset_id=dataset_id)
        )
    
    tags = [row[0] for row in query.all()]
    return sorted(tags)


@router.get("/models-in-use", response_model=List[str])
def list_models_in_use(
    dataset_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all models that have been used in task instances"""
    query = db.query(TaskInstance.model).distinct().filter(
        TaskInstance.model.isnot(None)
    )
    
    if dataset_id:
        query = query.join(TaskInstance.task).filter(
            TaskInstance.task.has(dataset_id=dataset_id)
        )
    
    if tag:
        query = query.filter(TaskInstance.tag == tag)
    
    models = [row[0] for row in query.all()]
    return sorted(models)
