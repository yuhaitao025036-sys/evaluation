export interface Dataset {
  id: number
  name: string
  description: string | null
  file_name?: string
  file_path?: string
  format?: string
  file_size?: number
  total_instances?: number
  imported_instances?: number
  last_scanned_at?: string | null
  created_at: string
  updated_at?: string
}

export interface DatasetInstance {
  id: number
  dataset_id: number
  instance_id: string
  repo_language?: string | null
  data: Record<string, any>
  created_at: string
  updated_at?: string
}

export interface ScriptArgument {
  name: string
  cli_name: string
  type: 'string' | 'int' | 'float' | 'boolean' | 'choice'
  required?: boolean
  default?: any
  help?: string | null
  choices?: string[] | null
  action?: string | null
}

export interface Script {
  id: number
  name?: string
  file_name?: string
  description: string | null
  file_path: string
  argument_schema?: ScriptArgument[]
  last_scanned_at?: string | null
  created_at: string
  updated_at?: string
}

export interface TaskGroup {
  id: number
  name: string
  description: string | null
  dataset_id: number
  script_id: number
  tag: string
  model: string | null
  concurrency: number
  filter_conditions: Record<string, any> | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  created_at: string
  updated_at: string
  dataset?: Dataset
  script?: Script
}

export interface Task {
  id: number
  task_group_id: number
  batch_index: number
  model: string | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface TaskInstance {
  id: number
  task_id: number
  instance_id: string
  tag: string
  model: string | null
  input_data: Record<string, any>
  result_data: Record<string, any> | null
  patch_content: string | null
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timeout'
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  duration: number | null
  created_at: string
  updated_at: string
}

export interface TaskLog {
  id: number
  task_id: number
  log_level: 'info' | 'warning' | 'error'
  message: string
  created_at: string
}

export interface Comparison {
  id: number
  name: string
  description: string | null
  baseline_tag: string
  comparison_tags: string[]
  model: string | null
  filter_conditions: Record<string, any> | null
  result_summary: Record<string, any> | null
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface TaskGroupStats {
  total: number
  pending: number
  running: number
  completed: number
  failed: number
  success_rate: number
}

export interface ComparisonMetadataBatch {
  id: number
  batch_name: string
  dataset_id: number | null
  model: string
  tag: string
  status: string
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
}

export interface ComparisonMetadata {
  models: string[]
  tags: string[]
  datasets: Array<{ id: number; name: string }>
  batches: ComparisonMetadataBatch[]
}

export interface CompareBatchesRequest {
  batch_ids: number[]
  include_instances?: boolean
  instance_limit?: number
  only_common_instances?: boolean
}

export interface CompareByModelsRequest {
  models: string[]
  dataset_id?: number
  tag?: string
  include_instances?: boolean
  instance_limit?: number
  only_common_instances?: boolean
}

export interface CompareByTagsRequest {
  tags: string[]
  dataset_id?: number
  model?: string
  include_instances?: boolean
  instance_limit?: number
  only_common_instances?: boolean
}

export interface CompareInstanceRequest {
  instance_id: string
  batch_ids?: number[]
  models?: string[]
  tags?: string[]
  dataset_id?: number
}

export interface ComparisonRunSummary {
  key: string
  batch_id: number | null
  batch_name: string | null
  model: string
  tag: string
  dataset_id: number | null
  total: number
  completed: number
  failed: number
  validation_success: number
  validation_failure: number
  validation_unknown: number
  accuracy: number | null
  evaluation_success_rate: number | null
  test_pass_rate: number | null
  avg_duration_seconds: number | null
}

export interface ComparisonInstanceCell {
  batch_id: number
  batch_name: string
  model: string
  tag: string
  status: string
  validation_success: boolean | null
  tests_passed: number
  tests_failed: number
  tests_total: number
  duration_seconds: number | null
  has_patch: boolean
  result_summary: Record<string, any> | null
}

export interface ComparisonInstanceRow {
  instance_id: string
  outcome: string
  results: Record<string, ComparisonInstanceCell | null>
}

export interface ComparisonResponse {
  mode: 'batches' | 'models' | 'tags'
  keys: string[]
  summaries: Record<string, ComparisonRunSummary>
  compared_instances: number
  total_union_instances: number
  common_instances: number
  instance_rows: ComparisonInstanceRow[]
}

export interface InstanceComparisonResponse {
  instance_id: string
  results: ComparisonInstanceCell[]
}

// ============================================================================
// 批次系统类型定义 (v2.0)
// ============================================================================

export interface Batch {
  id: number
  batch_name: string
  dataset_id: number
  script_id: number
  model: string
  tag: string
  
  // 批次状态
  status: 'created' | 'running' | 'paused' | 'completed' | 'failed'
  
  // 并发控制
  max_concurrency: number
  current_running: number
  priority: number
  
  // 任务统计
  total_tasks: number
  pending_tasks: number
  queued_tasks: number
  running_tasks: number
  completed_tasks: number
  failed_tasks: number
  
  // 时间戳
  created_at: string
  started_at: string | null
  paused_at: string | null
  completed_at: string | null
  updated_at: string
  
  // 输出目录
  output_dir: string
  
  // 关联对象
  dataset?: Dataset
  script?: Script
  
  // 执行配置
  execution_config?: Record<string, any>
  created_by?: string
}

export interface BatchResult {
  id: number
  batch_id: number
  dataset_instance_id: number
  instance_id: string
  
  // 任务配置
  model: string
  tag: string
  
  // 任务状态
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'retrying'
  
  // 重试机制
  retry_count: number
  max_retries: number
  
  // 队列信息
  job_id: string | null
  worker_id: string | null
  
  // 执行结果
  validation_success: boolean | null
  tests_passed: number
  tests_failed: number
  tests_total: number
  duration_seconds: number | null
  result_summary: Record<string, any> | null
  
  // 输出文件
  patch_path: string | null
  output_dir: string
  trace_file_path?: string | null
  validation_detail_path?: string | null

  // 错误信息
  error_message: string | null
  
  // 时间戳
  created_at: string
  queued_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface BatchStats {
  batch_id: number
  batch_name: string
  status: string
  effective_status: string
  outcome: string
  total_tasks: number
  pending_tasks: number
  queued_tasks: number
  running_tasks: number
  retrying_tasks: number
  completed_tasks: number
  failed_tasks: number
  active_tasks: number
  terminal_tasks: number
  completion_rate: number
  task_success_rate: number
  task_failure_rate: number
  success_rate: number
  failure_rate: number
  validation_success_count: number
  validation_failure_count: number
  validation_unknown_count: number
  validation_success_rate: number | null
  validation_failure_rate: number | null
  evaluation_success_rate: number
  evaluation_failure_rate: number
  tests_passed: number
  tests_failed: number
  tests_total: number
  test_pass_rate: number | null
  avg_duration: number | null
  total_duration: number | null
}

export interface BatchCreateRequest {
  batch_name: string
  dataset_id: number
  script_id: number
  model: string
  tag: string
  
  // 实例选择（三选一）
  instance_ids?: string[]
  start_index?: number
  end_index?: number
  filter_conditions?: Record<string, any>
  
  // 追加模式
  append_to_existing?: boolean
  overwrite_existing?: boolean
  
  // 配置
  max_concurrency?: number
  max_retries?: number
  priority?: number
  execution_config?: Record<string, any>
  created_by?: string
}

export interface BatchAddTasksRequest {
  instance_ids?: string[]
  start_index?: number
  end_index?: number
  filter_conditions?: Record<string, any>
  overwrite_existing?: boolean
}
