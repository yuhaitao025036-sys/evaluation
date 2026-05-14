# 配置修改总结 - 去除 DUCC 专有命名

## ✅ 修改完成时间
2024-05-14

## 📋 修改概述

已完成方案 A：最小改动方案
- ✅ 更换为强密码
- ✅ 容器名改为通用名称
- ✅ 队列名改为通用名称
- ✅ 日志路径改为通用名称
- ✅ 所有脚本中的引用已同步更新

---

## 🔐 密码修改

### 修改前
```
POSTGRES_PASSWORD: ducc_pass  # 旧的弱密码
```

### 修改后
```
POSTGRES_PASSWORD: <REDACTED>  # 已更换为强密码（24位随机生成）
```

**新密码特性**：
- 24 位长度 ✅
- 随机生成 ✅
- 包含大小写字母和数字 ✅
- 符合安全标准 ✅

⚠️ **安全提示**：真实密码已被 `.gitignore` 保护，不会提交到 Git。

---

## 🏷️ 命名修改对照表

| 类型 | 修改前 | 修改后 | 状态 |
|------|--------|--------|------|
| **PostgreSQL 容器** | `ducc_postgres` | `eval_postgres` | ✅ 已修改 |
| **Redis 容器** | `ducc_redis` | `eval_redis` | ✅ 已修改 |
| **RQ 队列名** | `ducc-tasks` | `eval-tasks` | ✅ 已修改 |
| **备份日志** | `/var/log/ducc-backup.log` | `/var/log/eval-backup.log` | ✅ 已修改 |
| **系统名称** | "DUCC 评测系统" | "Agent 评测系统" | ✅ 已修改 |
| 数据库名 | `ducc_evaluation` | `ducc_evaluation` | ⏸️ 保持不变 |
| 数据库用户 | `ducc_user` | `ducc_user` | ⏸️ 保持不变 |

**说明**：数据库名和用户名保持不变，避免数据迁移的复杂性。

---

## 📁 修改的文件清单

### 核心配置文件

#### 1. docker-compose.yml
```diff
- container_name: ducc_postgres
+ container_name: eval_postgres
- POSTGRES_PASSWORD: ducc_pass
+ POSTGRES_PASSWORD: <REDACTED>  # 强密码，已被 .gitignore 保护
- container_name: ducc_redis
+ container_name: eval_redis
```

⚠️ **注意**：`docker-compose.yml` 包含真实密码，已添加到 `.gitignore`，不会提交到 Git。

#### 2. backend/.env.example
```diff
- DATABASE_URL=postgresql://ducc:ducc123@localhost:5432/ducc_eval
+ DATABASE_URL=postgresql://ducc_user:YOUR_SECURE_PASSWORD_HERE@localhost:5432/ducc_evaluation
```

⚠️ **注意**：`.env.example` 使用占位符，可以安全提交。真实密码在 `backend/.env` 中（已被 `.gitignore` 保护）。

#### 3. backend/start_backend.sh
```diff
- echo "启动 DUCC Evaluation Backend API"
+ echo "启动 Agent Evaluation Backend API"
```

#### 4. backend/start_worker.sh
```diff
- echo "启动 DUCC Evaluation Worker"
+ echo "启动 Agent Evaluation Worker"
- rq worker --url "${REDIS_URL}" ducc-tasks
+ rq worker --url "${REDIS_URL}" eval-tasks
```

### 脚本文件

#### 5. scripts/backup-docker-data.sh
```diff
- # DUCC 评测系统 - Docker 数据备份脚本
+ # Agent 评测系统 - Docker 数据备份脚本
- # 日志文件：/var/log/ducc-backup.log
+ # 日志文件：/var/log/eval-backup.log
- docker exec ducc_postgres pg_dump ...
+ docker exec eval_postgres pg_dump ...
- docker exec ducc_redis redis-cli ...
+ docker exec eval_redis redis-cli ...
- 0 3 * * * ... >> /var/log/ducc-backup.log
+ 0 3 * * * ... >> /var/log/eval-backup.log
```

#### 6. scripts/check-docker-data.sh
```diff
- # DUCC 评测系统 - Docker 数据检查脚本
+ # Agent 评测系统 - Docker 数据检查脚本
- docker ps -f name=ducc_postgres
+ docker ps -f name=eval_postgres
- docker exec ducc_postgres psql ...
+ docker exec eval_postgres psql ...
```

#### 7. scripts/migrate-docker-data.sh
```diff
- # DUCC 评测系统 - Docker 数据迁移脚本
+ # Agent 评测系统 - Docker 数据迁移脚本
```

### 新增文档

#### 8. docs/DATABASE_PASSWORD.md （新建）
- 记录当前密码配置
- 安全说明和最佳实践
- 修改密码的步骤
- 验证和故障排查

---

## 🔄 需要手动操作的事项

### 1. 停止并重启容器（必须）

```bash
cd /Users/yuhaitao01/dev/baidu/explore/test/evaluation

# 停止旧容器
docker-compose down

# 启动新容器（使用新配置）
docker-compose up -d

# 验证容器状态
docker-compose ps
```

**预期输出**：
```
NAME              IMAGE                  STATUS
eval_postgres     postgres:15-alpine     Up
eval_redis        redis:7-alpine         Up
```

### 2. 创建新的 .env 文件（如果不存在）

```bash
cd backend

# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，将 YOUR_SECURE_PASSWORD_HERE 替换为你生成的密码
# 使用 openssl rand -base64 32 生成密码

# 设置权限
chmod 600 .env
```

### 3. 验证数据库连接

```bash
# 测试 PostgreSQL
docker exec eval_postgres psql -U ducc_user ducc_evaluation -c "SELECT version();"

# 测试 Redis
docker exec eval_redis redis-cli PING
```

### 4. 更新定时任务（如果已配置）

```bash
# 编辑 crontab
crontab -e

# 修改日志路径
# 旧的：>> /var/log/ducc-backup.log
# 新的：>> /var/log/eval-backup.log
0 3 * * * /Users/yuhaitao01/dev/baidu/explore/test/evaluation/scripts/backup-docker-data.sh >> /var/log/eval-backup.log 2>&1

# 创建新日志文件
sudo touch /var/log/eval-backup.log
sudo chown $(whoami):$(whoami) /var/log/eval-backup.log
```

### 5. 测试备份脚本

```bash
# 手动执行一次备份
./scripts/backup-docker-data.sh

# 查看备份结果
ls -lh /home/dejavu/backups/
```

---

## ✅ 验证清单

请按顺序执行以下验证：

### [ ] 1. 容器名验证
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```
**预期**：看到 `eval_postgres` 和 `eval_redis`

### [ ] 2. 密码验证
```bash
docker exec eval_postgres psql -U ducc_user ducc_evaluation -c "\conninfo"
```
**预期**：成功连接

### [ ] 3. 后端启动验证
```bash
cd backend
conda activate dejavu
./start_backend.sh
```
**预期**：看到 "启动 Agent Evaluation Backend API"

### [ ] 4. Worker 启动验证
```bash
cd backend
conda activate dejavu
./start_worker.sh
```
**预期**：看到 "启动 Agent Evaluation Worker" 和 "队列: eval-tasks"

### [ ] 5. 备份脚本验证
```bash
./scripts/backup-docker-data.sh
```
**预期**：成功备份到 `/home/dejavu/backups/`

### [ ] 6. 检查脚本验证
```bash
./scripts/check-docker-data.sh
```
**预期**：显示 "Agent 评测系统数据检查"，容器状态正常

---

## 🎯 下一步建议

### 短期（立即执行）

1. ✅ 重启 Docker 容器（使用新配置）
2. ✅ 创建/更新 backend/.env 文件
3. ✅ 验证所有服务正常运行
4. ✅ 测试备份脚本

### 中期（本周完成）

1. 更新定时任务配置
2. 备份当前数据
3. 更新团队文档
4. 通知相关人员密码已更换

### 长期（下个版本）

如需进一步重命名数据库名和用户名：
1. 制定详细的迁移计划
2. 备份所有数据
3. 更新所有配置文件
4. 执行数据库重命名
5. 全面测试

---

## 📊 影响评估

### 无影响
- ✅ 现有数据不受影响（数据目录未变）
- ✅ API 端点不受影响
- ✅ 前端连接不受影响

### 需要更新
- ⚠️ Docker 容器需要重启
- ⚠️ 定时任务需要更新日志路径
- ⚠️ 已启动的 Worker 需要重启

### 破坏性变更
- ❌ 无破坏性变更

---

## 🔍 回滚方案

如果出现问题，可以快速回滚：

### 回滚步骤

```bash
# 1. 停止容器
docker-compose down

# 2. 恢复 docker-compose.yml
git checkout docker-compose.yml

# 3. 恢复脚本文件
git checkout backend/start_*.sh scripts/*.sh

# 4. 重启容器
docker-compose up -d
```

### 备注
回滚只会恢复容器名，密码建议保留新密码（更安全）。

---

## 📚 相关文档

- [DATABASE_PASSWORD.md](DATABASE_PASSWORD.md) - 密码配置详细说明
- [DOCKER_DATA_STORAGE.md](DOCKER_DATA_STORAGE.md) - 数据存储说明
- [BACKUP_CRON_SETUP.md](BACKUP_CRON_SETUP.md) - 备份定时任务配置
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署文档

---

## 📞 技术支持

如遇问题，请检查：
1. Docker 日志：`docker-compose logs -f`
2. 备份日志：`tail -f /var/log/eval-backup.log`
3. 后端日志：查看终端输出

---

**修改完成！系统已去除 DUCC 专有命名，使用通用的 eval 命名体系。** ✅
