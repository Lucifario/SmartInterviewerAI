import uuid, datetime
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import CreateAPIView, ListAPIView
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from .serializers import UserSignupSerializer


from .models import Resume, InterviewSession, Question, Answer
from .serializers import (
    ResumeSerializer,
    QuestionSerializer,
    AnswerSerializer,
)

class GenerateCategoryQuestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    MOCK = {
        'python': [{'text': 'Explain lists vs tuples in Python'}],
        'javascript': [{'text': 'What is event delegation?'}],
    }

    def get(self, request, category):
        data = self.MOCK.get(category.lower())
        if not data:
            return Response(
                {'detail': f"Category '{category}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        questions = [
            {
                'id': str(uuid.uuid4()),
                'text': item['text'],
                'created_at': datetime.datetime.utcnow(),
            }
            for item in data
        ]
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


class ResumeUploadView(CreateAPIView):
    serializer_class = ResumeSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        resume = serializer.save(owner=self.request.user)
        # parsed = parse_resume(resume.file.path)
        # resume.parsed_text = parsed
        # resume.save()


class GenerateSessionQuestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(
            InterviewSession, id=session_id, user=request.user
        )
        if not session.questions.exists():
            for text in ["Q1 text…", "Q2 text…", "Q3 text…"]:
                Question.objects.create(session=session, text=text)
        qs = session.questions.all()
        serializer = QuestionSerializer(qs, many=True)
        return Response(serializer.data)


class SubmitAnswerView(CreateAPIView):
    serializer_class = AnswerSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        question = get_object_or_404(
            Question, 
            id=self.kwargs['question_id'], 
            session__user=self.request.user
        )
        answer = serializer.save(question=question)
        # transcript = transcribe(answer.audio_file.path)
        # answer.transcript = transcript
        # answer.save()


class QALogsView(ListAPIView):
    serializer_class = AnswerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        session = get_object_or_404(
            InterviewSession, 
            id=self.kwargs['session_id'], 
            user=self.request.user
        )
        return Answer.objects.filter(question__session=session)

class SignupView(generics.CreateAPIView):
    serializer_class = UserSignupSerializer
    permission_classes = [permissions.AllowAny]
