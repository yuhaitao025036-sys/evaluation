"""Batch result comparison API endpoints."""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Batch, BatchResult, Dataset
from app.schemas import (
    CompareBatchesRequest,
    CompareByModelsRequest,
    CompareByTagsRequest,
    CompareInstanceRequest,
    ComparisonMetadata,
    ComparisonResponse,
    InstanceComparisonResponse,
)

router = APIRouter()

ResultMap = Dict[str, Dict[str, BatchResult]]
BatchMap = Dict[int, Batch]


def _sort_key(result: BatchResult) -> Tuple[datetime, datetime, int]:
    return (
        result.completed_at or datetime.min,
        result.created_at or datetime.min,
        result.id,
    )


def _dedupe_latest(results: List[BatchResult]) -> Dict[str, BatchResult]:
    latest: Dict[str, BatchResult] = {}
    for result in results:
        existing = latest.get(result.instance_id)
        if not existing or _sort_key(result) > _sort_key(existing):
            latest[result.instance_id] = result
    return latest


def _summary(key: str, results: List[BatchResult], batch: Optional[Batch] = None) -> Dict:
    total = len(results)
    completed = sum(1 for result in results if result.status == 'completed')
    failed = sum(1 for result in results if result.status == 'failed')
    validation_success = sum(1 for result in results if result.validation_success is True)
    validation_failure = sum(1 for result in results if result.validation_success is False)
    validation_unknown = total - validation_success - validation_failure
    tests_passed = sum(result.tests_passed or 0 for result in results)
    tests_total = sum(result.tests_total or 0 for result in results)
    durations = [result.duration_seconds for result in results if result.duration_seconds is not None]
    first = results[0] if results else None

    return {
        'key': key,
        'batch_id': batch.id if batch else None,
        'batch_name': batch.batch_name if batch else None,
        'model': batch.model if batch else (first.model if first else ''),
        'tag': batch.tag if batch else (first.tag if first else ''),
        'dataset_id': batch.dataset_id if batch else None,
        'total': total,
        'completed': completed,
        'failed': failed,
        'validation_success': validation_success,
        'validation_failure': validation_failure,
        'validation_unknown': validation_unknown,
        'accuracy': validation_success / completed if completed else None,
        'evaluation_success_rate': validation_success / total if total else None,
        'test_pass_rate': tests_passed / tests_total if tests_total else None,
        'avg_duration_seconds': sum(durations) / len(durations) if durations else None,
    }


def _cell(result: BatchResult, batch: Batch) -> Dict:
    return {
        'batch_id': result.batch_id,
        'batch_name': batch.batch_name,
        'model': result.model,
        'tag': result.tag,
        'status': result.status,
        'validation_success': result.validation_success,
        'tests_passed': result.tests_passed or 0,
        'tests_failed': result.tests_failed or 0,
        'tests_total': result.tests_total or 0,
        'duration_seconds': result.duration_seconds,
        'has_patch': bool(result.patch_path),
        'result_summary': result.result_summary,
    }


def _classify(cells: List[Optional[Dict]]) -> str:
    if any(cell is None for cell in cells):
        return 'missing'

    values = [cell.get('validation_success') for cell in cells if cell is not None]
    if values and all(value is True for value in values):
        return 'all_success'
    if values and all(value is False for value in values):
        return 'all_failed'

    baseline = values[0] if values else None
    comparisons = values[1:]
    if baseline is True and any(value is False for value in comparisons):
        return 'regression'
    if baseline is False and any(value is True for value in comparisons):
        return 'improvement'
    return 'mixed'


def _build_response(
    mode: str,
    keys: List[str],
    grouped_results: ResultMap,
    summaries: Dict[str, Dict],
    batches: BatchMap,
    only_common_instances: bool,
    include_instances: bool,
    instance_limit: int,
) -> Dict:
    instance_sets = [set(grouped_results.get(key, {}).keys()) for key in keys]
    union_instances = set().union(*instance_sets) if instance_sets else set()
    common_instances = set.intersection(*instance_sets) if instance_sets else set()
    selected_instances = common_instances if only_common_instances else union_instances

    rows = []
    if include_instances:
        for instance_id in selected_instances:
            results = {}
            cells = []
            for key in keys:
                result = grouped_results.get(key, {}).get(instance_id)
                cell = _cell(result, batches[result.batch_id]) if result else None
                results[key] = cell
                cells.append(cell)
            rows.append({
                'instance_id': instance_id,
                'outcome': _classify(cells),
                'results': results,
            })

        outcome_priority = {
            'regression': 0,
            'improvement': 1,
            'mixed': 2,
            'missing': 3,
            'all_failed': 4,
            'all_success': 5,
        }
        rows.sort(key=lambda row: (outcome_priority.get(row['outcome'], 9), row['instance_id']))
        rows = rows[:instance_limit]

    return {
        'mode': mode,
        'keys': keys,
        'summaries': summaries,
        'compared_instances': len(selected_instances),
        'total_union_instances': len(union_instances),
        'common_instances': len(common_instances),
        'instance_rows': rows,
    }


def _batch_map_for_results(db: Session, results: List[BatchResult]) -> BatchMap:
    batch_ids = sorted({result.batch_id for result in results})
    if not batch_ids:
        return {}
    return {batch.id: batch for batch in db.query(Batch).filter(Batch.id.in_(batch_ids)).all()}


@router.get('/metadata', response_model=ComparisonMetadata)
def get_comparison_metadata(db: Session = Depends(get_db)):
    batches = db.query(Batch).order_by(Batch.created_at.desc()).all()
    models = sorted({batch.model for batch in batches if batch.model})
    tags = sorted({batch.tag for batch in batches if batch.tag})
    datasets = db.query(Dataset).order_by(Dataset.name).all()

    return {
        'models': models,
        'tags': tags,
        'datasets': [{'id': dataset.id, 'name': dataset.name} for dataset in datasets],
        'batches': [
            {
                'id': batch.id,
                'batch_name': batch.batch_name,
                'dataset_id': batch.dataset_id,
                'model': batch.model,
                'tag': batch.tag,
                'status': batch.status,
                'total_tasks': batch.total_tasks,
                'completed_tasks': batch.completed_tasks,
                'failed_tasks': batch.failed_tasks,
            }
            for batch in batches
        ],
    }


@router.post('/compare-batches', response_model=ComparisonResponse)
def compare_batches(request: CompareBatchesRequest, db: Session = Depends(get_db)):
    batches = db.query(Batch).filter(Batch.id.in_(request.batch_ids)).all()
    batches_by_id = {batch.id: batch for batch in batches}
    missing = [batch_id for batch_id in request.batch_ids if batch_id not in batches_by_id]
    if missing:
        raise HTTPException(status_code=404, detail=f"批次不存在: {missing}")

    results = db.query(BatchResult).filter(BatchResult.batch_id.in_(request.batch_ids)).all()
    keys = [f'batch:{batch_id}' for batch_id in request.batch_ids]
    grouped_results: ResultMap = {}
    summaries = {}

    for batch_id in request.batch_ids:
        key = f'batch:{batch_id}'
        batch_results = [result for result in results if result.batch_id == batch_id]
        grouped_results[key] = _dedupe_latest(batch_results)
        summaries[key] = _summary(key, batch_results, batches_by_id[batch_id])

    return _build_response(
        mode='batches',
        keys=keys,
        grouped_results=grouped_results,
        summaries=summaries,
        batches=batches_by_id,
        only_common_instances=request.only_common_instances,
        include_instances=request.include_instances,
        instance_limit=request.instance_limit,
    )


@router.post('/compare-by-models', response_model=ComparisonResponse)
def compare_by_models(request: CompareByModelsRequest, db: Session = Depends(get_db)):
    query = db.query(BatchResult).join(Batch, BatchResult.batch_id == Batch.id).filter(
        BatchResult.model.in_(request.models)
    )
    if request.dataset_id:
        query = query.filter(Batch.dataset_id == request.dataset_id)
    if request.tag:
        query = query.filter(BatchResult.tag == request.tag)

    results = query.all()
    batches = _batch_map_for_results(db, results)
    keys = [f'model:{model}' for model in request.models]
    grouped_results: ResultMap = {}
    summaries = {}

    for model in request.models:
        key = f'model:{model}'
        model_results = [result for result in results if result.model == model]
        grouped_results[key] = _dedupe_latest(model_results)
        summaries[key] = _summary(key, model_results)

    return _build_response(
        mode='models',
        keys=keys,
        grouped_results=grouped_results,
        summaries=summaries,
        batches=batches,
        only_common_instances=request.only_common_instances,
        include_instances=request.include_instances,
        instance_limit=request.instance_limit,
    )


@router.post('/compare-by-tags', response_model=ComparisonResponse)
def compare_by_tags(request: CompareByTagsRequest, db: Session = Depends(get_db)):
    query = db.query(BatchResult).join(Batch, BatchResult.batch_id == Batch.id).filter(
        BatchResult.tag.in_(request.tags)
    )
    if request.dataset_id:
        query = query.filter(Batch.dataset_id == request.dataset_id)
    if request.model:
        query = query.filter(BatchResult.model == request.model)

    results = query.all()
    batches = _batch_map_for_results(db, results)
    keys = [f'tag:{tag}' for tag in request.tags]
    grouped_results: ResultMap = {}
    summaries = {}

    for tag in request.tags:
        key = f'tag:{tag}'
        tag_results = [result for result in results if result.tag == tag]
        grouped_results[key] = _dedupe_latest(tag_results)
        summaries[key] = _summary(key, tag_results)

    return _build_response(
        mode='tags',
        keys=keys,
        grouped_results=grouped_results,
        summaries=summaries,
        batches=batches,
        only_common_instances=request.only_common_instances,
        include_instances=request.include_instances,
        instance_limit=request.instance_limit,
    )


@router.post('/compare-instance', response_model=InstanceComparisonResponse)
def compare_single_instance(request: CompareInstanceRequest, db: Session = Depends(get_db)):
    query = db.query(BatchResult).join(Batch, BatchResult.batch_id == Batch.id).filter(
        BatchResult.instance_id == request.instance_id
    )
    if request.batch_ids:
        query = query.filter(BatchResult.batch_id.in_(request.batch_ids))
    if request.models:
        query = query.filter(BatchResult.model.in_(request.models))
    if request.tags:
        query = query.filter(BatchResult.tag.in_(request.tags))
    if request.dataset_id:
        query = query.filter(Batch.dataset_id == request.dataset_id)

    results = query.order_by(BatchResult.batch_id, BatchResult.id).all()
    if not results:
        raise HTTPException(status_code=404, detail="没有找到匹配的实例结果")

    batches = _batch_map_for_results(db, results)
    return {
        'instance_id': request.instance_id,
        'results': [_cell(result, batches[result.batch_id]) for result in results],
    }


@router.get('/tags', response_model=List[str])
def list_available_tags(
    dataset_id: Optional[int] = Query(None),
    model: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Batch.tag).distinct()
    if dataset_id:
        query = query.filter(Batch.dataset_id == dataset_id)
    if model:
        query = query.filter(Batch.model == model)
    return sorted(row[0] for row in query.all() if row[0])


@router.get('/models-in-use', response_model=List[str])
def list_models_in_use(
    dataset_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Batch.model).distinct()
    if dataset_id:
        query = query.filter(Batch.dataset_id == dataset_id)
    if tag:
        query = query.filter(Batch.tag == tag)
    return sorted(row[0] for row in query.all() if row[0])
