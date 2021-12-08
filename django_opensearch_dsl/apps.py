from django.apps import AppConfig
from django.conf import settings

from opensearch_dsl.connections import connections


class DEDConfig(AppConfig):
    name = 'django_opensearch_dsl'
    verbose_name = "django-opensearch-dsl"

    def ready(self):
        self.module.autodiscover()
        connections.configure(**settings.OPENSEARCH_DSL)

    @classmethod
    def default_index_settings(cls):
        return getattr(settings, 'OPENSEARCH_DSL_INDEX_SETTINGS', {})

    @classmethod
    def auto_refresh_enabled(cls):
        return getattr(settings, 'OPENSEARCH_DSL_AUTO_REFRESH', False)

    @classmethod
    def default_queryset_pagination(cls):
        return getattr(settings, "OPENSEARCH_DSL_QUERYSET_PAGINATION", 4096)
