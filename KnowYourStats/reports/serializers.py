from rest_framework import serializers
from .models import Report, ReportVisualization
from data_manager.serializers import DatasetSerializer


class ReportVisualizationSerializer(serializers.ModelSerializer):
    """Serializer for report visualizations"""
    
    class Meta:
        model = ReportVisualization
        fields = [
            'id', 'chart_type', 'title', 'data',
            'config', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for reports"""
    
    dataset_info = DatasetSerializer(source='dataset', read_only=True)
    visualization_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'title', 'query', 'report_content',
            'dataset', 'dataset_info', 'dataset_snapshot',
            'metadata', 'analysis_type', 'status',
            'error_message', 'visualization_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'error_message',
            'created_at', 'updated_at'
        ]
    
    def get_visualization_count(self, obj):
        """Get count of visualizations"""
        return obj.visualizations.count()


class ReportDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for reports with visualizations"""
    
    dataset_info = DatasetSerializer(source='dataset', read_only=True)
    visualizations = ReportVisualizationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'title', 'query', 'report_content',
            'dataset', 'dataset_info', 'dataset_snapshot',
            'metadata', 'analysis_type', 'status',
            'error_message', 'reasoning_trace',
            'visualizations', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'error_message',
            'created_at', 'updated_at'
        ]


class CreateReportSerializer(serializers.ModelSerializer):
    """Serializer for creating reports"""
    
    class Meta:
        model = Report
        fields = [
            'title', 'query', 'report_content',
            'dataset', 'dataset_snapshot', 'metadata',
            'analysis_type', 'reasoning_trace'
        ]
        extra_kwargs = {
            'dataset': {'required': False},
            'dataset_snapshot': {'required': False},
            'metadata': {'required': False},
            'analysis_type': {'required': False},
            'reasoning_trace': {'required': False}
        }