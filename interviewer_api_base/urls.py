from django.urls import path
from .views import (
    ResumeUploadView,
    GenerateSessionQuestionsView,
    SignupView,
    SubmitAnswerView,
    QALogsView,
    GenerateCategoryQuestionsView,
)

urlpatterns = [
    path('upload-resume/', ResumeUploadView.as_view(), name='upload-resume'),

    path(
        'generate-questions/<uuid:session_id>/',
        GenerateSessionQuestionsView.as_view(),
        name='generate-questions'
    ),

    path(
        'submit-answer/<uuid:question_id>/',
        SubmitAnswerView.as_view(),
        name='submit-answer'
    ),

    path(
        'qa-logs/<uuid:session_id>/',
        QALogsView.as_view(),
        name='qa-logs'
    ),

    path(
        'generate-category-questions/<str:category>/',
        GenerateCategoryQuestionsView.as_view(),
        name='generate-category-questions'
    ),

    path(
        'signup/', 
        SignupView.as_view(), 
        name='signup'),
]
