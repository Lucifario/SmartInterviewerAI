import json
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, viewsets, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from .models import InterviewSession, Notification, Question
from .serializers import NotificationSerializer, QuestionAdminSerializer, UserSerializer, ResumeSerializer, InterviewSessionSerializer, QuestionSerializer, AnswerSerializer, InterviewHistorySerializer, UserSignupSerializer
from .tasks import full_answer_analysis
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
        resume = serializer.save(user=self.request.user)
        try:
            parsed = parse_resume_file(resume.resume_file.path)
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

class StartInterviewSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        resume = request.user.resumes.order_by('-created_at').first()
        
        # Parse and save resume data
        parsed = parse_resume_file(resume.resume_file.path)
        resume.parsed_text = json.dumps(parsed)
        resume.save()
        
        # Generate questions if none exist
        if not session.questions.exists():
            execute(session, resume.resume_file.path)  # Fixed function call
        
        session_data = InterviewSessionSerializer(session).data
        first_q = session.questions.order_by('created_at').first()
        question_data = QuestionSerializer(first_q).data
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
    parser_classes   = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        question = get_object_or_404(Question, id=self.kwargs['question_id'], session__user=self.request.user)
        answer   = serializer.save(question=question)
        # **kick off** the full pipeline
        full_answer_analysis.delay(str(answer.id))
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
        
        # Fixed profile access with error handling
        role = 'Unknown'
        if hasattr(request.user, 'profile') and request.user.profile:
            role = request.user.profile.get_preferred_role_display()
        
        report_payload = {
            'session_id':   session.id,
            'role':         role,
            'started_at':   session.started_at,
            'ended_at':     session.ended_at,  # Fixed field name
            'questions':    detailed,
            'overall_score': overall,
            'suggestions':   suggestions or ["Great job! Keep it up."],
        }
        serializer = InterviewSessionSerializer(report_payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
        return Response({'status': 'read'})
    
class SignupView(generics.CreateAPIView):
    """
    User registration endpoint
    """
    serializer_class = UserSignupSerializer
    permission_classes = [permissions.AllowAny]