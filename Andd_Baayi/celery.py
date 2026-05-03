import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Andd_Baayi.settings")

app = Celery("andd_baayi")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    return {
        "id": self.request.id,
        "args": self.request.args,
        "kwargs": self.request.kwargs,
        "retries": self.request.retries,
    }
