"""
SQLAlchemy Models for DUCC Evaluation System v2.0
基于简化数据模型：数据层 → 批次层 → 结果层
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, BigInteger, Boolean, Float, ForeignKey, TIMESTAMP, Index, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================================================
# 数据层 (Data Layer)
# ============================================================================

class Dataset(Base):
    """数据集元信息"""
    __tablename__ = 'datasets'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    format = Column(String(50), nullable=False)
    file_size = Column(BigInteger)
    total_instances = Column(Integer)
    imported_instances = Column(Integer, default=0)
    description = Column(Text)
    last_scanned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # 关系
    instances = relationship("DatasetInstance", back_populates="dataset", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="dataset")


class DatasetInstance(Base):
    """数据集实例"""
    __tablename__ = 'dataset_instances'
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    instance_id = Column(String(255), nullable=False)
    repo_language = Column(String(50), index=True)
    data = Column(JSON, nullable=False)  # JSONB in PostgreSQL
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # 关系
    dataset = relationship("Dataset", back_populates="instances")
    batch_results = relationship("BatchResult", back_populates="dataset_instance")
    
    # 约束和索引
    __table_args__ = (
        UniqueConstraint('dataset_id', 'instance_id', name='uq_dataset_instance'),
        Index('idx_dataset_instances_instance_id', 'instance_id'),
        Index('idx_dataset_instances_dataset_instance', 'dataset_id', 'instance_id'),
        Index('idx_dataset_instances_data_gin', 'data', postgresql_using='gin'),
    )


class Script(Base):
    """评估脚本"""
    __tablename__ = 'scripts'
    
    id = Column(Integer, primary_key=True)
    file_name = Column(String(255), unique=True, nullable=False)
    file_path = Column(String(512), nullable=False)
    description = Column(Text)
    last_scanned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # 关系
    batches = relationship("Batch", back_populates="script")
    
    __table_args__ = (
        Index('idx_scripts_filename', 'file_name'),
    )


# ============================================================================
# 批次层 (Batch Layer) - 核心组织单位
# ============================================================================

class Batch(Base):
    """批次 - 任务聚合和管理单位"""
    __tablename__ = 'batches'
    
    id = Column(Integer, primary_key=True)
    batch_name = Column(String(200), unique=True, nullable=False)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'))
    script_id = Column(Integer, ForeignKey('scripts.id', ondelete='SET NULL'))
    model = Column(String(100), nullable=False)
    tag = Column(String(100), nullable=False)
    
    # 执行配置
    execution_config = Column(JSON)
    
    # 批次状态
    status = Column(String(50), default='created', index=True)  # created, running, paused, completed, failed
    
    # 并发控制
    max_concurrency = Column(Integer, default=10)
    current_running = Column(Integer, default=0)
    priority = Column(Integer, default=0, index=True)
    
    # 任务统计
    total_tasks = Column(Integer, default=0)
    pending_tasks = Column(Integer, default=0)
    queued_tasks = Column(Integer, default=0)
    running_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at = Column(TIMESTAMP(timezone=True))
    paused_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 输出目录
    output_dir = Column(String(512))
    
    # 创建者
    created_by = Column(String(100))
    
    # 关系
    dataset = relationship("Dataset", back_populates="batches")
    script = relationship("Script", back_populates="batches")
    results = relationship("BatchResult", back_populates="batch", cascade="all, delete-orphan")
    
    # 约束和索引
    __table_args__ = (
        Index('idx_batches_dataset', 'dataset_id'),
        Index('idx_batches_model_tag', 'model', 'tag'),
        Index('idx_batches_priority', 'priority'),
    )


# ============================================================================
# 结果层 (Result Layer)
# ============================================================================

class BatchResult(Base):
    """批次任务结果 - 每条记录是一个独立任务"""
    __tablename__ = 'batch_results'
    
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('batches.id', ondelete='CASCADE'), nullable=False)
    dataset_instance_id = Column(Integer, ForeignKey('dataset_instances.id', ondelete='CASCADE'), nullable=False)
    instance_id = Column(String(255), nullable=False)
    
    # 任务配置（冗余存储）
    model = Column(String(100), nullable=False)
    tag = Column(String(100), nullable=False)
    
    # 任务状态
    status = Column(String(50), default='pending', index=True)  # pending, queued, running, completed, failed, retrying
    
    # 重试机制
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # 队列和 Worker 信息
    job_id = Column(String(255), index=True)
    worker_id = Column(String(100))
    
    # 执行结果
    validation_success = Column(Boolean)
    tests_passed = Column(Integer, default=0)
    tests_failed = Column(Integer, default=0)
    tests_total = Column(Integer, default=0)
    duration_seconds = Column(Float)
    result_summary = Column(JSON)
    
    # 输出文件路径
    patch_path = Column(String(512))
    output_dir = Column(String(512))
    trace_file_path = Column(String(512))           # execution_trace.jsonl 路径
    validation_detail_path = Column(String(512))     # validation_detail.json 路径
    
    # 错误信息
    error_message = Column(Text)
    
    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    queued_at = Column(TIMESTAMP(timezone=True))
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    last_heartbeat = Column(TIMESTAMP(timezone=True))  # ✅ 心跳时间
    
    # 关系
    batch = relationship("Batch", back_populates="results")
    dataset_instance = relationship("DatasetInstance", back_populates="batch_results")
    
    # 约束和索引
    __table_args__ = (
        UniqueConstraint('batch_id', 'instance_id', name='uq_batch_result_batch_instance'),
        Index('idx_batch_results_batch', 'batch_id'),
        Index('idx_batch_results_instance', 'instance_id'),
        Index('idx_batch_results_model_tag', 'model', 'tag'),
        Index('idx_batch_results_job_id', 'job_id'),
        Index('idx_batch_results_batch_status', 'batch_id', 'status'),  # 调度器优化
    )


# ============================================================================
# 对比功能支持
# ============================================================================

class Comparison(Base):
    """对比配置"""
    __tablename__ = 'comparisons'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    comparison_type = Column(String(50), nullable=False)  # cross_model, cross_tag, three_way
    config = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(String(100))
