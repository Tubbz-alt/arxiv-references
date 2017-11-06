"""Initialize the Celery application."""

from references.factory import create_worker_app, celery_app

app = create_worker_app()
app.app_context().push()
