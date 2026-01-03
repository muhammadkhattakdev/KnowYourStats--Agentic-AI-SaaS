from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from .models import Dataset, DatasetChunk
from .serializers import (
    DatasetSerializer,
    DatasetUploadSerializer,
    DatasetChunkSerializer
)
from .tasks import process_dataset
import pandas as pd
import os


class DatasetViewSet(viewsets.ModelViewSet):
    """ViewSet for datasets"""
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DatasetUploadSerializer
        return DatasetSerializer
    
    def get_queryset(self):
        """Get datasets for current user"""
        return Dataset.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Upload and create new dataset"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data['file']
        description = serializer.validated_data.get('description', '')
        
        # Get file info
        extension = file.name.split('.')[-1].lower()
        file_type_map = {
            'csv': 'csv',
            'xlsx': 'xlsx',
            'xls': 'xls'
        }
        
        # Create dataset
        dataset = Dataset.objects.create(
            user=request.user,
            file=file,
            original_filename=file.name,
            file_type=file_type_map.get(extension, 'csv'),
            file_size=file.size,
            description=description,
            status='processing'
        )
        
        # Trigger async processing
        process_dataset.delay(str(dataset.id))
        
        return Response({
            'success': True,
            'message': 'Dataset uploaded successfully. Processing started.',
            'data': DatasetSerializer(dataset).data
        }, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """Get dataset details"""
        instance = self.get_object()
        
        # Check ownership
        if instance.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def list(self, request, *args, **kwargs):
        """List all datasets"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        """Update dataset metadata"""
        instance = self.get_object()
        
        # Check ownership
        if instance.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Only allow updating description and metadata
        allowed_fields = ['description', 'metadata']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(instance, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Dataset updated',
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete dataset"""
        instance = self.get_object()
        
        # Check ownership
        if instance.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        instance.delete()
        
        return Response({
            'success': True,
            'message': 'Dataset deleted'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get dataset preview (first 100 rows)"""
        dataset = self.get_object()
        
        if dataset.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if dataset.status != 'ready':
            return Response({
                'success': False,
                'message': f'Dataset is not ready. Status: {dataset.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Load preview data
            if dataset.file_type == 'csv':
                df = pd.read_csv(dataset.file.path, nrows=100)
            else:
                df = pd.read_excel(dataset.file.path, nrows=100)
            
            preview_data = {
                'columns': list(df.columns),
                'data': df.to_dict('records'),
                'total_rows': dataset.row_count,
                'preview_rows': len(df)
            }
            
            return Response({
                'success': True,
                'data': preview_data
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Failed to load preview: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get dataset statistics"""
        dataset = self.get_object()
        
        if dataset.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if dataset.status != 'ready':
            return Response({
                'success': False,
                'message': f'Dataset is not ready. Status: {dataset.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Load data
            if dataset.file_type == 'csv':
                df = pd.read_csv(dataset.file.path)
            else:
                df = pd.read_excel(dataset.file.path)
            
            # Calculate statistics
            stats = {
                'basic': {
                    'row_count': len(df),
                    'column_count': len(df.columns),
                    'memory_usage': df.memory_usage(deep=True).sum()
                },
                'columns': {},
                'missing_values': df.isnull().sum().to_dict()
            }
            
            # Per-column statistics
            for col in df.columns:
                col_stats = {
                    'dtype': str(df[col].dtype),
                    'non_null_count': int(df[col].count()),
                    'null_count': int(df[col].isnull().sum()),
                    'unique_count': int(df[col].nunique())
                }
                
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_stats.update({
                        'mean': float(df[col].mean()),
                        'median': float(df[col].median()),
                        'std': float(df[col].std()),
                        'min': float(df[col].min()),
                        'max': float(df[col].max())
                    })
                
                stats['columns'][col] = col_stats
            
            return Response({
                'success': True,
                'data': stats
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Failed to calculate statistics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess dataset"""
        dataset = self.get_object()
        
        if dataset.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        dataset.status = 'processing'
        dataset.error_message = ''
        dataset.save()
        
        # Trigger reprocessing
        process_dataset.delay(str(dataset.id))
        
        return Response({
            'success': True,
            'message': 'Dataset reprocessing started'
        })