from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .registries import registry


@receiver(post_save)
def update_document(sender, **kwargs):
    instance = kwargs['instance']
    registry.update(instance)


@receiver(post_delete)
def delete_document(sender, **kwargs):
    instance = kwargs['instance']
    registry.delete(instance, raise_on_error=False)
