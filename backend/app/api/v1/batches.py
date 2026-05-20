"""
Batch Management API Endpoints
批次管理 API 路由
"""
import json
import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    BatchCreate, BatchUpdate, BatchResponse, BatchStats,
    BatchResultResponse, MessageResponse, BatchStartRequest,
    BatchPauseRequest, BatchRetryRequest, BatchTaskRerunRequest, BatchAddTasksRequest
)
from app.services.batch_service import BatchService
from app.services.scheduler_service import SchedulerService

router = APIRouter()


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    batch_create: BatchCreate,
    db: Session = Depends(get_db)
):
    """
    创建批次并生成任务实例
    
    支持两种模式：
    - 新建批次：创建新的批次记录
    - 追加模式：向已有批次追加任务（需设置 append_to_existing=True）
    """
    try:
        service = BatchService(db)
        batch, stats = service.create_batch(batch_create)
        
        return MessageResponse(
            message=f"批次 '{batch.batch_name}' 创建成功",
            data={
                "batch_id": batch.id,
                "batch_name": batch.batch_name,
                "stats": stats
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建批次失败: {str(e)}")


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """获取批次详情"""
    service = BatchService(db)
    batch = service.get_batch(batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail=f"批次 ID {batch_id} 不存在")
    
    return batch


@router.get("", response_model=List[BatchResponse])
async def list_batches(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    model: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """列出批次"""
    service = BatchService(db)
    batches = service.list_batches(
        skip=skip,
        limit=limit,
        status=status,
        model=model,
        tag=tag
    )
    return batches


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: int,
    batch_update: BatchUpdate,
    db: Session = Depends(get_db)
):
    """更新批次配置"""
    try:
        service = BatchService(db)
        batch = service.update_batch(batch_id, batch_update)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{batch_id}", response_model=MessageResponse)
async def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """删除批次（级联删除所有任务结果）"""
    service = BatchService(db)
    success = service.delete_batch(batch_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"批次 ID {batch_id} 不存在")
    
    return MessageResponse(message=f"批次 {batch_id} 已删除")


# ============================================================================
# 批次操作 API
# ============================================================================

@router.post("/{batch_id}/start", response_model=MessageResponse)
async def start_batch(
    batch_id: int,
    request: BatchStartRequest = BatchStartRequest(),
    db: Session = Depends(get_db)
):
    """
    启动批次
    
    启动后系统会：
    1. 将批次状态改为 running
    2. 启动任务调度器
    3. 根据 max_concurrency 调度 pending 任务
    """
    try:
        scheduler = SchedulerService(db)
        result = scheduler.start_batch(batch_id, force=request.force)
        
        return MessageResponse(
            message=f"批次 {batch_id} 已启动",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动批次失败: {str(e)}")


@router.post("/{batch_id}/pause", response_model=MessageResponse)
async def pause_batch(
    batch_id: int,
    request: BatchPauseRequest = BatchPauseRequest(),
    db: Session = Depends(get_db)
):
    """
    暂停批次
    
    暂停后：
    - 不再调度新任务
    - 正在运行的任务继续执行（如果 wait_for_running=True）
    """
    try:
        scheduler = SchedulerService(db)
        result = scheduler.pause_batch(batch_id, wait_for_running=request.wait_for_running)
        
        return MessageResponse(
            message=f"批次 {batch_id} 已暂停",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{batch_id}/resume", response_model=MessageResponse)
async def resume_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """恢复批次（从暂停状态恢复）"""
    try:
        scheduler = SchedulerService(db)
        result = scheduler.resume_batch(batch_id)
        
        return MessageResponse(
            message=f"批次 {batch_id} 已恢复",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/retry", response_model=MessageResponse)
async def retry_failed_tasks(
    batch_id: int,
    request: BatchRetryRequest = BatchRetryRequest(),
    db: Session = Depends(get_db)
):
    """
    重试失败任务
    
    可以：
    - 重试所有失败任务
    - 重试指定 instance_id 的任务
    - 选择是否重置重试计数
    """
    try:
        scheduler = SchedulerService(db)
        result = scheduler.retry_failed_tasks(
            batch_id=batch_id,
            instance_ids=request.instance_ids,
            reset_retry_count=request.reset_retry_count
        )
        
        return MessageResponse(
            message=f"已重试 {result['retried_count']} 个失败任务",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{batch_id}/tasks", response_model=MessageResponse)
async def add_tasks_to_batch(
    batch_id: int,
    request: BatchAddTasksRequest,
    db: Session = Depends(get_db)
):
    """向现有批次追加任务"""
    try:
        service = BatchService(db)
        stats = service.add_tasks_to_batch(batch_id, request)
        
        return MessageResponse(
            message=f"已向批次 {batch_id} 追加任务",
            data=stats
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 批次统计和任务查询 API
# ============================================================================

@router.get("/{batch_id}/stats", response_model=BatchStats)
async def get_batch_stats(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """获取批次统计信息"""
    service = BatchService(db)
    stats = service.get_batch_stats(batch_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail=f"批次 ID {batch_id} 不存在")
    
    return stats


@router.get("/{batch_id}/tasks", response_model=List[BatchResultResponse])
async def get_batch_tasks(
    batch_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取批次的任务列表"""
    service = BatchService(db)
    tasks = service.get_batch_tasks(
        batch_id=batch_id,
        status=status,
        skip=skip,
        limit=limit
    )
    return tasks


@router.get("/{batch_id}/tasks/{instance_id}", response_model=BatchResultResponse)
async def get_batch_task(
    batch_id: int,
    instance_id: str,
    db: Session = Depends(get_db)
):
    """获取批次中指定实例的任务结果"""
    service = BatchService(db)
    task = service.get_batch_task(batch_id, instance_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"批次 {batch_id} 中不存在实例 {instance_id} 的任务"
        )

    return task


@router.post("/{batch_id}/tasks/{instance_id}/run", response_model=MessageResponse)
async def run_single_task(
    batch_id: int,
    instance_id: str,
    db: Session = Depends(get_db)
):
    """只执行指定 pending 子任务，不触发批次级调度。"""
    try:
        scheduler = SchedulerService(db)
        result = scheduler.run_single_task(batch_id, instance_id)
        return MessageResponse(message="子任务已加入队列", data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/tasks/{instance_id}/rerun", response_model=MessageResponse)
async def rerun_single_task(
    batch_id: int,
    instance_id: str,
    request: BatchTaskRerunRequest = BatchTaskRerunRequest(),
    db: Session = Depends(get_db)
):
    """强制重跑指定非 pending 子任务，不触发批次级调度。"""
    try:
        scheduler = SchedulerService(db)
        result = scheduler.rerun_single_task(
            batch_id=batch_id,
            instance_id=instance_id,
            reset_retry_count=request.reset_retry_count,
        )
        return MessageResponse(message="子任务已加入重跑队列", data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 文件读取 API - 获取任务输出文件内容
# ============================================================================

@router.get("/{batch_id}/tasks/{instance_id}/validation-detail")
async def get_task_validation_detail(
    batch_id: int,
    instance_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取任务的详细验证报告 (validation_detail.json)
    
    返回完整的测试详情，包括:
    - 每个测试用例的执行结果
    - 断言详情
    - 代码覆盖率
    - 性能数据
    """
    service = BatchService(db)
    task = service.get_batch_task(batch_id, instance_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"批次 {batch_id} 中不存在实例 {instance_id} 的任务"
        )
    
    if not task.validation_detail_path:
        raise HTTPException(
            status_code=404,
            detail="该任务没有生成详细验证报告"
        )
    
    if not os.path.exists(task.validation_detail_path):
        raise HTTPException(
            status_code=404,
            detail=f"验证报告文件不存在: {task.validation_detail_path}"
        )
    
    try:
        with open(task.validation_detail_path, 'r', encoding='utf-8') as f:
            detail = json.load(f)
        return detail
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"验证报告文件格式错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"读取验证报告失败: {str(e)}"
        )


@router.get("/{batch_id}/tasks/{instance_id}/trace")
async def get_task_trace(
    batch_id: int,
    instance_id: str,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    获取任务的执行轨迹 (execution_trace.jsonl)
    
    返回逐行执行记录，每条记录包括:
    - 时间戳
    - 执行的代码行
    - 变量状态
    - 函数调用栈
    """
    service = BatchService(db)
    task = service.get_batch_task(batch_id, instance_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"批次 {batch_id} 中不存在实例 {instance_id} 的任务"
        )
    
    if not task.trace_file_path:
        raise HTTPException(
            status_code=404,
            detail="该任务没有生成执行轨迹文件"
        )
    
    if not os.path.exists(task.trace_file_path):
        raise HTTPException(
            status_code=404,
            detail=f"执行轨迹文件不存在: {task.trace_file_path}"
        )
    
    try:
        trace_lines = []
        with open(task.trace_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    trace_lines.append(json.loads(line))
        return trace_lines
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"执行轨迹文件格式错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"读取执行轨迹失败: {str(e)}"
        )


@router.get("/{batch_id}/tasks/{instance_id}/patch")
async def get_task_patch(
    batch_id: int,
    instance_id: str,
    db: Session = Depends(get_db)
):
    """
    下载任务生成的补丁文件 (extracted_patch.diff)
    
    以文件形式返回，浏览器会自动下载
    """
    service = BatchService(db)
    task = service.get_batch_task(batch_id, instance_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"批次 {batch_id} 中不存在实例 {instance_id} 的任务"
        )
    
    if not task.patch_path:
        raise HTTPException(
            status_code=404,
            detail="该任务没有生成补丁文件"
        )
    
    if not os.path.exists(task.patch_path):
        raise HTTPException(
            status_code=404,
            detail=f"补丁文件不存在: {task.patch_path}"
        )
    
    return FileResponse(
        path=task.patch_path,
        media_type='text/plain',
        filename=f"{instance_id}_patch.diff"
    )


@router.get("/{batch_id}/tasks/{instance_id}/logs/{log_name}")
async def get_task_log_content(
    batch_id: int,
    instance_id: str,
    log_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """获取任务日志文件内容。"""
    allowed_logs = {
        'generation_stdout': 'generation_stdout.log',
        'generation_stderr': 'generation_stderr.log',
        'evaluation_stdout': 'evaluation_stdout.log',
        'evaluation_stderr': 'evaluation_stderr.log',
        'ducc_execution': 'ducc_execution.log',
    }
    if log_name not in allowed_logs:
        raise HTTPException(status_code=400, detail="不支持的日志类型")

    service = BatchService(db)
    task = service.get_batch_task(batch_id, instance_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"批次 {batch_id} 中不存在实例 {instance_id} 的任务"
        )
    if not task.output_dir:
        raise HTTPException(status_code=404, detail="该任务没有输出目录")

    log_path = os.path.join(task.output_dir, allowed_logs[log_name])
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail=f"日志文件不存在: {allowed_logs[log_name]}")

    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            return {"content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")


@router.get("/{batch_id}/tasks/{instance_id}/patch-content")
async def get_task_patch_content(
    batch_id: int,
    instance_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    获取补丁文件的文本内容 (用于前端直接展示)
    
    返回格式: {"content": "patch内容..."}
    """
    service = BatchService(db)
    task = service.get_batch_task(batch_id, instance_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"批次 {batch_id} 中不存在实例 {instance_id} 的任务"
        )
    
    if not task.patch_path:
        raise HTTPException(
            status_code=404,
            detail="该任务没有生成补丁文件"
        )
    
    if not os.path.exists(task.patch_path):
        raise HTTPException(
            status_code=404,
            detail=f"补丁文件不存在: {task.patch_path}"
        )
    
    try:
        with open(task.patch_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"读取补丁文件失败: {str(e)}"
        )
