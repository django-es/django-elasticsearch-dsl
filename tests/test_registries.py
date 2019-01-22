from mock import Mock, patch
from unittest import TestCase

from django_elasticsearch_dsl.registries import DocumentRegistry
from tests import fixtures


class DocumentRegistryTestCase(fixtures.WithFixturesMixin, TestCase):
    def setUp(self):
        super(DocumentRegistryTestCase, self).setUp()

        self.registry.register(self.index_1, fixtures.DocA1)
        self.registry.register(self.index_1, fixtures.DocA2)
        self.registry.register(self.index_2, fixtures.DocB1)
        self.registry.register(self.index_1, fixtures.DocC1)
        self.registry.register(self.index_1, fixtures.DocD1)
        self.registry.register(self.index_1, fixtures.DocD2)

        self.buffer_patcher = patch(
            'django_elasticsearch_dsl.registries.ActionBuffer')
        self.action_buffer = self.buffer_patcher.start()
        self.action_buffer().add_model_actions = Mock()
        self.action_buffer().execute = Mock()

    def tearDown(self):
        self.buffer_patcher.stop()

    def test_empty_registry(self):
        registry = DocumentRegistry()
        self.assertEqual(registry._indices, {})
        self.assertEqual(registry._models, {})

    def test_register(self):
        self.assertEqual(
            self.registry._models[fixtures.ModelA],
            {fixtures.DocA1, fixtures.DocA2}
        )
        self.assertEqual(
            self.registry._models[fixtures.ModelB],
            {fixtures.DocB1}
        )

        self.assertEqual(
            self.registry._indices[self.index_1],
            {fixtures.DocA1, fixtures.DocA2, fixtures.DocC1, fixtures.DocD1,
             fixtures.DocD2}
        )
        self.assertEqual(
            self.registry._indices[self.index_2],
            {fixtures.DocB1}
        )

    def test_get_models(self):
        self.assertEqual(
            self.registry.get_models(),
            {fixtures.ModelA, fixtures.ModelB, fixtures.ModelC,
             fixtures.ModelD}
        )

    def test_get_documents(self):
        self.assertEqual(
            self.registry.get_documents(),
            {fixtures.DocA1, fixtures.DocA2, fixtures.DocB1,
             fixtures.DocC1, fixtures.DocD1, fixtures.DocD2}
        )

    def test_get_documents_by_model(self):
        self.assertEqual(
            self.registry.get_documents([fixtures.ModelA]),
            {fixtures.DocA1, fixtures.DocA2}
        )

    def test_get_documents_by_unregister_model(self):
        ModelC = Mock()
        self.assertFalse(self.registry.get_documents([ModelC]))

    def test_get_indices(self):
        self.assertEqual(
            self.registry.get_indices(),
            {self.index_1, self.index_2}
        )

    def test_get_indices_by_model(self):
        self.assertEqual(
            self.registry.get_indices([fixtures.ModelA]),
            {self.index_1}
        )

    def test_get_indices_by_unregister_model(self):
        ModelC = Mock()
        self.assertFalse(self.registry.get_indices([ModelC]))

    def test_update_instance(self):
        instance = fixtures.ModelA

        self.registry.update(instance)

        self.action_buffer().add_model_actions.assert_called_with(
            instance, 'index'
        )
        self.action_buffer().execute.assert_called_once()

    def test_update_signals_disabled(self):
        instance = fixtures.ModelC()

        self.registry.update(instance)

        self.action_buffer().add_model_actions.assert_called_with(
            instance, 'index'
        )
        self.action_buffer().execute.assert_called_once()

    def test_get_related_doc(self):
        results = list(self.registry.get_related_doc(fixtures.ModelE))
        self.assertEqual(set([fixtures.DocD1, fixtures.DocD2]), set(results))

    def test_delete_instance(self):
        instance = fixtures.ModelB()

        self.registry.delete(instance)

        self.action_buffer().add_model_actions.assert_called_with(
            instance, 'delete'
        )

        self.action_buffer().execute.assert_called_once()
