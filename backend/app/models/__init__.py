"""Database models"""
from app.database import Base

from app.models.batch import (
    Dataset, DatasetInstance, Script, Batch, BatchResult, Comparison
)

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class TaskGroup(Base):
    """Task group model - for batch management"""
    __tablename__ = "task_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Configuration
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(100), nullable=False, index=True)
    script_args = Column(Text)

    # Model selection
    model = Column(String(100), index=True)
    model_params = Column(JSONB)

    # Concurrency configuration
    concurrency = Column(Integer, default=1)
    filter_conditions = Column(JSONB)

    # Batch configuration
    batch_size = Column(Integer, default=50)
    total_batches = Column(Integer)

    # Instance range
    start_index = Column(Integer, default=0)
    end_index = Column(Integer)
    total_instances = Column(Integer)

    # Status
    status = Column(String(50), default='created', index=True)
    completed_batches = Column(Integer, default=0)
    completed_instances = Column(Integer, default=0)
    failed_instances = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_by = Column(String(100))

    # Relationships
    tasks = relationship("Task", back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('dataset_id', 'tag', name='uq_group_tag'),
        Index('idx_task_groups_dataset_tag', 'dataset_id', 'tag'),
    )


class Task(Base):
    """Task model"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Associations
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("task_groups.id", ondelete="CASCADE"))

    # Tag for comparison
    tag = Column(String(100), nullable=False, default='baseline', index=True)

    # Configuration
    script_args = Column(Text)

    # Task range
    start_index = Column(Integer, default=0)
    end_index = Column(Integer)

    # Status
    status = Column(String(50), default='created', index=True)
    total_instances = Column(Integer, default=0)
    completed_instances = Column(Integer, default=0)
    failed_instances = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_by = Column(String(100))

    # Output
    output_dir = Column(String(512))

    # Relationships
    dataset = relationship("Dataset", back_populates="tasks")
    script = relationship("Script", back_populates="tasks")
    group = relationship("TaskGroup", back_populates="tasks")
    task_instances = relationship("TaskInstance", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('dataset_id', 'tag', 'start_index', 'end_index', name='uq_task_tag'),
        Index('idx_tasks_dataset_tag', 'dataset_id', 'tag'),
    )


class TaskInstance(Base):
    """Task instance model"""
    __tablename__ = "task_instances"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dataset_instance_id = Column(Integer, ForeignKey("dataset_instances.id"))
    instance_id = Column(String(255), nullable=False, index=True)

    # Tag (from task)
    tag = Column(String(100), nullable=False, index=True)

    # Model tracking
    model = Column(String(100), index=True)
    model_params = Column(JSONB)

    # Status
    status = Column(String(50), default='pending', index=True)

    # Results
    summary = Column(JSONB)
    generated_patch = Column(Text)

    # Validation results
    test_passed = Column(Integer, default=0)
    test_failed = Column(Integer, default=0)
    test_errors = Column(Integer, default=0)
    validation_success = Column(Boolean)

    # Timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)

    # File paths
    task_dir = Column(String(512))

    # Relationships
    task = relationship("Task", back_populates="task_instances")

    __table_args__ = (
        UniqueConstraint('instance_id', 'tag', name='uq_instance_tag'),
        Index('idx_task_instances_instance_tag', 'instance_id', 'tag'),
    )


class TaskLog(Base):
    """Task log model"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(20))
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    task = relationship("Task", back_populates="logs")
