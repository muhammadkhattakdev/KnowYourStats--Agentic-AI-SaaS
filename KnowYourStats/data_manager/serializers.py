from rest_framework import serializers
from .models import Dataset, DatasetChunk


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for datasets"""
    
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = Dataset
        fields = [
            'id', 'original_filename', 'file_type', 'file_size',
            'file_size_mb', 'row_count', 'column_count', 'columns',
            'status', 'error_message', 'description', 'metadata',
            'has_embeddings', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'file_size_mb',
            'row_count', 'column_count', 'columns', 'status',
            'error_message', 'has_embeddings', 'created_at', 'updated_at'
        ]
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        return round(obj.file_size / (1024 * 1024), 2) if obj.file_size else 0


class DatasetUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading datasets"""
    
    class Meta:
        model = Dataset
        fields = ['file', 'description']
        extra_kwargs = {
            'description': {'required': False}
        }
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file extension
        extension = value.name.split('.')[-1].lower()
        allowed_extensions = ['csv', 'xlsx', 'xls']
        
        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                f'File type .{extension} not supported. Allowed: {", ".join(allowed_extensions)}'
            )
        
        # Check file size (50MB max)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f'File size exceeds 50MB limit. Your file: {round(value.size / (1024 * 1024), 2)}MB'
            )
        
        return value


class DatasetChunkSerializer(serializers.ModelSerializer):
    """Serializer for dataset chunks"""
    
    class Meta:
        model = DatasetChunk
        fields = ['id', 'chunk_index', 'content', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']