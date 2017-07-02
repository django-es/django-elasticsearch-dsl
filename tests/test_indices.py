from unittest import TestCase
from django.db import models
from mock import patch
from django_elasticsearch_dsl.indices import Index
from django_elasticsearch_dsl.documents import DocType
from django_elasticsearch_dsl.registries import DocumentRegistry
from django.conf import settings


class IndexTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        class ModelA(models.Model):
            class Meta:
                app_label = 'test'
        cls.ModelA = ModelA

        class DocA1(DocType):
            class Meta:
                model = cls.ModelA
        cls.DocA1 = DocA1

        class DocA2(DocType):
            class Meta:
                model = cls.ModelA
        cls.DocA2 = DocA2

    def test_documents_add_to_register(self):
        registry = DocumentRegistry()
        with patch('django_elasticsearch_dsl.indices.registry', new=registry):
            index = Index('test')
            index.doc_type(self.DocA1)
            docs = list(registry.get_documents())
            self.assertEqual(len(docs), 1)
            self.assertIsInstance(docs[0], self.DocA1)

            index.doc_type(self.DocA2)
            docs = list(registry.get_documents())
            self.assertEqual(len(docs), 2)
            self.assertIsInstance(docs[0], self.DocA1)
            self.assertIsInstance(docs[1], self.DocA2)

    def test__str__(self):
        index = Index('test')
        self.assertEqual(index.__str__(), 'test')

    def test__init__(self):
        settings.ELASTICSEARCH_DSL_INDEX_SETTINGS = {
            'number_of_replicas': 0,
            'number_of_shards': 2,
        }

        index = Index('test')
        self.assertEqual(index._settings, {
            'number_of_replicas': 0,
            'number_of_shards': 2,
        })

        settings.ELASTICSEARCH_DSL_INDEX_SETTINGS = {}
