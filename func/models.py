from django.conf import settings
from django.db import models
import uuid
from django.dispatch import receiver
from django.db.models.signals import post_save

# Create your models here.
class Profile(models.Model):
    ROLES=[
        ('SDE', 'Software Development Engineer'),
        ('QA', 'Quality Assurance'),
        ('PM', 'Project Manager'),
        ('HR', 'Human Resources'),
        ('UI/UX', 'User Interface/User Experience'),
        ('DevOps', 'Development Operations'),
    ]
    DIFFICULTY_CHOICES = [
        ('E', 'Easy'),
        ('M', 'Medium'),
        ('H', 'Hard'),
    ]
    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('behavioral', 'Behavioral'),
        ('scenario', 'Scenario'),
    ]
    user=models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    preferred_role=models.CharField(max_length=20, choices=ROLES, default='SDE')
    difficulty= models.CharField(max_length=1, choices=DIFFICULTY_CHOICES, default='M')
    category= models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='technical')
    def __str__(self):
        return f"{self.user.username} - {self.preferred_role} Profile"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile when a new User is created"""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """Save the Profile when User is saved (if profile exists)"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        Profile.objects.get_or_create(user=instance)

class Resume(models.Model):
    owner=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resume')
    file=models.FileField(upload_to='resume/')
    uploaded_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    parsed_text=models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.owner.username} - Resume {self.id}"
    
class InterviewSession(models.Model):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interview_sessions')
    started_at=models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"Session {self.id} for {self.user.username} started at {self.started_at}"

class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q {self.id} for session {self.session.id}"
    
class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    audio_file = models.FileField(upload_to='answers/', blank=True, null=True)
    transcript = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"A {self.id} to Q {self.question.id}"
    
class AnswerAnalysis(models.Model):
    answer                  = models.OneToOneField(Answer, on_delete=models.CASCADE, related_name='analysis')
    tone_score              = models.FloatField(null=True, blank=True)
    pace_wpm                = models.FloatField(null=True, blank=True)
    fluency_score           = models.FloatField(null=True, blank=True)
    relevance_score         = models.FloatField(null=True, blank=True)
    average_pause_duration  = models.FloatField(null=True, blank=True)
    pause_frequency         = models.IntegerField(null=True, blank=True)
    speech_rate_consistency = models.FloatField(null=True, blank=True)
    created_at              = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Analysis for Answer {self.answer.id}"
    
class Notification(models.Model):
    user= models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='notifications')
    session= models.ForeignKey('InterviewSession',on_delete=models.CASCADE,null=True,blank=True)
    message= models.CharField(max_length=255)
    read= models.BooleanField(default=False)
    created_at= models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Notif for {self.user.username}: {self.message[:20]}"