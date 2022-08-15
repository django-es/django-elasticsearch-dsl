from unittest import mock
from unittest.mock import Mock
from unittest import TestCase

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.test import override_settings

from django_opensearch_dsl.registries import DocumentRegistry
from django_opensearch_dsl.indices import Index

from .fixtures import WithFixturesMixin


class DocumentRegistryTestCase(WithFixturesMixin, TestCase):
    def setUp(self):
        self.registry = DocumentRegistry()
        self.index_1 = Index(name="index_1")
        self.index_2 = Index(name="index_2")

        self.doc_a1 = self._generate_doc_mock(self.ModelA, self.index_1)
        self.doc_a2 = self._generate_doc_mock(self.ModelA, self.index_1)
        self.doc_b1 = self._generate_doc_mock(self.ModelB, self.index_2)
        self.doc_c1 = self._generate_doc_mock(self.ModelC, self.index_1)
        self.doc_d1 = self._generate_doc_mock(self.ModelD, self.index_1, _related_models=[self.ModelE])
        self.doc_e1 = self._generate_doc_mock(self.ModelE, self.index_1)

    def test_empty_registry(self):
        registry = DocumentRegistry()
        self.assertEqual(registry._indices, {})
        self.assertEqual(registry._models, {})

    def test_register(self):
        self.assertEqual(self.registry._models[self.ModelA], set([self.doc_a1, self.doc_a2]))
        self.assertEqual(self.registry._models[self.ModelB], set([self.doc_b1]))

        self.assertEqual(
            self.registry._indices[self.index_1], set([self.doc_a1, self.doc_a2, self.doc_c1, self.doc_d1, self.doc_e1])
        )
        self.assertEqual(self.registry._indices[self.index_2], set([self.doc_b1]))

    def test_register_with_related_models(self):
        self.assertEqual(self.registry._related_models[self.ModelE], set([self.ModelD]))

    def test_get_related_doc(self):
        instance = self.ModelE()
        related_set = set()
        for doc in self.registry._get_related_doc(instance):
            related_set.add(doc)
        self.assertEqual(related_set, set([self.doc_d1]))

    def test_get_indices(self):
        self.assertEqual(self.registry.get_indices(), set([self.index_1, self.index_2]))

    def test_get_indices_by_model(self):
        self.assertEqual(self.registry.get_indices([self.ModelA]), set([self.index_1]))

    def test_get_indices_by_unregister_model(self):
        ModelC = Mock()
        self.assertFalse(self.registry.get_indices([ModelC]))

    def test_update_instance(self):
        doc_a3 = self._generate_doc_mock(self.ModelA, self.index_1, _ignore_signals=True)

        instance = self.ModelA()
        self.registry.update(instance)

        self.assertFalse(doc_a3.update.called)
        self.assertFalse(self.doc_b1.update.called)
        self.doc_a1.update.assert_called_once_with(instance, "index")
        self.doc_a2.update.assert_called_once_with(instance, "index")

    def test_update_related_instances(self):
        doc_d1 = self._generate_doc_mock(self.ModelD, self.index_1, _related_models=[self.ModelE, self.ModelB])
        doc_d2 = self._generate_doc_mock(self.ModelD, self.index_1, _related_models=[self.ModelE])

        instance_e = self.ModelE()
        instance_b = self.ModelB()
        related_instance = self.ModelD()

        doc_d2.get_instances_from_related.return_value = related_instance
        doc_d1.get_instances_from_related.return_value = related_instance
        self.registry.update_related(instance_e)

        doc_d1.get_instances_from_related.assert_called_once_with(instance_e)
        doc_d1.update.assert_called_once_with(related_instance, "index")
        doc_d2.get_instances_from_related.assert_called_once_with(instance_e)
        doc_d2.update.assert_called_once_with(related_instance, "index")

        doc_d1.get_instances_from_related.reset_mock()
        doc_d1.update.reset_mock()
        doc_d2.get_instances_from_related.reset_mock()
        doc_d2.update.reset_mock()

        self.registry.update_related(instance_b)
        doc_d1.get_instances_from_related.assert_called_once_with(instance_b)
        doc_d1.update.assert_called_once_with(related_instance, "index")
        doc_d2.get_instances_from_related.assert_not_called()
        doc_d2.update.assert_not_called()

    def test_update_related_instances_not_defined(self):
        doc_d1 = self._generate_doc_mock(_model=self.ModelD, index=self.index_1, _related_models=[self.ModelE])

        instance = self.ModelE()

        doc_d1.get_instances_from_related.side_effect = ObjectDoesNotExist(Mock(return_value=None))
        self.registry.update_related(instance)

        doc_d1.get_instances_from_related.assert_called_once_with(instance)
        doc_d1.update.assert_not_called()

    def test_delete_instance(self):
        doc_a3 = self._generate_doc_mock(self.ModelA, self.index_1, _ignore_signals=True)

        instance = self.ModelA()
        self.registry.delete(instance)

        self.assertFalse(doc_a3.update.called)
        self.assertFalse(self.doc_b1.update.called)
        self.doc_a1.update.assert_called_once_with(instance, "delete")
        self.doc_a2.update.assert_called_once_with(instance, "delete")

    def test_delete_related_instance(self):
        """
        Test that update is called when related_instance is defined.

        doc_d1 is a related doc for instance. If we call delete_related on
        instance, then update should be called with related_instance.
        """
        doc_d1 = self._generate_doc_mock(self.ModelD, self.index_1, _related_models=[self.ModelE])

        instance = self.ModelE()
        related_instance = self.ModelD()

        doc_d1.get_instances_from_related.return_value = related_instance
        self.registry.delete_related(instance)

        doc_d1.get_instances_from_related.assert_called_once_with(instance)
        doc_d1.update.assert_called_once_with(related_instance, "index")

    def test_delete_related_instance_not_defined(self):
        """
        Test that update is not called if related not defined.

        If we try to call delete_related on instance when
        get_instances_from_related returns None on doc_d1, then update
        should not be called on doc_d1.
        """
        doc_d1 = self._generate_doc_mock(_model=self.ModelD, index=self.index_1, _related_models=[self.ModelE])

        instance = self.ModelE()

        doc_d1.get_instances_from_related.side_effect = ObjectDoesNotExist(Mock(return_value=None))
        self.registry.delete_related(instance)

        doc_d1.get_instances_from_related.assert_called_once_with(instance)
        doc_d1.update.assert_not_called()

    @mock.patch("django_opensearch_dsl.apps.DODConfig.autosync_enabled")
    def test_delete_related_autosync_disabled(self, autosync_mock):
        """If autosync is disabled, delete_related should just return."""

        autosync_mock.return_value = False

        doc_d1 = self._generate_doc_mock(self.ModelD, self.index_1, _related_models=[self.ModelE])

        instance = self.ModelE()

        doc_d1.get_instances_from_related.return_value = None
        self.registry.delete_related(instance)

        doc_d1.get_instances_from_related.assert_not_called()
        doc_d1.update.assert_not_called()

    @override_settings(OPENSEARCH_DSL_AUTOSYNC=False)
    def test_autosync(self):
        instance = self.ModelA()
        self.registry.update(instance)
        self.assertFalse(self.doc_a1.update.called)
