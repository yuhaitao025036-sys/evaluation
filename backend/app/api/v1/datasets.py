"""Datasets API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import Dataset, DatasetCreate
from app.services.dataset_service import DatasetService
from app import models

router = APIRouter()


@router.get("/datasets", response_model=List[Dataset])
async def list_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all datasets"""
    datasets = db.query(models.Dataset).offset(skip).limit(limit).all()
    return datasets


@router.get("/datasets/{dataset_id}", response_model=Dataset)
async def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Get dataset by ID"""
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/datasets/scan")
async def scan_datasets(db: Session = Depends(get_db)):
    """
    Scan datasets folder and register new datasets
    
    This will scan the configured datasets directory and register
    any new .parquet, .csv, .json, or .jsonl files.
    """
    try:
        newly_registered = DatasetService.scan_datasets_folder(db)
        return {
            "message": f"Scanned datasets folder",
            "newly_registered": len(newly_registered),
            "datasets": [
                {
                    "id": d.id,
                    "name": d.name,
                    "file_name": d.file_name,
                    "total_instances": d.total_instances
                }
                for d in newly_registered
            ]
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning datasets: {str(e)}")


@router.post("/datasets/{dataset_id}/import")
async def import_dataset(
    dataset_id: int,
    start_index: int = 0,
    end_index: int = None,
    db: Session = Depends(get_db)
):
    """
    Import dataset instances to database
    
    This will load instances from the dataset file and store them in the database.
    Use start_index and end_index to import specific ranges.
    """
    try:
        imported_count = DatasetService.import_dataset_instances(
            db=db,
            dataset_id=dataset_id,
            start_index=start_index,
            end_index=end_index
        )
        
        return {
            "message": f"Imported {imported_count} instances",
            "dataset_id": dataset_id,
            "imported_count": imported_count
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing dataset: {str(e)}")


@router.get("/datasets/{dataset_id}/instances")
async def get_dataset_instances(
    dataset_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get instances from a dataset"""
    instances = db.query(models.DatasetInstance).filter(
        models.DatasetInstance.dataset_id == dataset_id
    ).offset(skip).limit(limit).all()
    
    return {
        "dataset_id": dataset_id,
        "instances": [
            {
                "id": inst.id,
                "instance_id": inst.instance_id,
                "repo_language": inst.repo_language,
                "data": inst.data
            }
            for inst in instances
        ]
    }
