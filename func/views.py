import json
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, viewsets, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import InterviewSession, Notification, Question
from .serializers import NotificationSerializer, QuestionAdminSerializer, UserSerializer, ResumeSerializer, InterviewSessionSerializer, QuestionSerializer, AnswerSerializer, InterviewHistorySerializer, UserSignupSerializer
from django_q.tasks import async_task
from .parser import parse_resume_file, execute
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML

class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_object(self):
        return self.request.user

class ResumeUploadView(CreateAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    def perform_create(self, serializer):
        resume = serializer.save(owner=self.request.user)
        try:
            parsed = parse_resume_file(resume.file.path)
            resume.parsed_text = json.dumps(parsed)
            resume.save()
        except Exception as e:
            resume.parsed_text = json.dumps({'error': str(e)})
            resume.save()
        session = InterviewSession.objects.create(user=self.request.user)
        self.session_id = session.id
    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        resp.data['session_id'] = str(self.session_id)
        return resp

from .parser import parse_resume_file, build_prompt, execute
from .models import Question  # Assuming you have a Question model

class StartInterviewSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        resume = request.user.resume.order_by('-uploaded_at').first()

        # 1. Parse the resume
        parsed = parse_resume_file(resume.file.path)
        resume.parsed_text = json.dumps(parsed)
        resume.save()

        # 2. Generate questions only if session doesn't have them
        if not session.questions.exists():
            prompt = build_prompt(parsed, {"job": "Senior Backend Developer at Amazon"})  # Can be dynamic later
            generated_output = execute(prompt)

            # 3. Extract actual questions from LLM output (after "Questions:\n1. ...")
            questions_block = generated_output.split("Questions:")[-1].strip()
            questions = [q.strip() for q in questions_block.split("\n") if q.strip()]
            
            for q in questions:
                # Remove numbering like "1." or "2."
                clean_q = q.lstrip("0123456789. ").strip()
                if clean_q:
                    Question.objects.create(session=session, text=clean_q)

        # 4. Return session and first question
        session_data = InterviewSessionSerializer(session).data
        first_q = session.questions.order_by('created_at').first()
        question_data = QuestionSerializer(first_q).data if first_q else {}

        return Response({'session': session_data, 'first_question': question_data}, status=status.HTTP_200_OK)

class NextQuestionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        next_qs = session.questions.exclude(answers__isnull=False).order_by('created_at')
        if not next_qs.exists():
            return Response({'detail': 'No more questions.'}, status=status.HTTP_204_NO_CONTENT)
        q = next_qs.first()
        return Response(QuestionSerializer(q).data, status=status.HTTP_200_OK)

class SubmitAnswerView(CreateAPIView):
    serializer_class = AnswerSerializer
    parser_classes   = [JSONParser]
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        question = get_object_or_404(Question, id=self.kwargs['question_id'], session__user=self.request.user)
        answer   = serializer.save(question=question)
        # **kick off** the full pipeline
        async_task('func.tasks.full_answer_analysis', str(answer.id))
        Notification.objects.create(
            user    = self.request.user,
            session = question.session,
            message = f"Your answer for question '{question.text[:30]}…' was submitted and is being analyzed."
        )


class SessionAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        detailed = []
        scores = []
        suggestions = []
        for question in session.questions.prefetch_related('answers__analysis'):
            for answer in question.answers.all():
                if hasattr(answer, 'analysis'):
                    a = answer.analysis
                    detailed.append({
                        "question_id":        str(question.id),
                        "question_text":      question.text,
                        "answer_id":          str(answer.id),
                        "transcript":         answer.transcript,
                        "tone_score":         a.tone_score,
                        "pace_wpm":           a.pace_wpm,
                        "fluency_score":      a.fluency_score,
                        "relevance_score":    a.relevance_score,
                    })
                    if a.relevance_score is not None:
                        scores.append(a.relevance_score)
                        if a.relevance_score < 0.7:
                            suggestions.append(
                                f"Question '{question.text[:30]}...' could use more relevance."
                            )
        overall = sum(scores) / len(scores) if scores else 0
        report_payload = {
            'session_id':   session.id,
            'role':         request.user.profile.get_preferred_role_display(),
            'started_at':   session.started_at,
            'finished_at':  session.finished_at,
            'questions':    detailed,            # embed the detailed list here
            'overall_score': overall,
            'suggestions':   suggestions or ["Great job! Keep it up."],
        }
        serializer = InterviewSessionSerializer(report_payload)    
        return Response({
            "message": "SESSION ANALYSIS",
            "data": serializer.data,
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
        

class SessionAnalysisPDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, session_id):
        analysis_data = SessionAnalysisView().get(request, session_id).data
        html_string = render_to_string('report_template.html', { 'report': analysis_data })
        pdf_file = HTML(string=html_string).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{session_id}.pdf"'
        return response
    
class InterviewHistoryView(ListAPIView):
    """
    List all past interview sessions for the current user.
    """
    serializer_class = InterviewHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InterviewSession.objects.filter(user=self.request.user).order_by('-started_at')
    
class QuestionAdminViewSet(viewsets.ModelViewSet):
    """
    Admin-only CRUD for questions.
    """
    queryset = Question.objects.all().order_by('-created_at')
    serializer_class = QuestionAdminSerializer
    permission_classes = [permissions.IsAdminUser]
    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        diff = self.request.query_params.get('difficulty')
        cat = self.request.query_params.get('category')
        if role:
            qs = qs.filter(role=role)
        if diff:
            qs = qs.filter(difficulty=diff)
        if cat:
            qs = qs.filter(category=cat)
        return qs
    
class NotificationListView(generics.ListAPIView):
    serializer_class   = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, notification_id):
        notif = get_object_or_404(Notification, id=notification_id, user=request.user)
        notif.read = True
        notif.save()
        return Response({
            "message": "read",
            "data": "",
            'status': 'read'
        }, status=status.HTTP_200_OK)
        
    
class SignupView(generics.CreateAPIView):
    """
    User registration endpoint
    """
    serializer_class = UserSignupSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            "message": "User registered successfully",
            "data": self.get_serializer(user).data,
            "status": status.HTTP_201_CREATED
        }, status=status.HTTP_200_OK)