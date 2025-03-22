import os
from celery import Celery
import multiprocessing
import platform

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zunhub.settings')

app = Celery('zunhub')


if platform.system() == "Windows":
    multiprocessing.set_start_method('spawn', force=True)


# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in installed apps
app.autodiscover_tasks()
