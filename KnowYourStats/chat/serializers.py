from rest_framework import serializers
from .models import ChatSession, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""
    
    class Meta:
        model = Message
        fields = [
            'id', 'role', 'content', 'message_type',
            'metadata', 'related_report', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions"""
    
    message_count = serializers.IntegerField(read_only=True, source='get_message_count')
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'title', 'created_at', 'updated_at',
            'last_message_at', 'is_active', 'message_count', 'last_message'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_message_at']
    
    def get_last_message(self, obj):
        """Get last message preview"""
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'content': last_msg.content[:100] + ('...' if len(last_msg.content) > 100 else ''),
                'role': last_msg.role,
                'created_at': last_msg.created_at
            }
        return None


class ChatSessionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for chat session with messages"""
    
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(read_only=True, source='get_message_count')
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'title', 'created_at', 'updated_at',
            'last_message_at', 'is_active', 'message_count', 'messages'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_message_at']


class CreateChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for creating a new chat session"""
    
    class Meta:
        model = ChatSession
        fields = ['title']
        extra_kwargs = {
            'title': {'required': False}
        }