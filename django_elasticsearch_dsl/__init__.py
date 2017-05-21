from django.utils.module_loading import autodiscover_modules

from .documents import DocType  # noqa
from .indices import Index  # noqa
from .signals import delete_document, update_document # noqa
from .fields import * # noqa

__version__ = '0.1.0'


def autodiscover():
    autodiscover_modules('documents')


default_app_config = 'django_elasticsearch_dsl.apps.DEDConfig'
