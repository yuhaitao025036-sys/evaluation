"""RQ Worker for executing task instances

Architecture Note:
- Worker runs on host machine (not in Docker)
- Worker executes evaluation scripts directly on host
- Evaluation scripts (e.g., test_tmux_cc_experience.py) internally call Docker
- This avoids Docker-in-Docker complexity
"""
import os
import sys
import json
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import TaskInstance, Task, DatasetInstance, TaskLog, Script
from app.config import settings
from app.utils.script_validator import ScriptValidator


def execute_task_instance(task_instance_id: int):
    """
    Execute a single task instance on the host machine
    
    This function is called by RQ workers to process task instances.
    
    Execution Flow:
    1. Load instance data from database
    2. Prepare working directory on host
    3. Execute evaluation script on host (script will use Docker internally)
    4. Collect results and update database
    
    The evaluation script is responsible for:
    - Starting Docker containers for the test environment
    - Running the actual evaluation
    - Generating results and patches
    """
    db = SessionLocal()
    task = None
    instance = None
    
    try:
        # Load task instance
        instance = db.query(TaskInstance).filter(
            TaskInstance.id == task_instance_id
        ).first()
        
        if not instance:
            raise Exception(f"Task instance {task_instance_id} not found")
        
        # Update status to running
        instance.status = 'running'
        instance.started_at = datetime.now()
        db.commit()
        
        # Load related task and dataset data
        task = db.query(Task).filter(Task.id == instance.task_id).first()
        if not task:
            raise Exception(f"Task {instance.task_id} not found")
        
        # Load script
        script = db.query(Script).filter(Script.id == task.script_id).first()
        if not script:
            raise Exception(f"Script {task.script_id} not found")
        
        dataset_instance = db.query(DatasetInstance).filter(
            DatasetInstance.instance_id == instance.instance_id
        ).first()
        
        if not dataset_instance:
            raise Exception(f"Dataset instance {instance.instance_id} not found")
        
        # Prepare working directory on host machine
        work_dir = Path(settings.WORK_DIR) / f"task_{task.id}" / f"instance_{instance.id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        instance.task_dir = str(work_dir)
        
        # Write instance data to JSON file
        instance_data_file = work_dir / "instance_data.json"
        with open(instance_data_file, 'w') as f:
            json.dump(dataset_instance.data, f, indent=2)
        
        log_message(db, task.id, 'INFO', 
                   f"Prepared working directory: {work_dir}")
        
        # Build command to execute script on host
        # Script path should be absolute
        script_path = Path(script.file_path)
        if not script_path.is_absolute():
            script_path = Path(settings.SCRIPTS_DIR) / script.file_name
        
        if not script_path.exists():
            raise Exception(f"Script not found: {script_path}")
        
        # Build base command
        base_cmd = [
            sys.executable,  # Python interpreter on host
            str(script_path),
            str(instance_data_file),  # Input data file
            str(work_dir)  # Output directory
        ]
        
        # Add additional script arguments if provided
        if task.script_args:
            validator = ScriptValidator()
            extra_args = validator.validate_and_parse_args(task.script_args)
            base_cmd.extend(extra_args)
        
        # Add model information if available
        if instance.model:
            base_cmd.extend(['--model', instance.model])
        
        if instance.model_params:
            model_params_file = work_dir / "model_params.json"
            with open(model_params_file, 'w') as f:
                json.dump(instance.model_params, f)
            base_cmd.extend(['--model-params', str(model_params_file)])
        
        # Log command
        log_message(db, task.id, 'INFO', 
                   f"Executing on host: {' '.join(base_cmd)}")
        
        # Execute script on host machine
        # The script will internally use Docker for the actual evaluation
        result = subprocess.run(
            base_cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=settings.TASK_TIMEOUT_SECONDS,
            env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # Ensure output is not buffered
        )
        
        # Save stdout/stderr
        stdout_file = work_dir / "stdout.log"
        stderr_file = work_dir / "stderr.log"
        stdout_file.write_text(result.stdout)
        stderr_file.write_text(result.stderr)
        
        log_message(db, task.id, 'INFO',
                   f"Script execution completed with return code: {result.returncode}")
        
        # Check for results file
        results_file = work_dir / "results.json"
        if results_file.exists():
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            # Update instance with results
            instance.summary = results.get('summary', {})
            instance.validation_success = results.get('validation_success', False)
            instance.test_passed = results.get('test_passed', 0)
            instance.test_failed = results.get('test_failed', 0)
            instance.test_errors = results.get('test_errors', 0)
            
            # Load generated patch if available
            patch_file = work_dir / "generated.patch"
            if patch_file.exists():
                instance.generated_patch = patch_file.read_text()
                log_message(db, task.id, 'INFO',
                           f"Generated patch loaded: {len(instance.generated_patch)} bytes")
        else:
            log_message(db, task.id, 'WARNING',
                       f"Results file not found: {results_file}")
            
            # Try to extract useful info from stderr
            instance.summary = {
                'error': 'Results file not generated',
                'return_code': result.returncode,
                'stderr_tail': result.stderr[-1000:] if result.stderr else '',
                'stdout_tail': result.stdout[-1000:] if result.stdout else ''
            }
        
        # Update completion status
        instance.completed_at = datetime.now()
        instance.duration_seconds = (
            instance.completed_at - instance.started_at
        ).total_seconds()
        
        # Determine final status
        if result.returncode == 0 and results_file.exists():
            instance.status = 'completed'
            log_message(db, task.id, 'INFO',
                       f"Instance {instance.instance_id} completed successfully in {instance.duration_seconds:.2f}s")
        else:
            instance.status = 'failed'
            log_message(db, task.id, 'ERROR',
                       f"Instance {instance.instance_id} failed with return code {result.returncode}")
        
        db.commit()
        
        # Update parent task statistics
        update_task_statistics(db, task.id)
        
        return {
            'task_instance_id': task_instance_id,
            'status': instance.status,
            'duration_seconds': instance.duration_seconds
        }
    
    except subprocess.TimeoutExpired:
        if instance:
            instance.status = 'failed'
            instance.completed_at = datetime.now()
            instance.summary = {
                'error': 'Execution timeout',
                'timeout_seconds': settings.TASK_TIMEOUT_SECONDS
            }
            db.commit()
        
        if task:
            log_message(db, task.id, 'ERROR',
                       f"Instance {task_instance_id} timed out after {settings.TASK_TIMEOUT_SECONDS}s")
        raise
    
    except Exception as e:
        # Handle execution errors
        if instance:
            instance.status = 'failed'
            instance.completed_at = datetime.now()
            instance.summary = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            db.commit()
            
            if task:
                log_message(db, task.id, 'ERROR',
                           f"Instance {task_instance_id} error: {str(e)}")
        raise
    
    finally:
        db.close()


def update_task_statistics(db: Session, task_id: int):
    """Update task-level statistics based on task instances"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return
    
    # Count instance statuses
    instances = db.query(TaskInstance).filter(
        TaskInstance.task_id == task_id
    ).all()
    
    task.total_instances = len(instances)
    task.completed_instances = sum(
        1 for i in instances if i.status == 'completed'
    )
    task.failed_instances = sum(
        1 for i in instances if i.status == 'failed'
    )
    
    # Update task status
    if task.completed_instances + task.failed_instances == task.total_instances:
        if task.total_instances > 0:
            task.status = 'completed'
            task.completed_at = datetime.now()
    elif task.completed_instances > 0 or task.failed_instances > 0:
        task.status = 'running'
    
    db.commit()
    
    # Update task group statistics if task belongs to a group
    if task.group_id:
        update_task_group_statistics(db, task.group_id)


def update_task_group_statistics(db: Session, group_id: int):
    """Update task group statistics based on tasks"""
    from app.models import TaskGroup
    
    group = db.query(TaskGroup).filter(TaskGroup.id == group_id).first()
    if not group:
        return
    
    # Sum up all task instances across all tasks in the group
    tasks = db.query(Task).filter(Task.group_id == group_id).all()
    
    total_completed = 0
    total_failed = 0
    all_tasks_done = True
    
    for task in tasks:
        total_completed += task.completed_instances
        total_failed += task.failed_instances
        
        if task.status not in ['completed', 'failed']:
            all_tasks_done = False
    
    group.completed_instances = total_completed
    group.failed_instances = total_failed
    
    if all_tasks_done and len(tasks) > 0:
        group.status = 'completed'
        group.completed_at = datetime.now()
    elif total_completed > 0 or total_failed > 0:
        group.status = 'running'
    
    db.commit()


def log_message(db: Session, task_id: int, level: str, message: str):
    """Add a log message to the task"""
    log = TaskLog(
        task_id=task_id,
        level=level,
        message=message
    )
    db.add(log)
    db.commit()
