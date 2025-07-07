from django.contrib import admin
from .models import (
    Profile,
    Resume,
    InterviewSession,
    Question,
    Answer,
    AnswerAnalysis,
    Notification,
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'preferred_role', 'difficulty', 'category']
    list_filter   = ['preferred_role', 'difficulty', 'category']
    search_fields = ['user__username', 'user__email']


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display  = ['id', 'user', 'resume_file', 'created_at', 'updated_at']
    list_filter   = ['user__profile__preferred_role']
    search_fields = ['user__username', 'resume_file']


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display   = ['id', 'user', 'started_at', 'ended_at']
    list_filter    = ['user__profile__preferred_role']
    date_hierarchy = 'started_at'
    search_fields  = ['user__username']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display  = ['id', 'session', 'text', 'created_at']
    list_filter   = ['session__user__profile__preferred_role']
    search_fields = ['text']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display  = ['id', 'question', 'responded_at']
    list_filter   = ['question__session__user__profile__preferred_role']
    search_fields = ['transcript']


@admin.register(AnswerAnalysis)
class AnswerAnalysisAdmin(admin.ModelAdmin):
    list_display  = [
        'answer',
        'tone_score',
        'pace_wpm',
        'fluency_score',
        'relevance_score',
        'average_pause_duration',
        'pause_frequency',
        'speech_rate_consistency',
    ]
    list_filter   = ['tone_score', 'relevance_score']
    search_fields = ['answer__id']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['id', 'user', 'session', 'message', 'read', 'created_at']
    list_filter   = ['read', 'user__profile__preferred_role']
    search_fields = ['message', 'user__username']
