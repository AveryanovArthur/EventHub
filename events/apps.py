from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'

    def ready(self):
        from django.conf import settings

        if settings.BACKGROUND_WORKER_ENABLED:
            from . import background

            background.start_worker()