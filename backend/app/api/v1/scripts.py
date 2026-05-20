"""Scripts API endpoints"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from pathlib import Path
import os

from app.database import get_db
from app.models import Batch, Script, Task, TaskGroup
from app.schemas import Script as ScriptResponse
from app.config import settings
from app.utils.script_argument_parser import parse_script_arguments

router = APIRouter()


@router.get("", response_model=List[ScriptResponse])
def list_scripts(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List all available scripts"""
    scripts = db.query(Script).order_by(Script.file_name).all()
    existing_scripts = [script for script in scripts if os.path.exists(script.file_path)]
    return existing_scripts[offset:offset + limit]


@router.get("/{script_id}", response_model=ScriptResponse)
def get_script(
    script_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific script by ID"""
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    return script


@router.post("/scan")
def scan_scripts_folder(
    db: Session = Depends(get_db)
):
    """
    Scan the scripts folder for new Python scripts
    
    Registers new scripts found in the configured scripts directory
    """
    scripts_dir = Path(settings.SCRIPTS_DIR)
    
    if not scripts_dir.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Scripts directory not found: {settings.SCRIPTS_DIR}"
        )
    
    discovered_scripts = []
    registered_count = 0
    updated_count = 0
    deleted_count = 0
    discovered_file_names = set()

    # Find all Python scripts
    for script_file in scripts_dir.glob("*.py"):
        file_name = script_file.name
        file_path = str(script_file.absolute())
        discovered_file_names.add(file_name)
        argument_schema = parse_script_arguments(script_file)

        # Check if already registered
        existing = db.query(Script).filter(Script.file_name == file_name).first()

        if existing:
            # Update file path, arguments and scan time
            existing.file_path = file_path
            existing.argument_schema = argument_schema
            existing.last_scanned_at = func.now()
            updated_count += 1
            discovered_scripts.append({
                "id": existing.id,
                "file_name": file_name,
                "status": "updated",
                "argument_count": len(argument_schema)
            })
        else:
            # Register new script
            new_script = Script(
                file_name=file_name,
                file_path=file_path,
                description=f"Evaluation script: {file_name}",
                argument_schema=argument_schema
            )
            db.add(new_script)
            db.flush()
            registered_count += 1
            discovered_scripts.append({
                "id": new_script.id,
                "file_name": file_name,
                "status": "registered",
                "argument_count": len(argument_schema)
            })

    stale_scripts = db.query(Script).all()
    for script in stale_scripts:
        script_path = Path(script.file_path)
        if script.file_name not in discovered_file_names or not script_path.exists():
            is_referenced = any([
                db.query(Batch.id).filter(Batch.script_id == script.id).first(),
                db.query(TaskGroup.id).filter(TaskGroup.script_id == script.id).first(),
                db.query(Task.id).filter(Task.script_id == script.id).first(),
            ])
            if is_referenced:
                continue
            db.delete(script)
            deleted_count += 1

    db.commit()

    return {
        "message": f"Scan completed: {registered_count} new, {updated_count} updated, {deleted_count} deleted",
        "registered_count": registered_count,
        "updated_count": updated_count,
        "deleted_count": deleted_count,
        "scripts": discovered_scripts
    }


@router.get("/{script_id}/exists")
def check_script_exists(
    script_id: int,
    db: Session = Depends(get_db)
):
    """Check if a script file still exists on disk"""
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    exists = os.path.exists(script.file_path)
    
    return {
        "script_id": script_id,
        "file_name": script.file_name,
        "file_path": script.file_path,
        "exists": exists
    }
