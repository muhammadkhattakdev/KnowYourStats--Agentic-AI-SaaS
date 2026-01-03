from django.db import models
from django.conf import settings
import uuid
import os


def dataset_upload_path(instance, filename):
    """Generate upload path for dataset files"""
    return f'datasets/{instance.user.id}/{uuid.uuid4()}/{filename}'


class Dataset(models.Model):
    """Dataset model for uploaded data"""
    
    FILE_TYPE_CHOICES = [
        ('csv', 'CSV'),
        ('xlsx', 'Excel (XLSX)'),
        ('xls', 'Excel (XLS)'),
    ]
    
    STATUS_CHOICES = [
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='datasets'
    )
    
    # File information
    file = models.FileField(upload_to=dataset_upload_path)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    file_size = models.BigIntegerField()  # in bytes
    
    # Data information
    row_count = models.IntegerField(null=True, blank=True)
    column_count = models.IntegerField(null=True, blank=True)
    columns = models.JSONField(default=list, blank=True)  # List of column names
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploading')
    error_message = models.TextField(blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Vector storage
    has_embeddings = models.BooleanField(default=False)
    faiss_index_path = models.CharField(max_length=500, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dataset'
        verbose_name_plural = 'Datasets'
    
    def __str__(self):
        return f"{self.original_filename} - {self.user.email}"
    
    def get_file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.original_filename)[1].lower()
    
    def delete(self, *args, **kwargs):
        """Delete file when dataset is deleted"""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        
        # Delete FAISS index if exists
        if self.faiss_index_path and os.path.exists(self.faiss_index_path):
            os.remove(self.faiss_index_path)
        
        super().delete(*args, **kwargs)


class DatasetChunk(models.Model):
    """Chunked data for vector embeddings"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    
    # Chunk data
    content = models.TextField()
    chunk_index = models.IntegerField()
    
    # Embedding
    embedding = models.JSONField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['dataset', 'chunk_index']
        unique_together = ['dataset', 'chunk_index']
        verbose_name = 'Dataset Chunk'
        verbose_name_plural = 'Dataset Chunks'
    
    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.dataset.original_filename}"