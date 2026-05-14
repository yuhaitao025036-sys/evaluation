#!/usr/bin/env python3
"""
代码完整性验证脚本

检查所有关键文件是否存在，以及基本的导入和语法是否正确
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description} 不存在: {file_path}")
        return False

def main():
    """主验证函数"""
    base_dir = Path(__file__).parent
    backend_dir = base_dir
    
    print("=" * 70)
    print("代码完整性验证")
    print("=" * 70)
    print()
    
    all_checks = []
    
    # 1. 核心配置文件
    print("【核心配置文件】")
    all_checks.append(check_file_exists(backend_dir / "app" / "config.py", "配置文件"))
    all_checks.append(check_file_exists(backend_dir / "app" / "database.py", "数据库连接"))
    all_checks.append(check_file_exists(backend_dir / "requirements.txt", "依赖文件"))
    all_checks.append(check_file_exists(backend_dir / "Dockerfile", "Dockerfile"))
    print()
    
    # 2. 数据库模型
    print("【数据库模型】")
    all_checks.append(check_file_exists(backend_dir / "app" / "models" / "__init__.py", "数据库模型"))
    all_checks.append(check_file_exists(backend_dir / "schema.sql", "SQL Schema"))
    all_checks.append(check_file_exists(backend_dir / "migrations" / "001_add_model_concurrency.sql", "Migration"))
    all_checks.append(check_file_exists(backend_dir / "init_db.py", "数据库初始化脚本"))
    print()
    
    # 3. Pydantic Schemas
    print("【Pydantic Schemas】")
    all_checks.append(check_file_exists(backend_dir / "app" / "schemas" / "__init__.py", "Schema 定义"))
    print()
    
    # 4. API 端点
    print("【API 端点】")
    api_dir = backend_dir / "app" / "api" / "v1"
    all_checks.append(check_file_exists(api_dir / "__init__.py", "API v1 初始化"))
    all_checks.append(check_file_exists(api_dir / "models.py", "Models API"))
    all_checks.append(check_file_exists(api_dir / "datasets.py", "Datasets API"))
    all_checks.append(check_file_exists(api_dir / "scripts.py", "Scripts API"))
    all_checks.append(check_file_exists(api_dir / "task_groups.py", "Task Groups API"))
    all_checks.append(check_file_exists(api_dir / "task_instances.py", "Task Instances API"))
    all_checks.append(check_file_exists(api_dir / "comparisons.py", "Comparisons API"))
    print()
    
    # 5. 服务层
    print("【服务层】")
    services_dir = backend_dir / "app" / "services"
    all_checks.append(check_file_exists(services_dir / "__init__.py", "Services 初始化"))
    all_checks.append(check_file_exists(services_dir / "dataset_service.py", "Dataset Service"))
    all_checks.append(check_file_exists(services_dir / "task_group_service.py", "Task Group Service"))
    print()
    
    # 6. Worker
    print("【后台任务执行】")
    all_checks.append(check_file_exists(backend_dir / "app" / "worker" / "__init__.py", "Worker 初始化"))
    all_checks.append(check_file_exists(backend_dir / "app" / "worker" / "task_executor.py", "Task Executor"))
    all_checks.append(check_file_exists(backend_dir / "worker.py", "RQ Worker 启动脚本"))
    print()
    
    # 7. 工具类
    print("【工具类】")
    utils_dir = backend_dir / "app" / "utils"
    all_checks.append(check_file_exists(utils_dir / "__init__.py", "Utils 初始化"))
    all_checks.append(check_file_exists(utils_dir / "script_validator.py", "Script Validator"))
    print()
    
    # 8. WebSocket
    print("【WebSocket】")
    ws_dir = backend_dir / "app" / "websocket"
    all_checks.append(check_file_exists(ws_dir / "__init__.py", "WebSocket 初始化"))
    all_checks.append(check_file_exists(ws_dir / "manager.py", "WebSocket Manager"))
    print()
    
    # 9. 主应用
    print("【主应用】")
    all_checks.append(check_file_exists(backend_dir / "app" / "main.py", "FastAPI 主应用"))
    print()
    
    # 10. Docker 和部署
    print("【Docker 和部署】")
    parent_dir = backend_dir.parent
    all_checks.append(check_file_exists(parent_dir / "docker-compose.yml", "Docker Compose"))
    all_checks.append(check_file_exists(parent_dir / "quickstart.sh", "快速启动脚本"))
    print()
    
    # 11. 文档
    print("【文档】")
    docs_dir = parent_dir / "docs"
    all_checks.append(check_file_exists(parent_dir / "README.md", "README"))
    all_checks.append(check_file_exists(docs_dir / "DEPLOYMENT.md", "部署文档"))
    all_checks.append(check_file_exists(docs_dir / "API_TESTING.md", "API 测试指南"))
    all_checks.append(check_file_exists(docs_dir / "BACKEND_SUMMARY.md", "后端实现总结"))
    print()
    
    # 统计
    print("=" * 70)
    total = len(all_checks)
    passed = sum(all_checks)
    failed = total - passed
    
    print(f"总计: {total} 个检查项")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print()
    
    if failed == 0:
        print("🎉 所有文件检查通过！代码结构完整。")
        print()
        print("下一步：")
        print("1. 安装依赖: pip install -r requirements.txt")
        print("2. 配置环境变量: cp .env.example .env")
        print("3. 启动 Docker: cd .. && docker-compose up -d")
        print("4. 初始化数据库: python init_db.py")
        print("5. 访问 API 文档: http://localhost:8000/docs")
        return 0
    else:
        print("⚠️  部分文件缺失，请检查！")
        return 1

if __name__ == "__main__":
    sys.exit(main())
