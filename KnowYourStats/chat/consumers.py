import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatSession, Message
from data_manager.models import Dataset
from agent.agent_core import AgenticAI, SimpleResponseAgent
from agent.tasks import process_agent_message
import pandas as pd


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chat functionality"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        self.chat_session_id = self.scope['url_route']['kwargs']['chat_session_id']
        self.room_group_name = f'chat_{self.chat_session_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chat',
            'chat_session_id': str(self.chat_session_id)
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_user_message(data)
            elif message_type == 'typing':
                await self.handle_typing_indicator(data)
            elif message_type == 'save_report':
                await self.handle_save_report(data)
            
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
        except Exception as e:
            await self.send_error(f'Error: {str(e)}')
    
    async def handle_user_message(self, data):
        """Handle user chat message"""
        content = data.get('content', '').strip()
        
        if not content:
            return
        
        # Save user message
        user_message = await self.save_message(
            role='user',
            content=content,
            message_type='text'
        )
        
        # Send user message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': str(user_message.id),
                    'role': 'user',
                    'content': content,
                    'message_type': 'text',
                    'created_at': user_message.created_at.isoformat()
                }
            }
        )
        
        # Check if this is the first message (for auto-title generation)
        message_count = await self.get_message_count()
        if message_count == 1:
            await self.generate_chat_title(content)
        
        # Send typing indicator
        await self.send_typing_indicator(True)
        
        # Determine if query needs agentic analysis
        needs_analysis = await self.check_if_needs_analysis(content, data.get('dataset_id'))
        
        if needs_analysis:
            # Process with Agentic AI (async task)
            dataset_id = data.get('dataset_id')
            await self.process_with_agent(content, dataset_id)
        else:
            # Simple conversational response
            response = await self.get_simple_response(content)
            await self.send_agent_response(response, message_type='text')
        
        # Send typing indicator off
        await self.send_typing_indicator(False)
    
    async def handle_typing_indicator(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'is_typing': is_typing,
                'user': self.user.email
            }
        )
    
    async def handle_save_report(self, data):
        """Handle save report request"""
        message_id = data.get('message_id')
        
        if not message_id:
            await self.send_error('Message ID required')
            return
        
        # Create report from message
        report = await self.create_report_from_message(message_id)
        
        if report:
            await self.send(text_data=json.dumps({
                'type': 'report_saved',
                'report_id': str(report.id),
                'message': 'Report saved successfully'
            }))
        else:
            await self.send_error('Failed to save report')
    
    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send(text_data=json.dumps(event['message']))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing'],
            'user': event.get('user', 'agent')
        }))
    
    async def agent_response(self, event):
        """Send agent response to WebSocket"""
        await self.send(text_data=json.dumps(event['message']))
    
    async def send_agent_response(self, content, message_type='text', metadata=None):
        """Send agent response"""
        # Save agent message
        agent_message = await self.save_message(
            role='agent',
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        
        # Send to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'agent_response',
                'message': {
                    'id': str(agent_message.id),
                    'role': 'agent',
                    'content': content,
                    'message_type': message_type,
                    'metadata': metadata or {},
                    'created_at': agent_message.created_at.isoformat()
                }
            }
        )
    
    async def send_typing_indicator(self, is_typing):
        """Send typing indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'is_typing': is_typing,
                'user': 'agent'
            }
        )
    
    async def send_error(self, message):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    @database_sync_to_async
    def save_message(self, role, content, message_type='text', metadata=None):
        """Save message to database"""
        chat_session = ChatSession.objects.get(id=self.chat_session_id, user=self.user)
        
        message = Message.objects.create(
            chat_session=chat_session,
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        
        # Update chat session last message time
        chat_session.last_message_at = timezone.now()
        chat_session.save()
        
        return message
    
    @database_sync_to_async
    def get_message_count(self):
        """Get message count for chat session"""
        return Message.objects.filter(
            chat_session_id=self.chat_session_id
        ).count()
    
    @database_sync_to_async
    def generate_chat_title(self, first_message):
        """Generate chat title from first message"""
        from agent.agent_core import SimpleResponseAgent
        
        # Use AI to generate a concise title
        agent = SimpleResponseAgent(
            f"Generate a short 3-5 word title for a chat that starts with: '{first_message[:100]}'. Return ONLY the title, nothing else."
        )
        title = agent.respond().strip().strip('"\'')
        
        # Update chat session title
        chat_session = ChatSession.objects.get(id=self.chat_session_id)
        chat_session.title = title[:255]  # Ensure it fits
        chat_session.save()
        
        # Notify client of title update
        self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_title_updated',
                'title': title
            }
        )
    
    async def chat_title_updated(self, event):
        """Send title update to client"""
        await self.send(text_data=json.dumps({
            'type': 'title_updated',
            'title': event['title']
        }))
    
    @database_sync_to_async
    def check_if_needs_analysis(self, content, dataset_id):
        """Check if message needs agentic analysis"""
        # Simple heuristic: if dataset_id provided or message contains analysis keywords
        analysis_keywords = [
            'analyze', 'analysis', 'report', 'investigate', 'find', 'show',
            'compare', 'correlation', 'trend', 'pattern', 'insight', 'what'
        ]
        
        if dataset_id:
            return True
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in analysis_keywords)
    
    async def process_with_agent(self, query, dataset_id):
        """Process query with agentic AI"""
        # This will be handled by Celery task for heavy processing
        # For now, send a simple processing message
        
        dataset_context = await self.get_dataset_context(dataset_id) if dataset_id else None
        
        # Send processing status
        await self.send(text_data=json.dumps({
            'type': 'agent_processing',
            'message': 'Agent is analyzing your data...'
        }))
        
        # In production, this would be a Celery task
        # For now, we'll do synchronous processing
        try:
            agent = AgenticAI(query, dataset_context)
            result = await database_sync_to_async(agent.run)()
            
            # Send report as agent response
            await self.send_agent_response(
                content=result['report'],
                message_type='report',
                metadata={
                    'reasoning_trace': result['reasoning_trace'],
                    'tools_used': result['tools_used']
                }
            )
        except Exception as e:
            await self.send_error(f'Analysis failed: {str(e)}')
    
    @database_sync_to_async
    def get_dataset_context(self, dataset_id):
        """Get dataset context for analysis"""
        try:
            dataset = Dataset.objects.get(id=dataset_id, user=self.user)
            
            # Load basic dataset info
            context = {
                'filename': dataset.original_filename,
                'columns': dataset.columns,
                'row_count': dataset.row_count,
                'column_count': dataset.column_count
            }
            
            # Load sample data if file exists
            if dataset.file:
                try:
                    if dataset.file_type == 'csv':
                        df = pd.read_csv(dataset.file.path, nrows=100)
                    else:
                        df = pd.read_excel(dataset.file.path, nrows=100)
                    
                    context['sample_data'] = df.to_dict('records')
                    context['data_types'] = df.dtypes.astype(str).to_dict()
                except Exception as e:
                    context['error'] = f'Failed to load data: {str(e)}'
            
            return context
        except Dataset.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_simple_response(self, query):
        """Get simple conversational response"""
        agent = SimpleResponseAgent(query)
        return agent.respond()
    
    @database_sync_to_async
    def create_report_from_message(self, message_id):
        """Create report from a message"""
        from reports.models import Report
        
        try:
            message = Message.objects.get(id=message_id, chat_session__user=self.user)
            
            if not message.is_report_message():
                return None
            
            # Get the user query (previous message)
            user_query = Message.objects.filter(
                chat_session=message.chat_session,
                role='user',
                created_at__lt=message.created_at
            ).order_by('-created_at').first()
            
            report = Report.objects.create(
                user=self.user,
                chat_session=message.chat_session,
                title=f"Report: {user_query.content[:100] if user_query else 'Analysis'}",
                query=user_query.content if user_query else '',
                report_content=message.content,
                metadata=message.metadata,
                status='completed'
            )
            
            # Link message to report
            message.related_report = report
            message.save()
            
            return report
        except Message.DoesNotExist:
            return None