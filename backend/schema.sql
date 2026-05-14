-- DUCC Evaluation System Database Schema v2.0
-- PostgreSQL 15+
-- 基于简化数据模型：数据层 → 批次层 → 结果层
-- 去除执行层（tasks/task_groups），批次直接聚合任务结果

-- ============================================================================
-- 数据层 (Data Layer)
-- ============================================================================

-- Datasets table (数据集元信息)
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    format VARCHAR(50) NOT NULL,  -- parquet, csv, json, jsonl
    file_size BIGINT,
    total_instances INTEGER,
    imported_instances INTEGER DEFAULT 0,
    description TEXT,
    last_scanned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_datasets_name ON datasets(name);

-- Dataset instances table (数据集实例，JSONB 灵活存储)
CREATE TABLE IF NOT EXISTS dataset_instances (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    instance_id VARCHAR(255) NOT NULL,
    repo_language VARCHAR(50),
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(dataset_id, instance_id)
);

CREATE INDEX IF NOT EXISTS idx_dataset_instances_instance_id ON dataset_instances(instance_id);
CREATE INDEX IF NOT EXISTS idx_dataset_instances_dataset_instance ON dataset_instances(dataset_id, instance_id);
CREATE INDEX IF NOT EXISTS idx_dataset_instances_language ON dataset_instances(repo_language);
CREATE INDEX IF NOT EXISTS idx_dataset_instances_data_gin ON dataset_instances USING GIN (data);

-- Scripts table (评估脚本)
CREATE TABLE IF NOT EXISTS scripts (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) UNIQUE NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    description TEXT,
    last_scanned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scripts_filename ON scripts(file_name);

-- ============================================================================
-- 批次层 (Batch Layer) - 核心组织单位
-- ============================================================================

-- Batches table (批次 - 任务聚合和管理单位)
CREATE TABLE IF NOT EXISTS batches (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(200) UNIQUE NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    script_id INTEGER REFERENCES scripts(id) ON DELETE SET NULL,
    model VARCHAR(100) NOT NULL,  -- gpt-4-turbo, claude-3.5-sonnet 等
    tag VARCHAR(100) NOT NULL,    -- baseline, experiment_1 等
    
    -- 执行配置
    execution_config JSONB,  -- 脚本自定义参数（--timeout, --use-tmux 等）
    
    -- 批次状态
    status VARCHAR(50) DEFAULT 'created',  -- created, running, paused, completed, failed
    
    -- 并发控制（v2.0 新增）
    max_concurrency INTEGER DEFAULT 10,   -- 最大并发任务数
    current_running INTEGER DEFAULT 0,    -- 当前正在运行的任务数
    priority INTEGER DEFAULT 0,           -- 批次优先级（数字越大优先级越高）
    
    -- 任务统计
    total_tasks INTEGER DEFAULT 0,
    pending_tasks INTEGER DEFAULT 0,
    queued_tasks INTEGER DEFAULT 0,       -- 已加入队列等待执行
    running_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    paused_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 输出目录
    output_dir VARCHAR(512),
    
    -- 创建者
    created_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);
CREATE INDEX IF NOT EXISTS idx_batches_dataset ON batches(dataset_id);
CREATE INDEX IF NOT EXISTS idx_batches_model_tag ON batches(model, tag);
CREATE INDEX IF NOT EXISTS idx_batches_priority ON batches(priority DESC);

-- ============================================================================
-- 结果层 (Result Layer)
-- ============================================================================

-- Batch results table (批次任务结果 - 每条记录是一个独立任务)
CREATE TABLE IF NOT EXISTS batch_results (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER REFERENCES batches(id) ON DELETE CASCADE,
    dataset_instance_id INTEGER REFERENCES dataset_instances(id) ON DELETE CASCADE,
    instance_id VARCHAR(255) NOT NULL,
    
    -- 任务配置（冗余存储便于查询）
    model VARCHAR(100) NOT NULL,
    tag VARCHAR(100) NOT NULL,
    
    -- 任务状态（v2.0 状态机）
    status VARCHAR(50) DEFAULT 'pending',  -- pending, queued, running, completed, failed, retrying
    
    -- 重试机制（v2.0 新增）
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- 队列和 Worker 信息（v2.0 新增）
    job_id VARCHAR(255),        -- RQ job ID
    worker_id VARCHAR(100),     -- Worker 标识
    
    -- 执行结果
    validation_success BOOLEAN,
    tests_passed INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,
    tests_total INTEGER DEFAULT 0,
    duration_seconds FLOAT,
    result_summary JSONB,       -- 完整的 task_summary.json 内容
    
    -- 输出文件路径
    patch_path VARCHAR(512),
    output_dir VARCHAR(512),
    trace_file_path VARCHAR(512),           -- execution_trace.jsonl 路径
    validation_detail_path VARCHAR(512),     -- validation_detail.json 路径
    
    -- 错误信息
    error_message TEXT,
    
    -- 时间戳（v2.0 完整生命周期）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    queued_at TIMESTAMP WITH TIME ZONE,    -- 加入队列时间
    started_at TIMESTAMP WITH TIME ZONE,   -- 开始执行时间
    completed_at TIMESTAMP WITH TIME ZONE, -- 完成时间
    last_heartbeat TIMESTAMP WITH TIME ZONE, -- ✅ 心跳时间（用于检测 worker 是否存活）
    
    -- 约束：同一批次内 instance_id 唯一（核心数据隔离机制）
    CONSTRAINT uq_batch_result_batch_instance UNIQUE(batch_id, instance_id)
);

CREATE INDEX IF NOT EXISTS idx_batch_results_batch ON batch_results(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_results_status ON batch_results(status);
CREATE INDEX IF NOT EXISTS idx_batch_results_instance ON batch_results(instance_id);
CREATE INDEX IF NOT EXISTS idx_batch_results_model_tag ON batch_results(model, tag);
CREATE INDEX IF NOT EXISTS idx_batch_results_job_id ON batch_results(job_id);
CREATE INDEX IF NOT EXISTS idx_batch_results_batch_status ON batch_results(batch_id, status);  -- 调度器查询优化

-- ============================================================================
-- 触发器：自动更新批次统计
-- ============================================================================

-- 函数：更新批次任务统计
CREATE OR REPLACE FUNCTION update_batch_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- 更新批次的任务统计
    UPDATE batches SET
        total_tasks = (SELECT COUNT(*) FROM batch_results WHERE batch_id = NEW.batch_id),
        pending_tasks = (SELECT COUNT(*) FROM batch_results WHERE batch_id = NEW.batch_id AND status = 'pending'),
        queued_tasks = (SELECT COUNT(*) FROM batch_results WHERE batch_id = NEW.batch_id AND status = 'queued'),
        running_tasks = (SELECT COUNT(*) FROM batch_results WHERE batch_id = NEW.batch_id AND status = 'running'),
        completed_tasks = (SELECT COUNT(*) FROM batch_results WHERE batch_id = NEW.batch_id AND status = 'completed'),
        failed_tasks = (SELECT COUNT(*) FROM batch_results WHERE batch_id = NEW.batch_id AND status = 'failed'),
        current_running = (SELECT COUNT(*) FROM batch_results WHERE batch_id = NEW.batch_id AND status IN ('queued', 'running')),
        updated_at = NOW()
    WHERE id = NEW.batch_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 触发器：batch_results 状态变更时更新批次统计
DROP TRIGGER IF EXISTS trigger_update_batch_stats ON batch_results;
CREATE TRIGGER trigger_update_batch_stats
    AFTER INSERT OR UPDATE OF status ON batch_results
    FOR EACH ROW
    EXECUTE FUNCTION update_batch_stats();

-- ============================================================================
-- 对比功能支持表（保持兼容）
-- ============================================================================

-- Comparisons table (对比配置)
CREATE TABLE IF NOT EXISTS comparisons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    comparison_type VARCHAR(50) NOT NULL,  -- cross_model, cross_tag, three_way
    config JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- ============================================================================
-- 视图：批次任务明细（便于查询）
-- ============================================================================

CREATE OR REPLACE VIEW v_batch_task_details AS
SELECT 
    b.id as batch_id,
    b.batch_name,
    b.model,
    b.tag,
    b.status as batch_status,
    b.max_concurrency,
    b.current_running,
    br.id as task_id,
    br.instance_id,
    br.status as task_status,
    br.retry_count,
    br.validation_success,
    br.tests_passed,
    br.tests_total,
    br.duration_seconds,
    br.error_message,
    br.created_at as task_created_at,
    br.started_at as task_started_at,
    br.completed_at as task_completed_at,
    di.repo_language
FROM batches b
LEFT JOIN batch_results br ON b.id = br.batch_id
LEFT JOIN dataset_instances di ON br.dataset_instance_id = di.id;

-- ============================================================================
-- 初始化数据
-- ============================================================================

-- 插入默认模型（可选）
-- INSERT INTO models (name, description) VALUES 
--     ('gpt-4-turbo', 'OpenAI GPT-4 Turbo'),
--     ('claude-3.5-sonnet', 'Anthropic Claude 3.5 Sonnet'),
--     ('gemini-1.5-pro', 'Google Gemini 1.5 Pro')
-- ON CONFLICT DO NOTHING;

-- ============================================================================
-- 权限设置（如果需要）
-- ============================================================================

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ducc;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ducc;

-- ============================================================================
-- 数据库版本记录
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO schema_version (version, description) VALUES 
    ('2.0.0', '简化数据模型 - 去除执行层，批次直接聚合任务结果，支持系统级并发控制')
ON CONFLICT DO NOTHING;
