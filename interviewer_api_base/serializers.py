from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Resume, InterviewSession, Question, Answer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ['id', 'file', 'parsed_text', 'uploaded_at']
        read_only_fields = ['id', 'parsed_text', 'uploaded_at']

class InterviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSession
        fields = ['id', 'user', 'started_at', 'finished_at']
        read_only_fields = ['id', 'started_at', 'finished_at']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'session', 'text', 'created_at']
        read_only_fields = ['id', 'created_at']

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'question', 'audio_file', 'transcript', 'responded_at']
        read_only_fields = ['id', 'transcript', 'responded_at']

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
    def create(self, validated):
        user = User(
            username=validated['username'],
            email=validated.get('email', '')
        )
        user.set_password(validated['password'])
        user.save()
        return user