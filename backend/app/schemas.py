"""
Pydantic Schemas for DUCC Evaluation System v2.0
基于简化数据模型：数据层 → 批次层 → 结果层
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


# ============================================================================
# 批次 (Batch) Schemas
# ============================================================================

class BatchCreate(BaseModel):
    """创建批次请求"""
    batch_name: str = Field(..., description="批次名称，唯一标识")
    dataset_id: int = Field(..., description="数据集 ID")
    script_id: int = Field(..., description="脚本 ID")
    model: str = Field(..., description="模型名称")
    tag: str = Field(..., description="批次标签")
    
    # 数据范围
    instance_ids: Optional[List[str]] = Field(None, description="指定实例 ID 列表")
    start_index: Optional[int] = Field(0, description="数据集起始索引")
    end_index: Optional[int] = Field(None, description="数据集结束索引")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="数据筛选条件")
    
    # 执行配置
    execution_config: Optional[Dict[str, Any]] = Field(None, description="脚本自定义参数")
    max_concurrency: int = Field(10, ge=1, le=100, description="最大并发数")
    max_retries: int = Field(3, ge=0, le=10, description="最大重试次数")
    priority: int = Field(0, description="批次优先级")
    
    # 批次行为
    append_to_existing: bool = Field(False, description="是否追加到已有批次")
    overwrite_existing: bool = Field(False, description="遇到重复实例是否覆盖")
    
    created_by: Optional[str] = Field(None, description="创建者")


class BatchUpdate(BaseModel):
    """更新批次请求"""
    status: Optional[str] = Field(None, description="批次状态")
    max_concurrency: Optional[int] = Field(None, ge=1, le=100, description="最大并发数")
    priority: Optional[int] = Field(None, description="优先级")
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")


class BatchResponse(BaseModel):
    """批次响应"""
    id: int
    batch_name: str
    dataset_id: int
    script_id: Optional[int]
    model: str
    tag: str
    
    status: str
    max_concurrency: int
    current_running: int
    priority: int
    
    total_tasks: int
    pending_tasks: int
    queued_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    
    execution_config: Optional[Dict[str, Any]]
    output_dir: Optional[str]
    
    created_at: datetime
    started_at: Optional[datetime]
    paused_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime
    
    created_by: Optional[str]
    
    class Config:
        from_attributes = True


class BatchStats(BaseModel):
    """批次统计信息"""
    batch_id: int
    batch_name: str
    status: str
    
    total_tasks: int
    pending_tasks: int
    queued_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    
    success_rate: float = Field(description="完成率")
    validation_success_rate: Optional[float] = Field(None, description="验证通过率")
    
    avg_duration: Optional[float] = Field(None, description="平均耗时（秒）")
    total_duration: Optional[float] = Field(None, description="总耗时（秒）")


# ============================================================================
# 批次结果 (BatchResult) Schemas
# ============================================================================

class BatchResultResponse(BaseModel):
    """批次任务结果响应"""
    id: int
    batch_id: int
    instance_id: str
    model: str
    tag: str
    
    status: str
    retry_count: int
    max_retries: int
    
    job_id: Optional[str]
    worker_id: Optional[str]
    
    validation_success: Optional[bool]
    tests_passed: int
    tests_failed: int
    tests_total: int
    duration_seconds: Optional[float]
    
    result_summary: Optional[Dict[str, Any]]
    patch_path: Optional[str]
    output_dir: Optional[str]
    trace_file_path: Optional[str]
    validation_detail_path: Optional[str]
    error_message: Optional[str]

    created_at: datetime
    queued_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class BatchResultUpdate(BaseModel):
    """更新批次任务结果"""
    status: Optional[str] = None
    job_id: Optional[str] = None
    worker_id: Optional[str] = None
    validation_success: Optional[bool] = None
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    tests_total: Optional[int] = None
    duration_seconds: Optional[float] = None
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None


# ============================================================================
# 批次操作 Schemas
# ============================================================================

class BatchStartRequest(BaseModel):
    """启动批次请求"""
    force: bool = Field(False, description="强制启动（即使有失败任务）")


class BatchPauseRequest(BaseModel):
    """暂停批次请求"""
    wait_for_running: bool = Field(True, description="等待正在运行的任务完成")


class BatchRetryRequest(BaseModel):
    """重试失败任务请求"""
    instance_ids: Optional[List[str]] = Field(None, description="指定要重试的实例 ID，为空则重试所有失败任务")
    reset_retry_count: bool = Field(True, description="重置重试计数")


class BatchAddTasksRequest(BaseModel):
    """向批次追加任务请求"""
    instance_ids: Optional[List[str]] = Field(None, description="指定实例 ID 列表")
    start_index: Optional[int] = Field(None, description="数据集起始索引")
    end_index: Optional[int] = Field(None, description="数据集结束索引")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="数据筛选条件")
    overwrite_existing: bool = Field(False, description="遇到重复实例是否覆盖")


# ============================================================================
# 数据集 Schemas (保持兼容)
# ============================================================================

class DatasetResponse(BaseModel):
    """数据集响应"""
    id: int
    name: str
    file_name: str
    file_path: str
    format: str
    file_size: Optional[int]
    total_instances: Optional[int]
    imported_instances: int
    description: Optional[str]
    last_scanned_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class DatasetInstanceResponse(BaseModel):
    """数据集实例响应"""
    id: int
    dataset_id: int
    instance_id: str
    repo_language: Optional[str]
    data: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# 脚本 Schemas (保持兼容)
# ============================================================================

class ScriptResponse(BaseModel):
    """脚本响应"""
    id: int
    file_name: str
    file_path: str
    description: Optional[str]
    last_scanned_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# 通用响应 Schemas
# ============================================================================

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
