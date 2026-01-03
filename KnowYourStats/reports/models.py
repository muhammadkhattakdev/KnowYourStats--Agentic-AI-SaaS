from django.db import models
from django.conf import settings
import uuid


class Report(models.Model):
    """Report model for saved analysis reports"""
    
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    chat_session = models.ForeignKey(
        'chat.ChatSession',
        on_delete=models.CASCADE,
        related_name='reports',
        null=True,
        blank=True
    )
    
    # Report content
    title = models.CharField(max_length=500)  # Auto-generated from query
    query = models.TextField()  # Original user query/instruction
    report_content = models.TextField()  # Generated report
    
    # Associated dataset
    dataset = models.ForeignKey(
        'data_manager.Dataset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )
    
    # Dataset snapshot (in case dataset is deleted)
    dataset_snapshot = models.JSONField(default=dict, blank=True)  # Store key dataset info
    
    # Report metadata
    metadata = models.JSONField(default=dict, blank=True)
    analysis_type = models.CharField(max_length=100, blank=True)  # e.g., "trend_analysis", "correlation"
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    error_message = models.TextField(blank=True)
    
    # Agent reasoning trace (for debugging/transparency)
    reasoning_trace = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def get_short_query(self, max_length=100):
        """Get shortened query for display"""
        if len(self.query) <= max_length:
            return self.query
        return self.query[:max_length] + "..."


class ReportVisualization(models.Model):
    """Store visualizations/charts generated for reports"""
    
    CHART_TYPE_CHOICES = [
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('scatter', 'Scatter Plot'),
        ('heatmap', 'Heatmap'),
        ('table', 'Table'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='visualizations'
    )
    
    # Visualization data
    chart_type = models.CharField(max_length=20, choices=CHART_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    data = models.JSONField()  # Chart data in JSON format
    config = models.JSONField(default=dict, blank=True)  # Chart configuration
    
    # Order
    order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['report', 'order']
        verbose_name = 'Report Visualization'
        verbose_name_plural = 'Report Visualizations'
    
    def __str__(self):
        return f"{self.title} ({self.chart_type}) - {self.report.title}"