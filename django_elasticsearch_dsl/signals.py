# encoding: utf-8
"""
A convenient way to attach django-elasticsearch-dsl to Django's signals and
cause things to index.
"""

from __future__ import absolute_import

from django.db import models
from django.apps import apps
from django.dispatch import Signal
from .registries import registry
from django.core.exceptions import ObjectDoesNotExist
from importlib import import_module
# Sent after document indexing is completed
post_index = Signal()

class BaseSignalProcessor(object):
    """Base signal processor.

    By default, does nothing with signals but provides underlying
    functionality.
    """

    def __init__(self, connections):
        self.connections = connections
        self.setup()

    def setup(self):
        """Set up.

        A hook for setting up anything necessary for
        ``handle_save/handle_delete`` to be executed.

        Default behavior is to do nothing (``pass``).
        """
        # Do nothing.

    def teardown(self):
        """Tear-down.

        A hook for tearing down anything necessary for
        ``handle_save/handle_delete`` to no longer be executed.

        Default behavior is to do nothing (``pass``).
        """
        # Do nothing.

    def handle_m2m_changed(self, sender, instance, action, **kwargs):
        if action in ('post_add', 'post_remove', 'post_clear'):
            self.handle_save(sender, instance)
        elif action in ('pre_remove', 'pre_clear'):
            self.handle_pre_delete(sender, instance)

    def handle_save(self, sender, instance, **kwargs):
        """Handle save.

        Given an individual model instance, update the object in the index.
        Update the related objects either.
        """
        registry.update(instance)
        registry.update_related(instance)

    def handle_pre_delete(self, sender, instance, **kwargs):
        """Handle removing of instance object from related models instance.
        We need to do this before the real delete otherwise the relation
        doesn't exists anymore and we can't get the related models instance.
        """
        registry.delete_related(instance)

    def handle_delete(self, sender, instance, **kwargs):
        """Handle delete.

        Given an individual model instance, delete the object from index.
        """
        registry.delete(instance, raise_on_error=False)


class RealTimeSignalProcessor(BaseSignalProcessor):
    """Real-time signal processor.

    Allows for observing when saves/deletes fire and automatically updates the
    search engine appropriately.
    """

    def setup(self):
        # Listen to all model saves.
        models.signals.post_save.connect(self.handle_save)
        models.signals.post_delete.connect(self.handle_delete)

        # Use to manage related objects update
        models.signals.m2m_changed.connect(self.handle_m2m_changed)
        models.signals.pre_delete.connect(self.handle_pre_delete)

    def teardown(self):
        # Listen to all model saves.
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)
        models.signals.m2m_changed.disconnect(self.handle_m2m_changed)
        models.signals.pre_delete.disconnect(self.handle_pre_delete)

try:
    from celery import shared_task
except ImportError:
    pass
else:
    class CelerySignalProcessor(RealTimeSignalProcessor):
        """Celery signal processor.

        Allows automatic updates on the index as delayed background tasks using
        Celery.

        NB: We cannot process deletes as background tasks.
        By the time the Celery worker would pick up the delete job, the
        model instance would already deleted. We can get around this by
        setting Celery to use `pickle` and sending the object to the worker,
        but using `pickle` opens the application up to security concerns.
        """

        def handle_save(self, sender, instance, **kwargs):
            """Handle save with a Celery task.

            Given an individual model instance, update the object in the index.
            Update the related objects either.
            """
            pk = instance.pk
            app_label = instance._meta.app_label
            model_name = instance.__class__.__name__

            self.registry_update_task.delay(pk, app_label, model_name)
            self.registry_update_related_task.delay(pk, app_label, model_name)

        def handle_pre_delete(self, sender, instance, **kwargs):
            """Handle removing of instance object from related models instance.
            We need to do this before the real delete otherwise the relation
            doesn't exists anymore and we can't get the related models instance.
            """
            self.prepare_registry_delete_related_task(instance)

        def handle_delete(self, sender, instance, **kwargs):
            """Handle delete.

            Given an individual model instance, delete the object from index.
            """
            self.prepare_registry_delete_task(instance)


        @shared_task()
        def registry_delete_related_task(doc_module, doc_class, object_ids, action):
            """
            A Celery task that fetches the latest data for given object IDs and performs the required indexing action.
            This version uses the custom `get_queryset()` method defined in the document class.

            Instead of deleting the related objects we update it so that the deleted connection between
            the deleted model and the related model is updated into elasticsearch.
            """
            doc_instance = getattr(import_module(doc_module), doc_class)()
            model = doc_instance.django.model

            # Fetch the latest instances from the database
            #object_list = model.objects.filter(pk__in=object_ids).all()
            # Use the custom queryset method if available
            object_list = doc_instance.get_queryset().filter(pk__in=object_ids)
            if not object_list:
                return

            # Generate the bulk update data
            bulk_data = list(doc_instance._get_actions(object_list, action))

            if bulk_data:
                doc_instance._bulk(bulk_data, parallel=True)


        def prepare_registry_delete_related_task(self, instance):
            """
            Collect IDs of related instances before the main instance is deleted and queue these IDs
            for indexing in Elasticsearch through a registry_delete_related_task.
            """
            related_docs = list(registry._get_related_doc(instance))
            if not related_docs:
                return

            for doc_class in related_docs:
                doc_instance = doc_class()
                try:
                    related = doc_instance.get_instances_from_related(instance)
                except ObjectDoesNotExist:
                    related = None

                if related:
                    if isinstance(related, models.Model):
                        object_ids = [related.pk]
                    else:
                        object_ids = [obj.pk for obj in related if hasattr(obj, 'pk')]

                    action = 'index'  # Set the operation as 'index'
                    # Send only the IDs to the task
                    self.registry_delete_related_task.delay(doc_class.__module__, doc_class.__name__, object_ids, action)


        @shared_task()
        def registry_delete_task(doc_module, doc_class, bulk_data):
            """
            Handle the bulk delete data on the registry as a Celery task.
            The different implementations used are due to the difference between delete and update operations. 
            The update operation can re-read the updated data from the database to ensure eventual consistency, 
            but the delete needs to be processed before the database record is deleted to obtain the associated data.
            """
            doc_instance = getattr(import_module(doc_module), doc_class)()
            parallel = True
            doc_instance._bulk(bulk_data, parallel=parallel)


        def prepare_registry_delete_task(self, instance):
            """
            Prepare deletion of the instance itself from Elasticsearch.
            """
            action = 'delete'

            # Find all documents in the registry that are related to the instance's model class
            if instance.__class__ not in registry._models:
                return

            bulk_data = []
            for doc_class in registry._models[instance.__class__]:
                doc_instance = doc_class()  # Create an instance of the document
                if isinstance(instance, models.Model):
                    object_list = [instance]
                else:
                    object_list = instance

                # Assuming get_actions method prepares the correct delete actions for Elasticsearch
                bulk_data.extend(list(doc_instance._get_actions(object_list, action)))

            if bulk_data:
                # Ensure registry_delete_task is prepared to handle bulk deletion
                self.registry_delete_task.delay(doc_instance.__module__, doc_instance.__class__.__name__, bulk_data)


        @shared_task()
        def registry_update_task(pk, app_label, model_name):
            """Handle the update on the registry as a Celery task."""
            try:
                model = apps.get_model(app_label, model_name)
            except LookupError:
                pass
            else:
                try:
                    registry.update(
                        model.objects.get(pk=pk)
                    )
                except ObjectDoesNotExist as e:
                    print(f'Error registry_update_task: {e}')


        @shared_task()
        def registry_update_related_task(pk, app_label, model_name):
            """Handle the related update on the registry as a Celery task."""
            try:
                model = apps.get_model(app_label, model_name)
            except LookupError:
                pass
            else:
                try:
                    registry.update_related(
                        model.objects.get(pk=pk)
                    )
                except ObjectDoesNotExist as e:
                    print(f'Error registry_update_related_task: {e}')
