from django.apps import AppConfig
from elasticsearch_dsl.connections import connections
from django.conf import settings


class DEDConfig(AppConfig):
    name = 'django_elasticsearch_dsl'
    verbose_name = "Django elasticsearch-dsl"

    def ready(self):
        self.module.autodiscover()
        connections.configure(**settings.ELASTICSEARCH_DSL)

    @classmethod
    def autosync_enabled(cls):
        return getattr(settings, 'ELASTICSEARCH_DSL_AUTOSYNC', True)

    @classmethod
    def default_index_settings(cls):
        return getattr(settings, 'ELASTICSEARCH_DSL_INDEX_SETTINGS', {})

    @classmethod
    def auto_refresh_enabled(cls):
        return getattr(settings, 'ELASTICSEARCH_DSL_AUTO_REFRESH', True)
