from copy import deepcopy

from opensearch_dsl import Index as DSLIndex

from .apps import DODConfig
from .registries import registry


class Index(DSLIndex):
    """Creates an index and makes a deep copy of default index settings."""

    def __init__(self, *args, **kwargs):
        super(Index, self).__init__(*args, **kwargs)
        default_index_settings = deepcopy(DODConfig.default_index_settings())
        self.settings(**default_index_settings)

    def document(self, document):
        """Extend to register the document in the global document registry."""
        document = super(Index, self).document(document)
        registry.register_document(document)
        return document

    doc_type = document

    def __str__(self):
        return self._name
