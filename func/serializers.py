from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Resume, InterviewSession, Question, Answer, AnswerAnalysis, Notification

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    preferred_role = serializers.CharField(source='profile.role', required=False)
    class Meta:
        model=User
        fields=['id', 'username', 'email', 'preferred_role']
        read_only_fields= ['id', 'username', 'email']

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model= Resume
        fields= ['id', 'resume_file', 'parsed_text', 'uploaded_at']
        read_only_fields= ['id', 'parsed_text', 'uploaded_at']

class InterviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model= InterviewSession
        fields= ['id', 'started_at', 'ended_at']
        read_only_fields= ['id', 'started_at', 'ended_at']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model= Question
        fields= ['id', 'session', 'text', 'created_at']
        read_only_fields= ['id', 'session', 'text', 'created_at']

class AnswerAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AnswerAnalysis
        fields = ['tone_score', 'pace_wpm', 'fluency_score', 'relevance_score', 'average_pause_duration', 'pause_frequency', 'speech_rate_consistency']
        read_only_fields = fields

class AnswerSerializer(serializers.ModelSerializer):
    analysis= AnswerAnalysisSerializer(read_only=True)
    class Meta:
        model= Answer
        fields= ['id', 'audio_file', 'transcript', 'responded_at', 'analysis']
        read_only_fields = ['id', 'transcript', 'responded_at', 'analysis']

class InterviewHistorySerializer(serializers.ModelSerializer):
    total_questions     = serializers.SerializerMethodField()
    answered_questions  = serializers.SerializerMethodField()
    analysis_url        = serializers.SerializerMethodField()
    pdf_report_url      = serializers.SerializerMethodField()
    class Meta:
        model= InterviewSession
        fields= ['id', 'started_at', 'ended_at', 'total_questions', 'answered_questions', 'analysis_url', 'pdf_report_url']
    def get_total_questions(self, obj):
        return obj.questions.count()
    def get_answered_questions(self, obj):
        return sum(q.answers.count() for q in obj.questions.all())
    def get_analysis_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(f'/analysis/{obj.id}/')
    def get_pdf_report_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(f'/analysis-pdf/{obj.id}/')
    
class QuestionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Question
        fields = [ 'id', 'session', 'role', 'difficulty', 'category', 'text', 'created_at']
        read_only_fields = ['id', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    analysis_url = serializers.SerializerMethodField()
    pdf_url      = serializers.SerializerMethodField()
    class Meta:
        model  = Notification
        fields = ['id', 'message', 'created_at', 'read', 'analysis_url', 'pdf_url']
    def get_analysis_url(self, obj):
        if not obj.session:
            return None
        req = self.context.get('request')
        return req.build_absolute_uri(f'/analysis/{obj.session.id}/')
    def get_pdf_url(self, obj):
        if not obj.session:
            return None
        req = self.context.get('request')
        return req.build_absolute_uri(f'/analysis-pdf/{obj.session.id}/')
    
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