from celery import shared_task
from django.contrib.contenttypes.models import ContentType

from .registries import registry


@shared_task
def task_handle_save(pk, content_type):
    ct_model = ContentType.objects.get_by_natural_key(*content_type)
    instance = ct_model.get_object_for_this_type(pk=pk)
    registry.update(instance)
    registry.update_related(instance)

@shared_task
def task_handle_delete_related(pk, content_type):
    ct_model = ContentType.objects.get_by_natural_key(*content_type)
    instance = ct_model.get_object_for_this_type(pk=pk)
    registry.update(instance)

@shared_task
def task_handle_delete(ids, content_type):
    ct_model = ContentType.objects.get_by_natural_key(*content_type)
    registry.delete_by_id(ids, ct_model, raise_on_error=False)
