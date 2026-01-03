from celery import shared_task
from .agent_core import AgenticAI, SimpleResponseAgent
import json


@shared_task(bind=True, max_retries=2)
def process_agent_message(self, user_query, dataset_context=None, chat_session_id=None):
    """
    Process user message with Agentic AI
    This runs asynchronously to avoid blocking WebSocket
    """
    
    try:
        # Initialize agent
        agent = AgenticAI(user_query, dataset_context)
        
        # Run agentic analysis
        result = agent.run()
        
        return {
            'success': True,
            'chat_session_id': chat_session_id,
            'report': result['report'],
            'reasoning_trace': result['reasoning_trace'],
            'tools_used': result['tools_used'],
            'findings': result['findings']
        }
        
    except Exception as e:
        # Log error and retry
        print(f"Agent processing error: {str(e)}")
        
        # Retry task
        raise self.retry(exc=e, countdown=30)


@shared_task
def generate_chat_title(first_message):
    """Generate chat title from first message"""
    
    try:
        agent = SimpleResponseAgent(
            f"Generate a short 3-5 word title for a chat that starts with: '{first_message[:100]}'. "
            "Return ONLY the title, nothing else."
        )
        
        title = agent.respond().strip().strip('"\'')
        return title[:255]  # Ensure it fits in DB field
        
    except Exception as e:
        print(f"Title generation error: {str(e)}")
        return "New Analysis Chat"


@shared_task
def analyze_dataset_background(dataset_id, analysis_type='general'):
    """
    Background task for dataset analysis
    Can be used for pre-computing insights
    """
    
    try:
        from data_manager.models import Dataset
        import pandas as pd
        
        dataset = Dataset.objects.get(id=dataset_id)
        
        # Load data
        if dataset.file_type == 'csv':
            df = pd.read_csv(dataset.file.path)
        else:
            df = pd.read_excel(dataset.file.path)
        
        # Perform analysis based on type
        if analysis_type == 'general':
            # General statistical analysis
            insights = {
                'row_count': len(df),
                'column_count': len(df.columns),
                'numeric_columns': list(df.select_dtypes(include=['number']).columns),
                'categorical_columns': list(df.select_dtypes(include=['object']).columns),
                'missing_data': df.isnull().sum().to_dict()
            }
        
        # Store insights in dataset metadata
        if dataset.metadata is None:
            dataset.metadata = {}
        
        dataset.metadata['background_analysis'] = insights
        dataset.save()
        
        return {
            'success': True,
            'dataset_id': str(dataset_id),
            'insights': insights
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }