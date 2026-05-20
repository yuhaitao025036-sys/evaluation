"""Pydantic schemas for API requests and responses"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.batch import (
    BatchCreate, BatchUpdate, BatchResponse, BatchStats,
    BatchResultResponse, BatchResultUpdate,
    BatchStartRequest, BatchPauseRequest, BatchRetryRequest, BatchTaskRerunRequest, BatchAddTasksRequest,
    MessageResponse, ErrorResponse, PaginatedResponse,
    DatasetResponse, DatasetInstanceResponse, ScriptResponse,
)


class SchemaBaseModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


# Dataset schemas
class DatasetBase(SchemaBaseModel):
    name: str
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    file_name: str
    file_path: str
    format: str


class Dataset(DatasetBase):
    id: int
    file_name: str
    file_path: str
    format: str
    file_size: Optional[int] = None
    total_instances: Optional[int] = None
    imported_instances: int = 0
    last_scanned_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Script schemas
class ScriptBase(BaseModel):
    file_name: str
    description: Optional[str] = None


class Script(ScriptBase):
    id: int
    file_path: str
    argument_schema: Optional[List[Dict[str, Any]]] = None
    last_scanned_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Task Group schemas
class TaskGroupCreate(SchemaBaseModel):
    name: str
    description: Optional[str] = None
    dataset_id: int
    script_id: int
    model: str = Field(..., description="Model ID (e.g., 'gpt-4-turbo')")
    model_params: Optional[Dict[str, Any]] = None
    tag: str = Field(..., description="Experiment tag (e.g., 'baseline', 'experiment-1')")
    script_args: Optional[str] = None
    concurrency: int = Field(default=1, ge=1, le=50, description="Number of concurrent workers")
    filter_conditions: Optional[Dict[str, Any]] = None
    start_index: int = 0
    end_index: Optional[int] = None


class TaskGroup(SchemaBaseModel):
    id: int
    name: str
    description: Optional[str] = None
    dataset_id: int
    script_id: int
    model: str
    model_params: Optional[Dict[str, Any]] = None
    tag: str
    script_args: Optional[str] = None
    batch_size: int
    total_batches: Optional[int] = None
    concurrency: int
    filter_conditions: Optional[Dict[str, Any]] = None
    start_index: int
    end_index: Optional[int] = None
    total_instances: Optional[int] = None
    status: str
    completed_batches: int
    completed_instances: int
    failed_instances: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class TaskGroupWithDetails(TaskGroup):
    """Task group with related information"""
    dataset: Optional[Dataset] = None
    script: Optional[Script] = None
    model_info: Optional[Dict[str, Any]] = None


# Task Instance schemas
class TaskInstance(SchemaBaseModel):
    id: int
    task_id: int
    instance_id: str
    tag: str
    model: Optional[str] = None
    model_params: Optional[Dict[str, Any]] = None
    status: str
    summary: Optional[Dict[str, Any]] = None
    generated_patch: Optional[str] = None
    test_passed: int = 0
    test_failed: int = 0
    test_errors: int = 0
    validation_success: Optional[bool] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    task_dir: Optional[str] = None

    class Config:
        from_attributes = True


# Comparison schemas
class CompareBatchesRequest(SchemaBaseModel):
    batch_ids: List[int] = Field(..., min_length=2, description="Batch IDs to compare")
    include_instances: bool = True
    instance_limit: int = Field(default=200, ge=1, le=2000)
    only_common_instances: bool = True


class CompareByModelsRequest(SchemaBaseModel):
    models: List[str] = Field(..., min_length=2, description="Model IDs to compare")
    dataset_id: Optional[int] = None
    tag: Optional[str] = None
    include_instances: bool = True
    instance_limit: int = Field(default=200, ge=1, le=2000)
    only_common_instances: bool = True


class CompareByTagsRequest(SchemaBaseModel):
    tags: List[str] = Field(..., min_length=2, description="Tags to compare")
    dataset_id: Optional[int] = None
    model: Optional[str] = None
    include_instances: bool = True
    instance_limit: int = Field(default=200, ge=1, le=2000)
    only_common_instances: bool = True


class CompareInstanceRequest(SchemaBaseModel):
    instance_id: str
    batch_ids: Optional[List[int]] = None
    models: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    dataset_id: Optional[int] = None


class ComparisonDatasetOption(SchemaBaseModel):
    id: int
    name: str


class ComparisonBatchOption(SchemaBaseModel):
    id: int
    batch_name: str
    dataset_id: Optional[int] = None
    model: str
    tag: str
    status: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int


class ComparisonMetadata(SchemaBaseModel):
    models: List[str]
    tags: List[str]
    datasets: List[ComparisonDatasetOption]
    batches: List[ComparisonBatchOption]


class ComparisonRunSummary(SchemaBaseModel):
    key: str
    batch_id: Optional[int] = None
    batch_name: Optional[str] = None
    model: str
    tag: str
    dataset_id: Optional[int] = None
    total: int
    completed: int
    failed: int
    validation_success: int
    validation_failure: int
    validation_unknown: int
    accuracy: Optional[float] = None
    evaluation_success_rate: Optional[float] = None
    test_pass_rate: Optional[float] = None
    avg_duration_seconds: Optional[float] = None


class ComparisonInstanceCell(SchemaBaseModel):
    batch_id: int
    batch_name: str
    model: str
    tag: str
    status: str
    validation_success: Optional[bool] = None
    tests_passed: int
    tests_failed: int
    tests_total: int
    duration_seconds: Optional[float] = None
    has_patch: bool
    result_summary: Optional[Dict[str, Any]] = None


class ComparisonInstanceRow(SchemaBaseModel):
    instance_id: str
    outcome: str
    results: Dict[str, Optional[ComparisonInstanceCell]]


class ComparisonResponse(SchemaBaseModel):
    mode: str
    keys: List[str]
    summaries: Dict[str, ComparisonRunSummary]
    compared_instances: int
    total_union_instances: int
    common_instances: int
    instance_rows: List[ComparisonInstanceRow]


class InstanceComparisonResponse(SchemaBaseModel):
    instance_id: str
    results: List[ComparisonInstanceCell]


# Backward-compatible aliases for older imports
CompareModelsRequest = CompareByModelsRequest
CompareTagsRequest = CompareByTagsRequest
InstanceComparisonRequest = CompareInstanceRequest
TaskInstanceComparison = ComparisonInstanceRow
ModelComparisonResult = ComparisonResponse
TagComparisonResult = ComparisonResponse
InstanceComparisonDetail = InstanceComparisonResponse


# Task Instance response schemas
class TaskInstanceResponse(SchemaBaseModel):
    id: int
    task_id: int
    instance_id: str
    tag: str
    model: Optional[str] = None
    status: str
    validation_success: Optional[bool] = None
    test_passed: int = 0
    test_failed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    class Config:
        from_attributes = True


class TaskInstanceDetail(SchemaBaseModel):
    id: int
    task_id: int
    instance_id: str
    tag: str
    model: Optional[str] = None
    model_params: Optional[Dict[str, Any]] = None
    status: str
    validation_success: Optional[bool] = None
    test_passed: int = 0
    test_failed: int = 0
    test_errors: int = 0
    generated_patch: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    task_dir: Optional[str] = None
    task_name: Optional[str] = None
    dataset_name: Optional[str] = None


# Model info schema
class ModelInfo(SchemaBaseModel):
    id: str
    name: str
    provider: str
    description: str
