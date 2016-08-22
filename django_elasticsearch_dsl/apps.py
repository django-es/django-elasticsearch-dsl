from django.apps import AppConfig
from elasticsearch_dsl.connections import connections
from django.conf import settings


class DEDConfig(AppConfig):
    name = 'django_elasticsearch_dsl'
    verbose_name = "Django elasticsearch-dsl"

    def ready(self):
        self.module.autodiscover()
        connections.configure(**settings.ELASTICSEARCH_DSL)
