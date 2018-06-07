# encoding: utf-8
"""
A convenient way to attach django-elasticsearch-dsl to Django's signals and
cause things to index.
"""

from __future__ import absolute_import

import logging

from django.db import models
from django.conf import settings

from elasticsearch.exceptions import ElasticsearchException
from elasticsearch_dsl.exceptions import ElasticsearchDslException

from .registries import registry


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

LOG_ERRORS = getattr(settings, 'ELASTICSEARCH_DSL_AUTOSYNC_LOG_ERRORS', False)


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
        try:
            registry.update(instance)
            registry.update_related(instance)

        except (ElasticsearchException, ElasticsearchDslException):
            if not LOG_ERRORS:
                raise
            LOGGER.exception('Error during auto-sync save, continuing')

    def handle_pre_delete(self, sender, instance, **kwargs):
        """Handle removing of instance object from related models instance.
        We need to do this before the real delete otherwise the relation
        doesn't exists anymore and we can't get the related models instance.
        """
        try:
            registry.delete_related(instance)

        except (ElasticsearchException, ElasticsearchDslException):
            if not LOG_ERRORS:
                raise
            LOGGER.exception('Error during auto-sync pre-delete, continuing')

    def handle_delete(self, sender, instance, **kwargs):
        """Handle delete.

        Given an individual model instance, delete the object from index.
        """
        try:
            registry.delete(instance)

        except Exception:
            if not LOG_ERRORS:
                # Preserve functionality, don't ever raise during deletion, but
                # optionally log.
                return
            LOGGER.exception('Error during auto-sync delete, continuing')


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
