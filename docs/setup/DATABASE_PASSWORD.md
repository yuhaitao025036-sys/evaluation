# 🔐 数据库密码配置说明

⚠️ **重要安全提示**：本文档不应包含真实密码！请使用占位符。

## 配置说明

### PostgreSQL 数据库

- **数据库名**: `ducc_evaluation`
- **用户名**: `ducc_user`  
- **密码**: `YOUR_GENERATED_PASSWORD` （请自行生成强密码，24位以上随机字符）
- **容器名**: `eval_postgres` （通用名称）

### Redis

- **容器名**: `eval_redis` （通用名称）
- **端口**: 6379
- **无密码**（localhost 访问，安全）

### 队列名

- **RQ 队列**: `eval-tasks` （通用名称）

---

## 🔒 安全说明

### 密码强度要求

生成的密码应符合以下安全要求：

- ✅ 24 位以上长度
- ✅ 包含大写字母
- ✅ 包含小写字母
- ✅ 包含数字
- ✅ 随机生成，不含常见单词

### 密码生成命令

```bash
# 使用 openssl 生成密码（推荐）
openssl rand -base64 32

# 或使用 Python 生成强密码
python3 -c "import secrets, string; chars = string.ascii_letters + string.digits; print(''.join(secrets.choice(chars) for _ in range(24)))"
```

### 保护措施

1. **永远不要在文档中记录真实密码！**
   - 使用占位符如 `YOUR_GENERATED_PASSWORD`
   - 真实密码仅存储在本地配置文件中

2. **不要提交到 Git**
   - `docker-compose.yml` 已添加到 `.gitignore`
   - `backend/app/config.py` 已添加到 `.gitignore`

3. **文件权限**
   ```bash
   chmod 600 docker-compose.yml
   chmod 600 backend/app/config.py
   ```

4. **生产环境**
   - 使用环境变量替代硬编码
   - 定期更换密码（建议每季度）
   - 使用密钥管理服务（如 AWS Secrets Manager）

---

## 📝 配置位置

### 需要配置密码的文件

⚠️ **注意**：以下文件包含真实密码，已被 `.gitignore` 忽略，不会提交到 Git

1. **docker-compose.yml** (第 39 行)
   ```yaml
   POSTGRES_PASSWORD: YOUR_GENERATED_PASSWORD
   ```
   - 从 `docker-compose.yml.example` 复制并修改

2. **backend/app/config.py** (第 17 行)
   ```python
   DATABASE_URL: str = "postgresql://ducc_user:YOUR_GENERATED_PASSWORD@localhost:5432/ducc_evaluation"
   ```
   - 从 `backend/app/config.py.example` 复制并修改

### 示例配置文件（可以提交到 Git）

这些文件使用占位符，可以安全地提交：

- `docker-compose.yml.example`
- `backend/app/config.py.example`

---

## 🔄 首次配置流程

### 步骤 1: 生成密码

```bash
# 生成强密码
openssl rand -base64 32
```

### 步骤 2: 创建配置文件

```bash
# 从示例文件复制
cp docker-compose.yml.example docker-compose.yml
cp backend/app/config.py.example backend/app/config.py
```

### 步骤 3: 替换密码

在以下文件中将 `YOUR_GENERATED_PASSWORD` 替换为你生成的密码：
- `docker-compose.yml` (第 39 行)
- `backend/app/config.py` (第 17 行)

### 步骤 4: 设置文件权限

```bash
chmod 600 docker-compose.yml
chmod 600 backend/app/config.py
```

### 步骤 5: 启动服务

```bash
docker-compose up -d
```

---

## 🔄 修改密码（如需更换）

### 生成新密码

```bash
# 使用 openssl 生成
openssl rand -base64 32
```

#### 更新配置

1. 修改 `docker-compose.yml` 第 39 行的 `POSTGRES_PASSWORD`
2. 修改 `backend/app/config.py` 第 17 行的 `DATABASE_URL`
3. 重启服务：
   ```bash
   docker-compose down
   docker-compose up -d
   ```

---

## ✅ 验证配置

### 测试数据库连接

```bash
# 方式 1: 使用 Docker
docker exec eval_postgres psql -U ducc_user ducc_evaluation -c "SELECT version();"

# 方式 2: 使用 Python
cd backend
conda activate dejavu
python -c "from app.database import engine; print(engine.connect())"
```

### 查看容器状态

```bash
# 查看所有容器
docker-compose ps

# 查看 PostgreSQL 日志
docker-compose logs eval_postgres

# 查看 Redis 日志  
docker-compose logs eval_redis
```

---

## 🚨 安全检查清单

- [x] 密码不是默认密码（ducc_pass）
- [x] 密码长度 >= 16 位
- [x] 密码包含大小写字母和数字
- [x] .env 文件权限设置为 600
- [x] .env 文件已添加到 .gitignore
- [x] 容器名使用通用名称（eval_*）
- [x] 数据库仅监听 localhost
- [x] 备份脚本中无明文密码

---

## 📞 故障排查

### 问题 1: 无法连接数据库

```bash
# 检查配置文件中的密码是否一致
grep POSTGRES_PASSWORD docker-compose.yml
grep DATABASE_URL backend/.env

# 确保所有配置文件中的密码一致
```

### 问题 2: 容器无法启动

```bash
# 查看容器日志
docker-compose logs eval_postgres

# 常见原因：数据目录权限问题
sudo chown -R 999:999 /home/dejavu/docker-data/postgres/data
```

### 问题 3: 密码修改后无法连接

```bash
# 完全重启容器
docker-compose down
docker-compose up -d

# 或删除数据重新初始化
rm -rf /home/dejavu/docker-data/postgres/data/*
docker-compose up -d
```

---

## 🔗 相关文档

- [Docker 数据存储](DOCKER_DATA_STORAGE.md)
- [备份定时任务配置](BACKUP_CRON_SETUP.md)
- [部署文档](DEPLOYMENT.md)

---

**⚠️ 重要提醒：永远不要在文档或代码中记录真实密码！** 🔐
