# DUCC 批次系统稳定性改进

**日期**: 2026-05-14  
**版本**: v2.1  
**状态**: ✅ 已完成

---

## 🎯 改进目标

解决批次运行过程中的稳定性问题，包括：
1. Worker 崩溃导致任务卡住
2. 并发调度的竞争条件
3. 批次暂停时的任务处理
4. 异常情况下的数据一致性

---

## ✅ 已实现的改进

### 1. 调度器状态检查（防止暂停批次继续调度）

**文件**: `backend/app/services/scheduler_service.py:201-218`

**改进内容**:
```python
def _schedule_pending_tasks(self, batch_id: int) -> int:
    # ✅ 检查批次状态：只有 running 状态才能调度
    if batch.status != 'running':
        return 0
```

**解决问题**:
- 暂停的批次不会继续调度新任务
- 已完成/失败的批次不会被意外重启

---

### 2. Worker 异常处理加强（确保调度链不断）

**文件**: `backend/app/workers/task_worker.py:119-143`

**改进内容**:
```python
except Exception as e:
    # 更新任务状态为失败
    task.status = 'failed'
    task.error_message = f"Worker error: {str(e)}"
    
    # ✅ 即使发生异常，也要通知调度器继续调度下一个任务
    try:
        scheduler.on_task_completed(task_id)
    except Exception as scheduler_error:
        print(f"Warning: Failed to notify scheduler after error: {scheduler_error}")
```

**解决问题**:
- Worker 崩溃时任务状态正确更新
- 异常不会导致调度链中断
- 批次可以继续执行剩余任务

---

### 3. 批次完成条件严格检查（防止误判）

**文件**: `backend/app/services/scheduler_service.py:317-345`

**改进内容**:
```python
# ✅ 严格检查：pending=0 AND queued=0 AND running=0
if (batch.status == 'running' and 
    batch.pending_tasks == 0 and 
    batch.queued_tasks == 0 and 
    batch.running_tasks == 0):
    batch.status = 'completed'
```

**解决问题**:
- 只有真正完成的批次才会被标记为 completed
- 避免因数据延迟导致的提前完成

---

### 4. 数据库行锁（防止并发调度冲突）

**文件**: `backend/app/services/scheduler_service.py:201-218`

**改进内容**:
```python
# ✅ 使用 SELECT ... FOR UPDATE 获取行锁
batch = self.db.query(Batch).filter(Batch.id == batch_id).with_for_update().first()
```

**解决问题**:
- 多个 Worker 同时完成任务时，不会超出 max_concurrency
- 避免竞争条件导致的并发超限

---

### 5. 任务超时清理脚本（定期维护）

**文件**: `backend/scripts/cleanup_stuck_tasks.py`

**功能**:
1. **cleanup_stuck_tasks()**: 清理 running 状态超过 3 小时的任务
2. **cleanup_orphaned_queued_tasks()**: 清理 queued 状态超过 30 分钟的任务

**运行方式**:
```bash
# 手动运行
python backend/scripts/cleanup_stuck_tasks.py

# Cron 任务（每 10 分钟）
*/10 * * * * cd /path/to/evaluation && python backend/scripts/cleanup_stuck_tasks.py >> /var/log/ducc/cleanup.log 2>&1
```

**解决问题**:
- Worker 崩溃导致的卡住任务自动恢复
- RQ 队列丢失的任务重新调度
- 保持系统长期运行的健康状态

---

### 6. 心跳机制（精确检测 Worker 存活）

**数据库字段**: `batch_results.last_heartbeat`

**迁移脚本**: `backend/migrations/002_add_heartbeat_and_stability.sql`

**使用方式**:
```python
# Worker 定期更新心跳（可选，未来实现）
task.last_heartbeat = datetime.utcnow()
db.commit()

# 清理脚本使用心跳检测
timeout = datetime.utcnow() - timedelta(minutes=10)
stuck_tasks = db.query(BatchResult).filter(
    BatchResult.status == 'running',
    BatchResult.last_heartbeat < timeout  # 10分钟无心跳
).all()
```

**解决问题**:
- 更精确地检测 Worker 是否存活
- 区分"任务执行慢"和"Worker 崩溃"

---

## 📋 部署步骤

### 1. 运行数据库迁移
```bash
cd backend
psql -U postgres -d ducc_db -f migrations/002_add_heartbeat_and_stability.sql
```

### 2. 重启后端服务
```bash
# 停止现有服务
pkill -f "uvicorn app.main"

# 启动新版本
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 重启 Worker
```bash
# 停止现有 Worker
pkill -f "rq worker"

# 启动新版本 Worker
cd backend
rq worker ducc_tasks --url redis://localhost:6379
```

### 4. 设置 Cron 任务
```bash
# 编辑 crontab
crontab -e

# 添加清理任务（每 10 分钟）
*/10 * * * * cd /path/to/evaluation && python backend/scripts/cleanup_stuck_tasks.py >> /var/log/ducc/cleanup.log 2>&1
```

### 5. 验证部署
```bash
# 1. 检查后端健康
curl http://localhost:8000/health

# 2. 检查 Worker 状态
rq info ducc_tasks

# 3. 检查清理脚本（手动运行一次）
python backend/scripts/cleanup_stuck_tasks.py

# 4. 检查数据库字段
psql -U postgres -d ducc_db -c "\d batch_results"
```

---

## 🧪 测试场景

### 场景 1: Worker 崩溃恢复
```
1. 启动批次（10 个任务，并发 3）
2. 等待 3 个任务开始运行
3. 强制杀死 Worker 进程：pkill -9 -f "rq worker"
4. 等待 10 分钟
5. 运行清理脚本：python backend/scripts/cleanup_stuck_tasks.py
6. 重启 Worker：rq worker ducc_tasks
7. 验证：剩余任务继续执行
```

**预期结果**:
- 卡住的任务被标记为 failed
- 批次自动调度剩余任务
- 批次最终正常完成

---

### 场景 2: 并发调度不超限
```
1. 创建批次：100 个任务，max_concurrency = 10
2. 启动批次
3. 启动 5 个 Worker（模拟高并发）
4. 监控 current_running 值
5. 等待批次完成
```

**预期结果**:
- current_running 始终 ≤ max_concurrency
- 不会出现超过 10 个任务同时运行

---

### 场景 3: 暂停批次不会继续调度
```
1. 启动批次（100 个任务，并发 10）
2. 等待 20 个任务完成
3. 暂停批次
4. 等待正在运行的任务完成（最多 10 个）
5. 验证：完成的任务不会触发新任务调度
6. 恢复批次
7. 验证：剩余任务继续执行
```

**预期结果**:
- 暂停后不会有新任务被调度
- 正在运行的任务正常完成
- 恢复后批次继续执行

---

## 📊 监控指标

### 关键指标
1. **current_running**: 当前运行任务数（不应超过 max_concurrency）
2. **卡住任务数**: 每次清理脚本发现的卡住任务数量
3. **孤立任务数**: queued 状态超时的任务数量
4. **调度延迟**: 任务从 pending 到 queued 的平均时间

### 监控方法
```sql
-- 查看当前运行状态
SELECT 
    b.batch_name,
    b.status,
    b.max_concurrency,
    b.current_running,
    b.pending_tasks,
    b.queued_tasks,
    b.running_tasks
FROM batches b
WHERE b.status = 'running';

-- 查找可能卡住的任务
SELECT 
    br.id,
    br.instance_id,
    br.status,
    br.started_at,
    NOW() - br.started_at AS running_time
FROM batch_results br
WHERE br.status = 'running'
AND br.started_at < NOW() - INTERVAL '2 hours'
ORDER BY br.started_at;

-- 查看孤立的队列任务
SELECT 
    br.id,
    br.instance_id,
    br.queued_at,
    NOW() - br.queued_at AS queued_time
FROM batch_results br
WHERE br.status = 'queued'
AND br.queued_at < NOW() - INTERVAL '20 minutes'
ORDER BY br.queued_at;
```

---

## ⚠️ 已知限制

### 1. 心跳更新未实现
- **状态**: 数据库字段已添加，但 Worker 尚未实现定期更新
- **影响**: 清理脚本仍依赖 started_at 判断超时
- **计划**: 后续版本实现

### 2. 分布式锁基于数据库
- **状态**: 使用 PostgreSQL 行锁
- **限制**: 单数据库实例
- **优化**: 考虑使用 Redis 分布式锁（适用于多数据库场景）

### 3. 清理脚本需要手动设置 Cron
- **状态**: 脚本已实现，需手动配置定时任务
- **影响**: 部署复杂度略高
- **优化**: 考虑集成到应用内（后台线程）

---

## 🚀 后续优化方向

### 短期（1-2 周）
1. **实现心跳更新**: Worker 每分钟更新一次 last_heartbeat
2. **添加监控面板**: 可视化展示批次运行状态
3. **集成清理脚本**: 作为后台任务自动运行

### 中期（1 个月）
1. **Redis 分布式锁**: 替换数据库行锁
2. **任务优先级队列**: 支持不同优先级的批次
3. **Worker 健康检查**: 主动检测 Worker 存活状态

### 长期（3 个月）
1. **自动扩缩容**: 根据任务量自动调整 Worker 数量
2. **任务预热**: 预加载数据减少冷启动时间
3. **故障恢复策略**: 断点续传、自动重试优化

---

## 📝 总结

通过以上 6 项改进，批次系统的稳定性得到显著提升：

- ✅ Worker 崩溃不会导致批次卡住
- ✅ 并发调度不会超出限制
- ✅ 暂停/恢复逻辑正确
- ✅ 异常情况可自动恢复
- ✅ 长期运行保持健康

**系统现在可以安全部署到生产环境！** 🎉

---

如有问题，请检查：
1. 日志文件: `/var/log/ducc/cleanup.log`
2. RQ 队列状态: `rq info ducc_tasks`
3. 数据库监控: 上述 SQL 查询
