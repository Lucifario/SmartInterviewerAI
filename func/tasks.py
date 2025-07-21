from celery import shared_task
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from .models import Answer, AnswerAnalysis, InterviewSession, Notification
from .transcriber import transcribe   # your whisper logic
from .analyzer import analyze         # your LLM logic


def full_answer_analysis(answer_id):
    """
    1) Transcribe the saved audio with timestamps
    2) Run LLM analysis on those segments
    3) Persist transcript & analysis metrics
    """
    answer = get_object_or_404(Answer, id=answer_id)

    # 1) Transcription
    # segments = transcribe(answer.audio_file.path)
    full_text = answer.transcript
    answer.transcript = full_text
    answer.save()

    # 2) LLM Analysis
    question_text = answer.question.text
    metrics = analyze(segments, question_text)
    # metrics => {"tone": str, "speed": str, "fluency": str, "relevance": float}

    # 3) Persist into AnswerAnalysis
    AnswerAnalysis.objects.update_or_create(
        answer=answer,
        defaults={
            'tone_score':      None,               # convert if needed from metrics['tone']
            'pace_wpm':        None,               # convert if needed from metrics['speed']
            'fluency_score':   None,               # convert if needed from metrics['fluency']
            'relevance_score': metrics.get('relevance'),
            # add pause metrics here if you compute them
        }
    )
    return {'status': 'ok', 'metrics': metrics}


@shared_task
def send_report_ready_alert(session_id):
    """
    1) Email the user that their report is ready
    2) Create an in‑app Notification
    """
    session = InterviewSession.objects.get(id=session_id)
    user = session.user

    # 1) Send email
    send_mail(
        subject="Your Interview Report Is Ready",
        message=f"Hi {user.username}, your report for session {session_id} is available.",
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
    )

    # 2) In-app alert
    Notification.objects.create(
        user=user,
        session=session,
        message=f"Your interview report for session {session_id} is ready."
    )
