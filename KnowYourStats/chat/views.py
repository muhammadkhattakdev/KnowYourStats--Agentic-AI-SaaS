from rest_framework import status, generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from .models import ChatSession, Message
from .serializers import (
    ChatSessionSerializer,
    ChatSessionDetailSerializer,
    CreateChatSessionSerializer,
    MessageSerializer
)


class ChatSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for chat sessions"""
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatSessionDetailSerializer
        elif self.action == 'create':
            return CreateChatSessionSerializer
        return ChatSessionSerializer
    
    def get_queryset(self):
        """Get chat sessions for current user"""
        return ChatSession.objects.filter(
            user=self.request.user
        ).annotate(
            message_count=Count('messages')
        )
    
    def create(self, request, *args, **kwargs):
        """Create new chat session"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        chat_session = ChatSession.objects.create(
            user=request.user,
            title=serializer.validated_data.get('title', 'New Chat')
        )
        
        return Response({
            'success': True,
            'message': 'Chat session created',
            'data': ChatSessionSerializer(chat_session).data
        }, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """Get chat session with all messages"""
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
        """List all chat sessions"""
        queryset = self.filter_queryset(self.get_queryset())
        
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
        """Update chat session"""
        instance = self.get_object()
        
        # Check ownership
        if instance.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'success': True,
            'message': 'Chat session updated',
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete chat session"""
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
            'message': 'Chat session deleted'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a chat session"""
        chat_session = self.get_object()
        
        if chat_session.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        chat_session.is_active = False
        chat_session.save()
        
        return Response({
            'success': True,
            'message': 'Chat session archived'
        })
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive a chat session"""
        chat_session = self.get_object()
        
        if chat_session.user != request.user:
            return Response({
                'success': False,
                'message': 'Not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        chat_session.is_active = True
        chat_session.save()
        
        return Response({
            'success': True,
            'message': 'Chat session unarchived'
        })
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get archived chat sessions"""
        queryset = self.get_queryset().filter(is_active=False)
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for messages (read-only, messages created via WebSocket)"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        """Get messages for current user's chat sessions"""
        chat_session_id = self.request.query_params.get('chat_session_id')
        
        queryset = Message.objects.filter(
            chat_session__user=self.request.user
        )
        
        if chat_session_id:
            queryset = queryset.filter(chat_session_id=chat_session_id)
        
        return queryset.order_by('created_at')
    
    def list(self, request, *args, **kwargs):
        """List messages"""
        queryset = self.filter_queryset(self.get_queryset())
        
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