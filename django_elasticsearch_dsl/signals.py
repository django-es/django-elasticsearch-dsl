# encoding: utf-8
"""
A convenient way to attach django-elasticsearch-dsl to Django's signals and
cause things to index.
"""

from __future__ import absolute_import

from django.db import models

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
        if action in [
            'post_add', 'pre_remove', 'pre_clear', 'post_remove', 'post_clear'
        ]:
            self.handle_save(sender, instance=instance)

    def handle_save(self, sender, **kwargs):
        """Handle save.

        Given an individual model instance, update the object in the index.
        """
        instance = kwargs['instance']
        registry.update(instance)

    def handle_delete(self, sender, **kwargs):
        """Handle delete.

        Given an individual model instance, delete the object from index.
        """
        instance = kwargs['instance']
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
        models.signals.m2m_changed.connect(self.handle_m2m_changed)

    def teardown(self):
        # Listen to all model saves.
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)
        models.signals.m2m_changed.disconnect(self.handle_m2m_changed)
