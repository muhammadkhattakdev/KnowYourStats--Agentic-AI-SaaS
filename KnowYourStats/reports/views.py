from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from .models import Report, ReportVisualization
from .serializers import (
    ReportSerializer,
    ReportDetailSerializer,
    CreateReportSerializer,
    ReportVisualizationSerializer
)
from data_manager.models import Dataset


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for reports"""
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ReportDetailSerializer
        elif self.action == 'create':
            return CreateReportSerializer
        return ReportSerializer
    
    def get_queryset(self):
        """Get reports for current user"""
        return Report.objects.filter(
            user=self.request.user
        ).select_related('dataset', 'chat_session')
    
    def create(self, request, *args, **kwargs):
        """Create new report"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create dataset snapshot if dataset provided
        dataset_id = serializer.validated_data.get('dataset')
        dataset_snapshot = {}
        
        if dataset_id:
            try:
                dataset = Dataset.objects.get(id=dataset_id.id, user=request.user)
                dataset_snapshot = {
                    'filename': dataset.original_filename,
                    'columns': dataset.columns,
                    'row_count': dataset.row_count,
                    'column_count': dataset.column_count,
                    'created_at': dataset.created_at.isoformat()
                }
            except Dataset.DoesNotExist:
                pass
        
        report = Report.objects.create(
            user=request.user,
            dataset_snapshot=dataset_snapshot,
            **serializer.validated_data
        )
        
        return Response({
            'success': True,
            'message': 'Report created successfully',
            'data': ReportSerializer(report).data
        }, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """Get report details"""
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
        """List all reports"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by analysis type
        analysis_type = request.query_params.get('analysis_type')
        if analysis_type:
            queryset = queryset.filter(analysis_type=analysis_type)
        
        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(query__icontains=search)
            )
        
        # Order by
        order_by = request.query_params.get('order_by', '-created_at')
        queryset = queryset.order_by(order_by)
        
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
        """Update report"""
        instance = self.get_object()
        
        # Check ownership
        if instance.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Only allow updating certain fields
        allowed_fields = ['title', 'metadata']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(instance, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Report updated',
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete report"""
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
            'message': 'Report deleted'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get report statistics"""
        user_reports = self.get_queryset()
        
        stats = {
            'total_reports': user_reports.count(),
            'completed_reports': user_reports.filter(status='completed').count(),
            'failed_reports': user_reports.filter(status='failed').count(),
            'by_analysis_type': {},
            'recent_reports': []
        }
        
        # Count by analysis type
        analysis_types = user_reports.values('analysis_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for item in analysis_types:
            if item['analysis_type']:
                stats['by_analysis_type'][item['analysis_type']] = item['count']
        
        # Get 5 most recent reports
        recent = user_reports.order_by('-created_at')[:5]
        stats['recent_reports'] = ReportSerializer(recent, many=True).data
        
        return Response({
            'success': True,
            'data': stats
        })
    
    @action(detail=True, methods=['post'])
    def add_visualization(self, request, pk=None):
        """Add visualization to report"""
        report = self.get_object()
        
        if report.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ReportVisualizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        visualization = ReportVisualization.objects.create(
            report=report,
            **serializer.validated_data
        )
        
        return Response({
            'success': True,
            'message': 'Visualization added',
            'data': ReportVisualizationSerializer(visualization).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export report (could be PDF, DOCX, etc.)"""
        report = self.get_object()
        
        if report.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # For now, just return the report data
        # In production, you'd generate PDF/DOCX
        
        export_data = {
            'title': report.title,
            'query': report.query,
            'report_content': report.report_content,
            'dataset_info': report.dataset_snapshot,
            'created_at': report.created_at.isoformat(),
            'analysis_type': report.analysis_type
        }
        
        return Response({
            'success': True,
            'data': export_data
        })