# Conda 环境适配总结

## 背景

用户使用 Conda 环境而不是 venv：
- 环境名: `dejavu`
- Python 版本: 3.12.10
- 已存在，无需创建

## 修改内容

### 1. 启动脚本

#### backend/start_backend.sh
```bash
# 改动前
source venv/bin/activate

# 改动后
eval "$(conda shell.bash hook)"
conda activate dejavu
```

#### backend/start_worker.sh
```bash
# 改动前
source venv/bin/activate

# 改动后
eval "$(conda shell.bash hook)"
conda activate dejavu
```

### 2. 安装脚本

#### backend/install.sh
- 检查 conda 而不是 Python
- 检测 dejavu 环境是否存在
- 如不存在，提供创建选项
- 支持 conda install 或 pip install 安装依赖
- 激活 dejavu 环境进行后续操作

### 3. 快速启动脚本

#### quickstart.sh
- 添加 conda 检查
- 检测 dejavu 环境状态
- 初始化 conda for bash
- 在所有 Python 操作前激活 dejavu

### 4. 新增文档

#### docs/CONDA_SETUP.md
- Conda 环境配置说明
- 激活和使用方法
- 常见问题解决
- 与 venv 的对比

## 使用方法

### 快速开始

```bash
# 1. 启动数据库
docker-compose up -d

# 2. 启动 Backend
cd backend
./start_backend.sh

# 3. 启动 Worker (新终端)
cd backend
./start_worker.sh
```

### 手动方式

```bash
# 激活环境
conda activate dejavu

# 验证
python --version  # Python 3.12.10

# 安装依赖（如需要）
cd backend
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 Worker (新终端)
conda activate dejavu
python worker.py
```

## 关键改动点

### 1. 环境检查
```bash
# 检查 conda 环境是否存在
if ! conda env list | grep -q "^dejavu "; then
    echo "环境不存在"
fi
```

### 2. 激活环境
```bash
# 初始化 conda（确保 conda activate 可用）
eval "$(conda shell.bash hook)"

# 激活 dejavu 环境
conda activate dejavu
```

### 3. Python 命令
```bash
# 改动前
python3 -c "..."

# 改动后
python -c "..."  # conda 环境中 python 即 python3
```

## 验证

### 检查环境

```bash
conda env list | grep dejavu
# 输出: dejavu    /path/to/conda/envs/dejavu
```

### 检查 Python 版本

```bash
conda activate dejavu
python --version
# 输出: Python 3.12.10
```

### 测试启动脚本

```bash
cd backend

# 测试 Backend 启动
./start_backend.sh
# 应该看到: 
# ====================================
# 启动 DUCC Evaluation Backend API
# ====================================
# 激活 conda 环境 dejavu...
# Python 版本: Python 3.12.10
# ✓ 环境检查通过

# 测试 Worker 启动  
./start_worker.sh
# 应该看到:
# ====================================
# 启动 DUCC Evaluation Worker
# ====================================
# 激活 conda 环境 dejavu...
# Python 版本: Python 3.12.10
# ✓ 环境检查通过
```

## 文件清单

**修改的文件（4个）:**
1. `backend/start_backend.sh` - 使用 conda activate
2. `backend/start_worker.sh` - 使用 conda activate
3. `backend/install.sh` - 适配 conda 环境
4. `quickstart.sh` - 添加 conda 检查

**新增文件（1个）:**
1. `docs/CONDA_SETUP.md` - Conda 使用说明

## 兼容性

所有脚本已完全适配 conda 环境：
- ✅ 自动检测 conda
- ✅ 验证 dejavu 环境存在
- ✅ 正确激活环境
- ✅ 使用正确的 Python 命令
- ✅ 友好的错误提示

## 注意事项

### 1. Conda 初始化

确保 conda 已正确初始化：
```bash
conda init bash  # 或 zsh
source ~/.bashrc  # 或 ~/.zshrc
```

### 2. 环境变量

`.env` 文件中的路径配置不受影响，仍使用绝对路径。

### 3. Docker 访问

Worker 仍需要访问宿主机 Docker，与使用 venv 时相同。

### 4. 数据库连接

使用 localhost 连接 Docker 中的 PostgreSQL 和 Redis，不受环境管理工具影响。

## 后续使用

用户现在可以：

1. **正常使用启动脚本**
   ```bash
   ./start_backend.sh
   ./start_worker.sh
   ```

2. **手动激活环境**
   ```bash
   conda activate dejavu
   ```

3. **查看文档**
   ```bash
   cat docs/CONDA_SETUP.md
   ```

所有功能保持不变，只是底层使用 conda 而不是 venv 管理 Python 环境。

## 总结

✅ 所有脚本已适配 conda 环境 dejavu
✅ 保持与原有功能完全兼容
✅ 添加详细的 conda 使用文档
✅ 提供友好的错误提示和指引

**用户现在可以直接使用所有脚本，无需额外配置！**
