from django.urls import path
from .views import UserProfileView, ResumeUploadView
from . import views

urlpatterns = [
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('resume/upload/', views.ResumeUploadView.as_view(), name='resume-upload'),
    path('session/<uuid:session_id>/start/', views.StartInterviewSessionView.as_view(), name='start-session'),
    path('session/<uuid:session_id>/next/', views.NextQuestionView.as_view(), name='next-question'),
    path('question/<uuid:question_id>/answer/', views.SubmitAnswerView.as_view(), name='submit-answer'),
    path('session/<uuid:session_id>/analysis/', views.SessionAnalysisView.as_view(), name='session-analysis'),
    path('session/<uuid:session_id>/pdf/', views.SessionAnalysisPDFView.as_view(), name='session-pdf'),
    path('history/', views.InterviewHistoryView.as_view(), name='interview-history'),
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:notification_id>/read/', views.NotificationMarkReadView.as_view(), name='mark-read'),
    path('signup/', views.SignupView.as_view(), name='signup'),
]
