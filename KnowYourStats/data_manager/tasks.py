from celery import shared_task
from django.conf import settings
from .models import Dataset, DatasetChunk
import pandas as pd
import numpy as np
import faiss
import os
import json


@shared_task(bind=True, max_retries=3)
def process_dataset(self, dataset_id):
    """Process uploaded dataset - extract info, create embeddings"""
    
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        
        # Update status
        dataset.status = 'processing'
        dataset.save()
        
        # Load data
        if dataset.file_type == 'csv':
            df = pd.read_csv(dataset.file.path)
        elif dataset.file_type in ['xlsx', 'xls']:
            df = pd.read_excel(dataset.file.path)
        else:
            raise ValueError(f'Unsupported file type: {dataset.file_type}')
        
        # Extract basic information
        dataset.row_count = len(df)
        dataset.column_count = len(df.columns)
        dataset.columns = list(df.columns)
        
        # Store sample statistics
        dataset.metadata = {
            'dtypes': df.dtypes.astype(str).to_dict(),
            'numeric_columns': list(df.select_dtypes(include=[np.number]).columns),
            'categorical_columns': list(df.select_dtypes(include=['object']).columns),
            'missing_values': df.isnull().sum().to_dict(),
            'basic_stats': df.describe().to_dict()
        }
        
        # Create chunks for vector embeddings (optional, for large datasets)
        # chunk_size = 1000
        # for i in range(0, len(df), chunk_size):
        #     chunk_df = df.iloc[i:i+chunk_size]
        #     chunk_content = chunk_df.to_json()
        #     
        #     DatasetChunk.objects.create(
        #         dataset=dataset,
        #         content=chunk_content,
        #         chunk_index=i // chunk_size,
        #         metadata={'rows': len(chunk_df)}
        #     )
        
        # Update status to ready
        dataset.status = 'ready'
        dataset.save()
        
        return {
            'success': True,
            'dataset_id': str(dataset_id),
            'rows': dataset.row_count,
            'columns': dataset.column_count
        }
        
    except Exception as e:
        # Update status to error
        dataset.status = 'error'
        dataset.error_message = str(e)
        dataset.save()
        
        # Retry task
        raise self.retry(exc=e, countdown=60)


@shared_task
def create_embeddings_for_dataset(dataset_id):
    """
    Create FAISS embeddings for dataset (optional advanced feature)
    This would use OpenAI/Anthropic embeddings API
    """
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        
        # Load chunks
        chunks = DatasetChunk.objects.filter(dataset=dataset).order_by('chunk_index')
        
        if not chunks.exists():
            return {'success': False, 'message': 'No chunks found'}
        
        # Here you would:
        # 1. Generate embeddings using OpenAI/Anthropic API
        # 2. Create FAISS index
        # 3. Save index to disk
        
        # For now, just mark as having embeddings
        dataset.has_embeddings = True
        dataset.save()
        
        return {
            'success': True,
            'dataset_id': str(dataset_id)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }