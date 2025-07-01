from django.contrib import admin
from .models import Question, InterviewSession, Answer, AnswerAnalysis, Resume, Profile

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'preferred_role']
    list_filter  = ['preferred_role']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'text', 'created_at']
    list_filter  = ['session__user__profile__preferred_role']
    search_fields= ['text']

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'question', 'responded_at']
    list_filter  = ['question__session__user__profile__preferred_role']
    search_fields= ['transcript']

@admin.register(AnswerAnalysis)
class AnswerAnalysisAdmin(admin.ModelAdmin):
    list_display = ['answer', 'tone_score', 'pace_wpm', 'fluency_score', 'relevance_score']
    list_filter  = ['tone_score', 'relevance_score']

@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'started_at', 'finished_at']
    list_filter  = ['user__profile__preferred_role']
    date_hierarchy = 'started_at'

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'uploaded_at']
    list_filter  = ['owner__profile__preferred_role']
    search_fields= ['file']
