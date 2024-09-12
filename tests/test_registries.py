from mock import Mock
from unittest import TestCase

from django.conf import settings

from django_elasticsearch_dsl import Index
from django_elasticsearch_dsl.registries import DocumentRegistry

from .fixtures import WithFixturesMixin


class DocumentRegistryTestCase(WithFixturesMixin, TestCase):
    def setUp(self):
        self.registry = DocumentRegistry()
        self.index_1 = Index(name='index_1')
        self.index_2 = Index(name='index_2')

        self.doc_a1 = self._generate_doc_mock(self.ModelA, self.index_1)
        self.doc_a2 = self._generate_doc_mock(self.ModelA, self.index_1)
        self.doc_b1 = self._generate_doc_mock(self.ModelB, self.index_2)
        self.doc_c1 = self._generate_doc_mock(self.ModelC, self.index_1)

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
        doc_a3 = self._generate_doc_mock(
            self.ModelA, self.index_1, _ignore_signals=True
        )

        instance = self.ModelA()
        self.registry.update(instance)

        self.assertFalse(doc_a3.update.called)
        self.assertFalse(self.doc_b1.update.called)
        self.doc_a1.update.assert_called_once_with(instance)
        self.doc_a2.update.assert_called_once_with(instance)

    def test_update_related_instances(self):
        doc_d1 = self._generate_doc_mock(
            self.ModelD, self.index_1,
            _related_models=[self.ModelE, self.ModelB]
        )
        doc_d2 = self._generate_doc_mock(
            self.ModelD, self.index_1, _related_models=[self.ModelE]
        )

        instance_e = self.ModelE()
        instance_b = self.ModelB()
        related_instance = self.ModelD()

        doc_d2.get_instances_from_related.return_value = related_instance
        doc_d1.get_instances_from_related.return_value = related_instance
        self.registry.update_related(instance_e)

        doc_d1.get_instances_from_related.assert_called_once_with(instance_e)
        doc_d1.update.assert_called_once_with(related_instance)
        doc_d2.get_instances_from_related.assert_called_once_with(instance_e)
        doc_d2.update.assert_called_once_with(related_instance)

        doc_d1.get_instances_from_related.reset_mock()
        doc_d1.update.reset_mock()
        doc_d2.get_instances_from_related.reset_mock()
        doc_d2.update.reset_mock()

        self.registry.update_related(instance_b)
        doc_d1.get_instances_from_related.assert_called_once_with(instance_b)
        doc_d1.update.assert_called_once_with(related_instance)
        doc_d2.get_instances_from_related.assert_not_called()
        doc_d2.update.assert_not_called()

    def test_update_related_instances_not_defined(self):
        doc_d1 = self._generate_doc_mock(_model=self.ModelD, index=self.index_1,
                                         _related_models=[self.ModelE])

        instance = self.ModelE()

        doc_d1.get_instances_from_related.return_value = None
        self.registry.update_related(instance)

        doc_d1.get_instances_from_related.assert_called_once_with(instance)
        doc_d1.update.assert_not_called()

    def test_delete_instance(self):
        doc_a3 = self._generate_doc_mock(
            self.ModelA, self.index_1, _ignore_signals=True
        )

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


class DocumentRegistryBulkOperationsTestCase(WithFixturesMixin, TestCase):
    """
    Test case for working with bulk operations.
    """

    def setUp(self) -> None:
        self.registry = DocumentRegistry()
        self.index_1 = Index(name='index_1')
        self.index_2 = Index(name='index_2')

        self.doc_a1 = self._generate_doc_mock(self.ModelA, self.index_1)
        self.doc_a2 = self._generate_doc_mock(self.ModelA, self.index_1)
        self.doc_b1 = self._generate_doc_mock(self.ModelB, self.index_2)
        self.doc_c1 = self._generate_doc_mock(self.ModelC, self.index_1)

    def test_update_instances(self):
        """
        Checking for `update`.
        """
        doc_a3 = self._generate_doc_mock(
            self.ModelA, self.index_1, _ignore_signals=True
        )

        instances = self.ModelA.objects.all()
        self.registry.update(instances)

        self.assertFalse(doc_a3.update.called)
        self.assertFalse(self.doc_b1.update.called)
        self.doc_a1.update.assert_called_once_with(instances)
        self.doc_a2.update.assert_called_once_with(instances)

    def test_update_instances_as_list(self):
        """
        Checking for `update` where instances is list.
        """
        doc_a3 = self._generate_doc_mock(
            self.ModelA, self.index_1, _ignore_signals=True
        )

        instances = [self.ModelA()]
        self.registry.update(instances)

        self.assertFalse(doc_a3.update.called)
        self.assertFalse(self.doc_b1.update.called)
        self.doc_a1.update.assert_called_once_with(instances)
        self.doc_a2.update.assert_called_once_with(instances)

    def test_update_related_instances(self):
        """
        Checking the correct call of the get function from
        related objects.
        """
        doc_d1 = self._generate_doc_mock(
            self.ModelD, self.index_1,
            _related_models=[self.ModelE, self.ModelB]
        )
        doc_d2 = self._generate_doc_mock(
            self.ModelD, self.index_1, _related_models=[self.ModelE]
        )

        instances_e = self.ModelE.objects.all()
        instances_b = self.ModelB.objects.all()
        related_instances = self.ModelD.objects.all()

        doc_d2.get_instances_from_many_related.return_value = related_instances
        doc_d1.get_instances_from_many_related.return_value = related_instances
        self.registry.update_related(instances_e, many=True)

        doc_d1.get_instances_from_many_related.assert_called_once_with(
            self.ModelE, instances_e
        )
        doc_d1.get_instances_from_related.assert_not_called()
        doc_d1.update.assert_called_once_with(related_instances)
        doc_d2.get_instances_from_many_related.assert_called_once_with(
            self.ModelE, instances_e
        )
        doc_d2.get_instances_from_related.assert_not_called()
        doc_d2.update.assert_called_once_with(related_instances)

        doc_d1.get_instances_from_many_related.reset_mock()
        doc_d1.update.reset_mock()
        doc_d2.get_instances_from_many_related.reset_mock()
        doc_d2.update.reset_mock()

        self.registry.update_related(instances_b, many=True)
        doc_d1.get_instances_from_many_related.assert_called_once_with(
            self.ModelB, instances_b
        )
        doc_d1.get_instances_from_related.assert_not_called()
        doc_d1.update.assert_called_once_with(related_instances)
        doc_d2.get_instances_from_many_related.assert_not_called()
        doc_d2.get_instances_from_related.assert_not_called()
        doc_d2.update.assert_not_called()

    def test_update_related_instances_not_defined(self):
        """
        Checking the correct call, if the function of
        getting objects from related is not defined.
        """
        doc_d1 = self._generate_doc_mock(_model=self.ModelD, index=self.index_1,
                                         _related_models=[self.ModelE])

        instances = self.ModelE.objects.all()

        doc_d1.get_instances_from_related.return_value = None
        self.registry.update_related(instances)

        doc_d1.get_instances_from_related.assert_called_once_with(instances)
        doc_d1.update.assert_not_called()

    def test_delete_instances(self):
        """
        Checking the correct call `delete`.
        """
        doc_a3 = self._generate_doc_mock(
            self.ModelA, self.index_1, _ignore_signals=True
        )

        instances = self.ModelA.objects.all()
        self.registry.delete(instances)

        self.assertFalse(doc_a3.update.called)
        self.assertFalse(self.doc_b1.update.called)
        self.doc_a1.update.assert_called_once_with(instances, action='delete')
        self.doc_a2.update.assert_called_once_with(instances, action='delete')

    def test_delete_related_instances(self):
        """
        Checking the correct call `delete_related`.

        The signature is similar to `update_related`.
        """
        doc_d1 = self._generate_doc_mock(
            self.ModelD, self.index_1,
            _related_models=[self.ModelE, self.ModelB]
        )
        doc_d2 = self._generate_doc_mock(
            self.ModelD, self.index_1, _related_models=[self.ModelE]
        )

        instances_e = self.ModelE.objects.all()
        instances_b = self.ModelB.objects.all()
        related_instances = self.ModelD.objects.all()

        doc_d2.get_instances_from_many_related.return_value = related_instances
        doc_d1.get_instances_from_many_related.return_value = related_instances
        self.registry.delete_related(instances_e, many=True)

        doc_d1.get_instances_from_many_related.assert_called_once_with(
            self.ModelE, instances_e
        )
        doc_d1.get_instances_from_related.assert_not_called()
        doc_d1.update.assert_called_once_with(related_instances)
        doc_d2.get_instances_from_many_related.assert_called_once_with(
            self.ModelE, instances_e
        )
        doc_d2.get_instances_from_related.assert_not_called()
        doc_d2.update.assert_called_once_with(related_instances)

        doc_d1.get_instances_from_many_related.reset_mock()
        doc_d1.update.reset_mock()
        doc_d2.get_instances_from_many_related.reset_mock()
        doc_d2.update.reset_mock()

        self.registry.delete_related(instances_b, many=True)
        doc_d1.get_instances_from_many_related.assert_called_once_with(
            self.ModelB, instances_b
        )
        doc_d1.get_instances_from_related.assert_not_called()
        doc_d1.update.assert_called_once_with(related_instances)
        doc_d2.get_instances_from_many_related.assert_not_called()
        doc_d2.get_instances_from_related.assert_not_called()
        doc_d2.update.assert_not_called()

    def test_autosync(self):
        settings.ELASTICSEARCH_DSL_AUTOSYNC = False

        instances = self.ModelA.objects.all()
        self.registry.update(instances)
        self.assertFalse(self.doc_a1.update.called)

        settings.ELASTICSEARCH_DSL_AUTOSYNC = True
