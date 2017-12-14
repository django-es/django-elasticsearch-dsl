# encoding: utf-8
"""
A convenient way to attach django-elasticsearch-dsl to Django's signals and
cause things to index.
"""

from __future__ import absolute_import

from django.db import models

from .actions import ActionBuffer
from .registries import registry


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
        actions = ActionBuffer(registry=registry)

        for doc in registry.get_documents(instance.__class__):
            if not doc._doc_type.ignore_signals:
                actions.add_doc_actions(doc(), instance, 'index')

        for doc in registry.get_related_doc(instance.__class__):
            if not doc._doc_type.ignore_signals:
                doc_instance = doc()
                related = doc_instance.get_instances_from_related(instance)
                if related is not None:
                    actions.add_doc_actions(doc_instance, related, 'index')

        return actions.execute()

    def handle_pre_delete(self, sender, instance, **kwargs):
        """Handle removing of instance object from related models instance.
        We need to do this before the real delete otherwise the relation
        doesn't exists anymore and we can't get the related models instance.
        """
        actions = ActionBuffer(registry=registry)

        for doc in registry.get_related_doc(instance.__class__):
            if not doc._doc_type.ignore_signals:
                doc_instance = doc(related_instance_to_ignore=instance)
                related = doc_instance.get_instances_from_related(instance)
                if related is not None:
                    actions.add_doc_actions(doc_instance, related, 'index')

        return actions.execute()

    def handle_delete(self, sender, instance, **kwargs):
        """Handle delete.

        Given an individual model instance, delete the object from index.
        """
        actions = ActionBuffer(registry=registry)

        for doc in registry.get_documents(instance.__class__):
            if not doc._doc_type.ignore_signals:
                actions.add_doc_actions(doc(), instance, 'delete')

        return actions.execute()


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
