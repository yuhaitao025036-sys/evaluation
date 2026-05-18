"""Models API - list available models"""
from fastapi import APIRouter
from typing import List
from app.config import AVAILABLE_MODELS, get_model_by_id
from app.schemas import ModelInfo

router = APIRouter()


@router.get("", response_model=List[ModelInfo])
async def list_models():
    """
    List all available models

    Models are configured in app/config.py and hardcoded for simplicity.
    """
    return AVAILABLE_MODELS


@router.get("/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """Get model information by ID"""
    model = get_model_by_id(model_id)
    if not model:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model
