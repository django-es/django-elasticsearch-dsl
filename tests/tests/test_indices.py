from unittest import TestCase
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from django_opensearch_dsl.indices import Index
from django_opensearch_dsl.registries import DocumentRegistry

from .fixtures import WithFixturesMixin


class IndexTestCase(WithFixturesMixin, TestCase):
    def setUp(self):
        self.registry = DocumentRegistry()

    def test_documents_add_to_register(self):
        registry = self.registry
        with patch("django_opensearch_dsl.indices.registry", new=registry):
            index = Index("test")
            doc_a1 = self._generate_doc_mock(self.ModelA)
            index.document(doc_a1)
            indices = list(registry.get_indices())
            self.assertEqual(len(indices), 1)
            self.assertEqual(indices[0], index)

    def test__str__(self):
        index = Index("test")
        self.assertEqual(index.__str__(), "test")

    @override_settings(
        OPENSEARCH_DSL_INDEX_SETTINGS={
            "number_of_replicas": 0,
            "number_of_shards": 2,
        }
    )
    def test__init__(self):
        index = Index("test")
        self.assertEqual(
            index._settings,
            {
                "number_of_replicas": 0,
                "number_of_shards": 2,
            },
        )
