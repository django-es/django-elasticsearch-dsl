from itertools import chain

from collections import defaultdict

from django.core.paginator import Paginator
from django.db.models import Model
from elasticsearch.helpers import bulk
from six import iteritems

from .apps import DEDConfig


class ActionBuffer(object):
    """
    ActionBuffer helps to gather index/delete actions and send them in bulk.
    """

    def __init__(self, registry=None):
        if registry:
            self._registry = registry
        else:
            self._registry = self._get_default_registry()

        self._actions = defaultdict(set)

    def _get_default_registry(self):
        # Import the registry locally to avoid circular dependency.
        from django_elasticsearch_dsl.registries import registry
        return registry

    def add_doc_actions(self, doc_instance, instances, action='index'):
        """
        Add actions to update/delete model(s) for a specific DocType.

        Recommended when doing bulk updates.

        :param doc_instance: The DocType instance to perform actions on.
        :param instances: A model instance, list of models or queryset.
        :param action: What to do with the data (index/delete).
        """
        if isinstance(instances, Model):
            instances = [instances]

        self._actions[doc_instance.connection].add(self._get_actions(
            doc_instance, instances, action=action,
        ))

    def add_model_actions(self, model, action='index'):
        """
        Add actions to update all documents where this model is used.

        :param model: A Model instance.
        :param action: What do do with the documents (index/delete).
        """
        for doc in self._registry.get_documents(model.__class__):
            self.add_doc_actions(doc(), model, action=action)

        for doc in self._registry.get_related_doc(model.__class__):
            doc_instance = doc()

            related = doc_instance.get_instances_from_related(model)

            if related is not None:
                # Don't respect the original action. We just want to sync,
                # not delete.
                self.add_doc_actions(doc_instance, related, action='index')

    def _get_actions(self, doc_type, object_list, action):
        if doc_type._doc_type.queryset_pagination is not None:
            paginator = Paginator(
                object_list, doc_type._doc_type.queryset_pagination
            )
            for page in paginator.page_range:
                for object_instance in paginator.page(page).object_list:
                    yield self._prepare_action(doc_type, object_instance, action)
        else:
            for object_instance in object_list:
                yield self._prepare_action(doc_type, object_instance, action)

    def _prepare_action(self, doc_type, object_instance, action):
        return {
            '_op_type': action,
            '_index': str(doc_type._doc_type.index),
            '_type': doc_type._doc_type.mapping.doc_type,
            '_id': object_instance.pk,
            '_source': (
                doc_type.prepare(object_instance) if action != 'delete' else None
            ),
        }

    def execute(self, connection=None, **kwargs):
        """
        Send the buffered actions to Elasticsearch.

        :param connection: The ES connection to send (leave empty for all).
        :param kwargs: Additional options sent to Elasticsearch.
        """
        if 'refresh' not in kwargs and DEDConfig.auto_refresh_enabled():
            kwargs['refresh'] = True

        if connection:
            return bulk(
                client=connection,
                actions=chain(*self._actions[connection]),
                **kwargs
            )
        else:
            for conn, actions in iteritems(self._actions):
                bulk(client=conn, actions=chain(*actions), **kwargs)

    def __len__(self):
        return len(self._actions)

    def __nonzero__(self):
        return len(self) > 0
