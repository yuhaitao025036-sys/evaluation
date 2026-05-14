# Conda 环境配置说明

本项目使用 Conda 环境 `dejavu` (Python 3.12.10)。

## 快速开始

### 1. 确认 Conda 已安装

```bash
conda --version
# 输出: conda 24.x.x 或更高版本
```

如果未安装，请安装 [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 或 [Anaconda](https://www.anaconda.com/products/distribution)。

### 2. 环境已存在

项目使用的 conda 环境 `dejavu` 已经存在，无需创建。

验证环境：
```bash
conda env list | grep dejavu
# 输出: dejavu    /path/to/conda/envs/dejavu
```

### 3. 激活环境

```bash
conda activate dejavu
```

### 4. 验证 Python 版本

```bash
python --version
# 输出: Python 3.12.10
```

## 安装依赖

### 方式 1: 使用安装脚本（推荐）

```bash
cd backend
./install.sh
```

脚本会：
- 检查 dejavu 环境是否存在
- 激活 dejavu 环境
- 安装所有依赖

### 方式 2: 手动安装

```bash
# 激活环境
conda activate dejavu

# 进入后端目录
cd backend

# 安装依赖（使用 pip）
pip install -r requirements.txt

# 或使用 conda 安装主要依赖
conda install -y fastapi uvicorn sqlalchemy psycopg2 redis-py pandas pyarrow websockets pydantic
pip install -r requirements.txt  # 安装剩余依赖
```

## 启动服务

### Backend API

```bash
cd backend
./start_backend.sh
```

脚本会自动：
1. 激活 dejavu 环境
2. 检查数据库连接
3. 启动 FastAPI 服务

### Worker

```bash
cd backend
./start_worker.sh
```

脚本会自动：
1. 激活 dejavu 环境
2. 检查数据库和 Docker 连接
3. 启动 RQ Worker

## 手动操作

如果不使用启动脚本，可以手动启动：

```bash
# 激活环境
conda activate dejavu

# 启动 Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 Worker (新终端)
conda activate dejavu
cd backend
python worker.py
```

## 常见问题

### Q1: conda activate dejavu 失败

**错误**: `CommandNotFoundError: Your shell has not been properly configured`

**解决方案**:
```bash
# 初始化 conda
conda init bash  # 或 zsh, 根据你的 shell

# 重新加载配置
source ~/.bashrc  # 或 ~/.zshrc

# 或在脚本中使用
eval "$(conda shell.bash hook)"
conda activate dejavu
```

### Q2: 环境中缺少某个包

```bash
conda activate dejavu

# 检查已安装的包
conda list

# 安装缺失的包
pip install <package-name>

# 或使用 conda
conda install <package-name>
```

### Q3: Python 版本不对

```bash
conda activate dejavu
python --version

# 如果版本不是 3.12.10，检查环境
conda info --envs
```

确保你激活的是正确的 dejavu 环境。

### Q4: 更新依赖

```bash
conda activate dejavu
cd backend

# 更新所有依赖到最新版本
pip install -r requirements.txt --upgrade

# 或重新安装
pip install -r requirements.txt --force-reinstall
```

## 环境管理

### 查看当前环境

```bash
conda env list
# * 标记表示当前激活的环境
```

### 退出环境

```bash
conda deactivate
```

### 导出环境（备份）

```bash
conda activate dejavu

# 导出完整环境
conda env export > environment.yml

# 仅导出通过 conda 安装的包
conda env export --from-history > environment.yml
```

### 在其他机器上复制环境（可选）

如果其他开发者需要相同的环境：

```bash
# 从 environment.yml 创建环境
conda env create -f environment.yml

# 或手动创建
conda create -n dejavu python=3.12
conda activate dejavu
pip install -r requirements.txt
```

## 与 venv 的区别

| 特性 | conda | venv |
|------|-------|------|
| 创建 | `conda create -n name` | `python -m venv venv` |
| 激活 | `conda activate name` | `source venv/bin/activate` |
| 安装包 | `conda install` 或 `pip install` | `pip install` |
| 管理 Python 版本 | ✅ 内置支持 | ❌ 使用系统 Python |
| 跨平台 | ✅ 更好 | ⚠️ 依赖系统 |

## 项目配置

项目的所有启动脚本都已适配 conda：
- ✅ `backend/install.sh`
- ✅ `backend/start_backend.sh`
- ✅ `backend/start_worker.sh`
- ✅ `quickstart.sh`

直接使用这些脚本即可，无需额外配置。

## 参考资料

- [Conda 官方文档](https://docs.conda.io/)
- [Conda Cheat Sheet](https://docs.conda.io/projects/conda/en/latest/user-guide/cheatsheet.html)
- [Managing Environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
