"""Dataset service - handles dataset scanning, importing, and filtering"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from app.models import Dataset, DatasetInstance
from app.config import settings
import json


class DatasetService:
    """Service for managing datasets"""
    
    @staticmethod
    def scan_datasets_folder(db: Session) -> List[Dataset]:
        """
        Scan datasets folder and register new datasets
        
        Returns:
            List of newly registered datasets
        """
        datasets_dir = Path(settings.DATASETS_DIR)
        if not datasets_dir.exists():
            raise FileNotFoundError(f"Datasets directory not found: {datasets_dir}")
        
        newly_registered = []
        
        # Scan for supported file formats
        for file_path in datasets_dir.glob("*"):
            if file_path.suffix not in ['.parquet', '.csv', '.json', '.jsonl']:
                continue
            
            # Check if already registered
            existing = db.query(Dataset).filter(
                Dataset.file_path == str(file_path)
            ).first()
            
            if existing:
                continue
            
            # Get file info
            file_size = file_path.stat().st_size
            file_format = file_path.suffix[1:]  # Remove dot
            
            # Quick count instances
            total_instances = DatasetService._count_instances(file_path, file_format)
            
            # Register dataset
            dataset = Dataset(
                name=file_path.stem,
                file_name=file_path.name,
                file_path=str(file_path),
                format=file_format,
                file_size=file_size,
                total_instances=total_instances,
                imported_instances=0
            )
            
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            
            newly_registered.append(dataset)
        
        return newly_registered
    
    @staticmethod
    def _count_instances(file_path: Path, file_format: str) -> int:
        """Count instances in dataset file"""
        try:
            if file_format == 'parquet':
                import pyarrow.parquet as pq
                parquet_file = pq.ParquetFile(str(file_path))
                return parquet_file.metadata.num_rows
            elif file_format == 'csv':
                return sum(1 for _ in open(file_path)) - 1  # Subtract header
            elif file_format in ['json', 'jsonl']:
                return sum(1 for _ in open(file_path))
            else:
                return 0
        except Exception as e:
            print(f"Error counting instances in {file_path}: {e}")
            return 0
    
    @staticmethod
    def import_dataset_instances(
        db: Session,
        dataset_id: int,
        start_index: int = 0,
        end_index: Optional[int] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Import dataset instances to database
        
        Args:
            dataset_id: Dataset ID
            start_index: Start index
            end_index: End index (None = all)
            filter_conditions: Filter conditions (e.g., {"repo_language": "python"})
        
        Returns:
            Number of imported instances
        """
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        file_path = Path(dataset.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        
        # Load dataset
        if dataset.format == 'parquet':
            df = pd.read_parquet(file_path)
        elif dataset.format == 'csv':
            df = pd.read_csv(file_path)
        elif dataset.format in ['json', 'jsonl']:
            df = pd.read_json(file_path, lines=(dataset.format == 'jsonl'))
        else:
            raise ValueError(f"Unsupported format: {dataset.format}")
        
        # Apply filters
        if filter_conditions:
            df = DatasetService._apply_filters(df, filter_conditions)
        
        # Apply index range
        if end_index is not None:
            df = df.iloc[start_index:end_index]
        else:
            df = df.iloc[start_index:]
        
        # Import instances
        imported_count = 0
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            
            # Extract key fields
            instance_id = row_dict.get('instance_id', f"instance_{idx}")
            repo_language = row_dict.get('repo_language', row_dict.get('language'))
            
            # Check if already exists
            existing = db.query(DatasetInstance).filter(
                and_(
                    DatasetInstance.dataset_id == dataset_id,
                    DatasetInstance.instance_id == instance_id
                )
            ).first()
            
            if existing:
                continue
            
            # Create instance
            instance = DatasetInstance(
                dataset_id=dataset_id,
                instance_id=instance_id,
                repo_language=repo_language,
                data=row_dict  # Store complete data as JSONB
            )
            
            db.add(instance)
            imported_count += 1
        
        # Update dataset imported count
        dataset.imported_instances = db.query(DatasetInstance).filter(
            DatasetInstance.dataset_id == dataset_id
        ).count()
        
        db.commit()
        
        return imported_count
    
    @staticmethod
    def _apply_filters(df: pd.DataFrame, filter_conditions: Dict[str, Any]) -> pd.DataFrame:
        """Apply filter conditions to dataframe"""
        filtered_df = df.copy()
        
        # Language filter
        if 'repo_language' in filter_conditions:
            lang = filter_conditions['repo_language']
            if 'repo_language' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['repo_language'] == lang]
            elif 'language' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['language'] == lang]
        
        # Instance ID pattern filter
        if 'instance_id_pattern' in filter_conditions:
            pattern = filter_conditions['instance_id_pattern']
            if 'instance_id' in filtered_df.columns:
                # Simple wildcard support: django* -> django.*
                import re
                regex_pattern = pattern.replace('*', '.*')
                filtered_df = filtered_df[
                    filtered_df['instance_id'].str.match(regex_pattern)
                ]
        
        # Index range filter
        if 'index_range' in filter_conditions:
            start, end = filter_conditions['index_range']
            filtered_df = filtered_df.iloc[start:end]
        
        # JSONB field filters
        if 'jsonb_filters' in filter_conditions:
            for field, value in filter_conditions['jsonb_filters'].items():
                if field in filtered_df.columns:
                    if isinstance(value, list):
                        filtered_df = filtered_df[filtered_df[field].isin(value)]
                    else:
                        filtered_df = filtered_df[filtered_df[field] == value]
        
        return filtered_df
    
    @staticmethod
    def get_filtered_instance_ids(
        db: Session,
        dataset_id: int,
        filter_conditions: Optional[Dict[str, Any]] = None,
        start_index: int = 0,
        end_index: Optional[int] = None
    ) -> List[str]:
        """
        Get list of instance IDs matching filter conditions
        
        Returns:
            List of instance_id strings
        """
        query = db.query(DatasetInstance.instance_id).filter(
            DatasetInstance.dataset_id == dataset_id
        )
        
        # Apply filters
        if filter_conditions:
            if 'repo_language' in filter_conditions:
                query = query.filter(
                    DatasetInstance.repo_language == filter_conditions['repo_language']
                )
            
            # JSONB filters
            if 'jsonb_filters' in filter_conditions:
                for field, value in filter_conditions['jsonb_filters'].items():
                    if isinstance(value, list):
                        query = query.filter(
                            DatasetInstance.data[field].astext.in_(value)
                        )
                    else:
                        query = query.filter(
                            DatasetInstance.data[field].astext == str(value)
                        )
        
        # Apply offset and limit
        query = query.offset(start_index)
        if end_index is not None:
            query = query.limit(end_index - start_index)
        
        results = query.all()
        return [r[0] for r in results]
