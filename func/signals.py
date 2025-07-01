from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.core.mail import send_mail
from .models import Notification

@receiver(user_signed_up)
def on_user_signed_up(request, user, **kwargs):
    send_mail(
        subject="Welcome to SmartInterviewer!",
        message=f"Hi {user.username}, thanks for joining!",
        from_email=None,
        recipient_list=[user.email],
    )
    Notification.objects.create(
        user=user,
        message="Welcome to SmartInterviewer!"
    )
