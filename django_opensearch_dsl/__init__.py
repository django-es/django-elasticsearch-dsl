import django

from django.utils.module_loading import autodiscover_modules

from .documents import Document  # noqa
from .fields import *  # noqa

__version__ = '0.2.0'


def autodiscover():
    autodiscover_modules('documents')


if django.VERSION < (3, 2):  # pragma: no cover
    default_app_config = 'django_opensearch_dsl.apps.DEDConfig'
