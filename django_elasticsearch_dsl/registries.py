from django.utils.six import itervalues, iterkeys, iteritems
from collections import defaultdict
from itertools import chain

from .apps import DEDConfig


class DocumentRegistry(object):
    """
    Registry of models classes to a set of Document instances.
    """
    def __init__(self):
        self._indices = defaultdict(set)
        self._models = defaultdict(set)

    def register(self, index, doc):
        """Register the model with the registry"""
        self._indices[index].add(doc)
        self._models[doc._doc_type.model].add(doc)

    def update(self, instance, **kwargs):
        """
        Update all the elasticsearch documents attached to this model (if their
        ignore_signals flag allows it)
        """
        if DEDConfig.autosync_enabled() and instance.__class__ in self._models:
            for doc in self._models[instance.__class__]:
                if not doc._doc_type.ignore_signals:
                    doc.update(instance, **kwargs)

    def delete(self, instance, **kwargs):
        """
        Delete all the elasticsearch documents attached to this model (if their
        ignore_signals flag allows it)
        """
        self.update(instance, action="delete", **kwargs)

    def get_documents(self, models=None):
        """
        Get all documents in the registry or the documents for a list of models
        """
        if models is not None:
            return set(chain(*(self._models[model] for model in models
                               if model in self._models)))
        return set(chain(*itervalues(self._indices)))

    def get_models(self):
        """
        Get all models in the registry
        """
        return set(iterkeys(self._models))

    def get_indices(self, models=None):
        """
        Get all indices in the registry or the indices for a list of models
        """
        if models is not None:
            return set(indice for indice, docs in iteritems(self._indices)
                       for doc in docs if doc._doc_type.model in models)

        return set(iterkeys(self._indices))


registry = DocumentRegistry()
