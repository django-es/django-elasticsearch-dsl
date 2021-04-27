import django

from django.utils.module_loading import autodiscover_modules

from .documents import Document  # noqa
from .indices import Index  # noqa
from .fields import *  # noqa

__version__ = '7.1.1'


def autodiscover():
    autodiscover_modules('documents')


if django.VERSION < (3, 2):
    default_app_config = 'django_elasticsearch_dsl.apps.DEDConfig'
