from copy import deepcopy

from elasticsearch.dsl import Index as DSLIndex
from six import python_2_unicode_compatible

from .apps import DEDConfig
from .registries import registry


@python_2_unicode_compatible
class Index(DSLIndex):
    def __init__(self, *args, **kwargs):
        super(Index, self).__init__(*args, **kwargs)
        default_index_settings = deepcopy(DEDConfig.default_index_settings())
        self.settings(**default_index_settings)

    def document(self, document):
        """
        Extend to register the document in the global document registry
        """
        document = super(Index, self).document(document)
        registry.register_document(document)
        return document

    doc_type = document

    def __str__(self):
        return self._name
