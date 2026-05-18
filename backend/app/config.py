"""Configuration management

配置管理说明:
- 此文件定义配置结构和默认值
- 真实配置(密码等)存储在 backend/.env 文件中
- .env 文件会覆盖此处的默认值
- 此文件可以提交到 Git (不包含敏感信息)
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "DUCC Evaluation System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    # 默认值为占位符,实际值从 .env 读取
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/ducc_evaluation"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # File paths (使用相对路径作为默认值)
    DATA_DIR: str = os.path.join(os.path.dirname(__file__), "../../data")
    DATASETS_DIR: str = os.path.join(os.path.dirname(__file__), "../../data/datasets")
    SCRIPTS_DIR: str = os.path.join(os.path.dirname(__file__), "../../data/scripts")
    OUTPUTS_DIR: str = os.path.join(os.path.dirname(__file__), "../../data/outputs")
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_HEARTBEAT_TIMEOUT: int = 60  # seconds
    WS_CLEANUP_INTERVAL: int = 10  # seconds
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# 支持的模型列表（硬编码配置）
AVAILABLE_MODELS = [
    {
        "id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "description": "OpenAI GPT-4 Turbo - 最强大的代码生成模型"
    },
    {
        "id": "claude-3.5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "description": "Anthropic Claude 3.5 - 优秀的推理和代码能力"
    },
    {
        "id": "gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "provider": "google",
        "description": "Google Gemini 1.5 Pro - 超长上下文支持"
    },
    {
        "id": "deepseek-v3",
        "name": "DeepSeek V3",
        "provider": "deepseek",
        "description": "DeepSeek V3 - 开源强大代码模型"
    },
    {
        "id": "qwen-max",
        "name": "Qwen Max",
        "provider": "alibaba",
        "description": "阿里通义千问 Max - 中文代码优化"
    },
    {
        "id": "minimax",
        "name": "MiniMax",
        "provider": "minimax",
        "description": "MiniMax - 高性价比选择"
    }
]

# 模型显示顺序
MODEL_DISPLAY_ORDER = [
    "gpt-4-turbo",
    "claude-3.5-sonnet", 
    "gemini-1.5-pro",
    "deepseek-v3",
    "qwen-max",
    "minimax"
]


def get_model_by_id(model_id: str):
    """根据模型ID获取模型信息"""
    for model in AVAILABLE_MODELS:
        if model["id"] == model_id:
            return model
    return None


def validate_model_id(model_id: str) -> bool:
    """验证模型ID是否有效"""
    return model_id in [m["id"] for m in AVAILABLE_MODELS]
