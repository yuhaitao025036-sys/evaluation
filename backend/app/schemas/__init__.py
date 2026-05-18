"""Pydantic schemas for API requests and responses"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.batch import (
    BatchCreate, BatchUpdate, BatchResponse, BatchStats,
    BatchResultResponse, BatchResultUpdate,
    BatchStartRequest, BatchPauseRequest, BatchRetryRequest, BatchAddTasksRequest,
    MessageResponse, ErrorResponse, PaginatedResponse,
    DatasetResponse, DatasetInstanceResponse, ScriptResponse,
)


# Dataset schemas
class DatasetBase(BaseModel):
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
    last_scanned_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Task Group schemas
class TaskGroupCreate(BaseModel):
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


class TaskGroup(BaseModel):
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
class TaskInstance(BaseModel):
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
class CompareModelsRequest(BaseModel):
    model_ids: List[str] = Field(..., description="List of model IDs to compare")
    tag: str = Field(..., description="Tag to compare across models")
    dataset_id: Optional[int] = None


class CompareTagsRequest(BaseModel):
    tags: List[str] = Field(..., description="List of tags to compare")
    model_id: Optional[str] = None
    dataset_id: Optional[int] = None


class InstanceComparisonRequest(BaseModel):
    instance_id: str
    tags: Optional[List[str]] = None
    model_ids: Optional[List[str]] = None


# Comparison response schemas
class TaskInstanceComparison(BaseModel):
    instance_id: str
    results_by_model: Optional[Dict[str, Any]] = None
    results_by_tag: Optional[Dict[str, Any]] = None


class ModelComparisonResult(BaseModel):
    tag: str
    model_ids: List[str]
    dataset_id: Optional[int] = None
    comparison_stats: Dict[str, Any]
    instance_comparisons: List[Dict[str, Any]]


class TagComparisonResult(BaseModel):
    model_id: Optional[str] = None
    tags: List[str]
    dataset_id: Optional[int] = None
    comparison_stats: Dict[str, Any]
    instance_comparisons: List[Dict[str, Any]]


class InstanceComparisonDetail(BaseModel):
    instance_id: str
    total_runs: int
    results: List[Dict[str, Any]]


# Task Instance response schemas
class TaskInstanceResponse(BaseModel):
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


class TaskInstanceDetail(BaseModel):
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
class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str
