from mock import DEFAULT, Mock, patch
from unittest import TestCase
from django.utils.six import StringIO
from django.db import models
from django.core.management.base import CommandError
from django.core.management import call_command
from django_elasticsearch_dsl.registries import DocumentRegistry
from django_elasticsearch_dsl.management.commands.search_index import Command


class SearchIndexTestCase(TestCase):
    class ModelA(models.Model):
        class Meta:
            app_label = 'foo'

    class ModelB(models.Model):
        class Meta:
            app_label = 'foo'

    class ModelC(models.Model):
        class Meta:
            app_label = 'bar'

    def setUp(self):
        self.out = StringIO()
        self.registry = DocumentRegistry()
        self.index_a = Mock()
        self.index_b = Mock()

        self.doc_a1 = Mock()
        self.doc_a1._doc_type.model = self.ModelA
        self.doc_a1._doc_type.related_models = []
        self.doc_a1_qs = Mock()
        self.doc_a1.get_queryset = Mock(return_value=self.doc_a1_qs)

        self.doc_a2 = Mock()
        self.doc_a2._doc_type.model = self.ModelA
        self.doc_a2._doc_type.related_models = []
        self.doc_a2_qs = Mock()
        self.doc_a2.get_queryset = Mock(return_value=self.doc_a2_qs)

        self.doc_b1 = Mock()
        self.doc_b1._doc_type.model = self.ModelB
        self.doc_b1._doc_type.related_models = []
        self.doc_b1_qs = Mock()
        self.doc_b1.get_queryset = Mock(return_value=self.doc_b1_qs)

        self.doc_c1 = Mock()
        self.doc_c1._doc_type.model = self.ModelC
        self.doc_c1._doc_type.related_models = []
        self.doc_c1_qs = Mock()
        self.doc_c1.get_queryset = Mock(return_value=self.doc_c1_qs)

        self.registry.register(self.index_a, self.doc_a1)
        self.registry.register(self.index_a, self.doc_a2)
        self.registry.register(self.index_a, self.doc_b1)
        self.registry.register(self.index_b, self.doc_c1)

    def test_get_models(self):
        cmd = Command()
        with patch(
            'django_elasticsearch_dsl.management.commands.'
            'search_index.registry',
            self.registry
        ):
            self.assertEqual(
                cmd._get_models(['foo']),
                set([self.ModelA, self.ModelB])
            )

            self.assertEqual(
                cmd._get_models(['foo', 'bar.ModelC']),
                set([self.ModelA, self.ModelB, self.ModelC])
            )

            self.assertEqual(
                cmd._get_models([]),
                set([self.ModelA, self.ModelB, self.ModelC])
            )
            with self.assertRaises(CommandError):
                cmd._get_models(['unknown'])

    def test_no_action_error(self):
        cmd = Command()
        with self.assertRaises(CommandError):
            cmd.handle(action="")

    def test_delete_foo_index(self):

        with patch(
            'django_elasticsearch_dsl.management.commands.'
            'search_index.registry',
            self.registry
        ):
            with patch(
                'django_elasticsearch_dsl.management.commands.'
                'search_index.input',
                Mock(return_value="y")
            ):
                call_command('search_index', stdout=self.out,
                             action='delete', models=['foo'])
                self.index_a.delete.assert_called_once()
                self.assertFalse(self.index_b.delete.called)

    def test_force_delete_all_indices(self):

        with patch(
            'django_elasticsearch_dsl.management.commands.'
            'search_index.registry',
            self.registry
        ):
            call_command('search_index', stdout=self.out,
                         action='delete', force=True)
            self.index_a.delete.assert_called_once()
            self.index_b.delete.assert_called_once()

    def test_force_delete_bar_model_c_index(self):

        with patch(
            'django_elasticsearch_dsl.management.commands.'
            'search_index.registry',
            self.registry
        ):
            call_command('search_index', stdout=self.out,
                         models=['bar.ModelC'],
                         action='delete', force=True)
            self.index_b.delete.assert_called_once()
            self.assertFalse(self.index_a.delete.called)

    def test_create_all_indices(self):

        with patch(
            'django_elasticsearch_dsl.management.commands.'
            'search_index.registry',
            self.registry
        ):
            call_command('search_index', stdout=self.out, action='create')
            self.index_a.create.assert_called_once()
            self.index_b.create.assert_called_once()

    def test_populate_all_doc_type(self):

        with patch(
            'django_elasticsearch_dsl.management.commands.'
            'search_index.registry',
            self.registry
        ):
            call_command('search_index', stdout=self.out, action='populate')
            self.doc_a1.get_queryset.assert_called_once()
            self.doc_a1.update.assert_called_once_with(self.doc_a1_qs)
            self.doc_a2.get_queryset.assert_called_once()
            self.doc_a2.update.assert_called_once_with(self.doc_a2_qs)
            self.doc_b1.get_queryset.assert_called_once()
            self.doc_b1.update.assert_called_once_with(self.doc_b1_qs)
            self.doc_c1.get_queryset.assert_called_once()
            self.doc_c1.update.assert_called_once_with(self.doc_c1_qs)

    def test_rebuild_indices(self):

        with patch.multiple(
            Command, _create=DEFAULT, _delete=DEFAULT, _populate=DEFAULT
        ) as handles:
            handles['_delete'].return_value = True
            call_command('search_index', stdout=self.out, action='rebuild')
            handles['_delete'].assert_called()
            handles['_create'].assert_called()
            handles['_populate'].assert_called()

    def test_rebuild_indices_aborted(self):

        with patch.multiple(
            Command, _create=DEFAULT, _delete=DEFAULT, _populate=DEFAULT
        ) as handles:
            handles['_delete'].return_value = False
            call_command('search_index', stdout=self.out, action='rebuild')
            handles['_delete'].assert_called()
            handles['_create'].assert_not_called()
            handles['_populate'].assert_not_called()
