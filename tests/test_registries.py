from unittest import TestCase
from mock import Mock
from django_elasticsearch_dsl.registries import DocumentRegistry
from django.conf import settings


class DocumentRegistryTestCase(TestCase):

    class ModelA():
        pass

    class ModelB():
        pass

    class ModelC():
        pass

    def setUp(self):
        self.registry = DocumentRegistry()
        self.index_1 = Mock()
        self.index_2 = Mock()

        self.doc_a1 = Mock()
        self.doc_a1._doc_type.model = self.ModelA
        self.doc_a1._doc_type.ignore_signals = False

        self.doc_a2 = Mock()
        self.doc_a2._doc_type.model = self.ModelA
        self.doc_a2._doc_type.ignore_signals = False

        self.doc_b1 = Mock()
        self.doc_b1._doc_type.model = self.ModelB
        self.doc_b1._doc_type.ignore_signals = False

        self.doc_c1 = Mock()
        self.doc_c1._doc_type.model = self.ModelC
        self.doc_c1._doc_type.ignore_signals = False

        self.registry.register(self.index_1, self.doc_a1)
        self.registry.register(self.index_1, self.doc_a2)
        self.registry.register(self.index_2, self.doc_b1)
        self.registry.register(self.index_1, self.doc_c1)

    def test_empty_registry(self):
        registry = DocumentRegistry()
        self.assertEqual(registry._indices, {})
        self.assertEqual(registry._models, {})

    def test_register(self):
        self.assertEqual(self.registry._models[self.ModelA],
                         set([self.doc_a1, self.doc_a2]))
        self.assertEqual(self.registry._models[self.ModelB],
                         set([self.doc_b1]))

        self.assertEqual(self.registry._indices[self.index_1],
                         set([self.doc_a1, self.doc_a2, self.doc_c1]))
        self.assertEqual(self.registry._indices[self.index_2],
                         set([self.doc_b1]))

    def test_get_models(self):
        self.assertEqual(self.registry.get_models(),
                         set([self.ModelA, self.ModelB, self.ModelC]))

    def test_get_documents(self):
        self.assertEqual(self.registry.get_documents(),
                         set([self.doc_a1, self.doc_a2,
                              self.doc_b1, self.doc_c1]))

    def test_get_documents_by_model(self):
        self.assertEqual(self.registry.get_documents([self.ModelA]),
                         set([self.doc_a1, self.doc_a2]))

    def test_get_documents_by_unregister_model(self):
        ModelC = Mock()
        self.assertFalse(self.registry.get_documents([ModelC]))

    def test_get_indices(self):
        self.assertEqual(self.registry.get_indices(),
                         set([self.index_1, self.index_2]))

    def test_get_indices_by_model(self):
        self.assertEqual(self.registry.get_indices([self.ModelA]),
                         set([self.index_1]))

    def test_get_indices_by_unregister_model(self):
        ModelC = Mock()
        self.assertFalse(self.registry.get_indices([ModelC]))

    def test_update_instance(self):
        doc_a3 = Mock()
        doc_a3._doc_type.model = self.ModelA
        doc_a3._doc_type.ignore_signals = True

        self.registry.register(self.index_1, doc_a3)

        instance = self.ModelA()
        self.registry.update(instance)

        self.assertFalse(doc_a3.update.called)
        self.assertFalse(self.doc_b1.update.called)
        self.doc_a1.update.assert_called_once_with(instance)
        self.doc_a2.update.assert_called_once_with(instance)

    def test_delete_instance(self):
        doc_a3 = Mock()
        doc_a3._doc_type.model = self.ModelA
        doc_a3._doc_type.ignore_signals = True

        self.registry.register(self.index_1, doc_a3)

        instance = self.ModelA()
        self.registry.delete(instance)

        self.assertFalse(doc_a3.update.called)
        self.assertFalse(self.doc_b1.update.called)
        self.doc_a1.update.assert_called_once_with(instance, action='delete')
        self.doc_a2.update.assert_called_once_with(instance, action='delete')

    def test_autosync(self):
        settings.ELASTICSEARCH_DSL_AUTOSYNC = False

        instance = self.ModelA()
        self.registry.update(instance)
        self.assertFalse(self.doc_a1.update.called)

        settings.ELASTICSEARCH_DSL_AUTOSYNC = True
