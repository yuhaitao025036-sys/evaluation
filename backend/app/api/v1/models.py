"""Models API - list available models"""
import json
import os
from fastapi import APIRouter
from typing import Any, Dict, List
from app.config import AVAILABLE_MODELS, get_model_by_id, settings
from app.schemas import ModelInfo

router = APIRouter()


def _provider_config_path() -> str:
    return os.getenv(
        'DUCC_MODEL_PROVIDERS_CONFIG',
        os.path.join(settings.DATA_DIR, 'config', 'model_providers.json'),
    )


def _load_provider_configs() -> Dict[str, Any]:
    path = _provider_config_path()
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _public_provider_config(name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    models = config.get('models') or []
    default_model = config.get('model') or (models[0] if models else None)
    return {
        'provider': name,
        'base_url': config.get('base_url'),
        'model': default_model,
        'models': models,
        'configured': name == 'comate' or bool(config.get('api_key')),
    }


@router.get("", response_model=List[ModelInfo])
async def list_models():
    """
    List all available models

    Models are configured in app/config.py and hardcoded for simplicity.
    """
    return AVAILABLE_MODELS


@router.get("/providers")
async def list_model_providers():
    configs = _load_provider_configs()
    providers = []
    for name in ('comate', 'xinghe', 'qianfan'):
        providers.append(_public_provider_config(name, configs.get(name, {})))
    return providers


@router.get("/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """Get model information by ID"""
    model = get_model_by_id(model_id)
    if not model:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model
