# smartinterviewer/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartinterviewer.settings')
app = Celery('smartinterviewer')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
