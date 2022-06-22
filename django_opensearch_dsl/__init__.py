import django

from django.utils.module_loading import autodiscover_modules

from .documents import Document  # noqa
from .fields import *  # noqa

__version__ = "0.3.0"


def autodiscover():
    """Force the import of the `documents` modules of each `INSTALLED_APPS`."""
    autodiscover_modules("documents")


if django.VERSION < (3, 2):  # pragma: no cover
    default_app_config = "django_opensearch_dsl.apps.DODConfig"
