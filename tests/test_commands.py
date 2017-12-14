from mock import DEFAULT, Mock, patch
from unittest import TestCase

from django.core.management.base import CommandError
from django.core.management import call_command
from django.utils.six import StringIO

from django_elasticsearch_dsl.management.commands.search_index import Command
from tests import fixtures


class SearchIndexTestCase(fixtures.WithFixturesMixin, TestCase):
    def setUp(self):
        super(SearchIndexTestCase, self).setUp()
        self.index_1 = Mock()
        self.index_2 = Mock()

        self.out = StringIO()

        self.registry.register(self.index_1, fixtures.DocA1)
        self.registry.register(self.index_1, fixtures.DocA2)
        self.registry.register(self.index_1, fixtures.DocB1)
        self.registry.register(self.index_2, fixtures.DocC1)
        self.registry.register(self.index_1, fixtures.DocD1)

        self.registry_patcher = patch(
            'django_elasticsearch_dsl.management.commands.'
            'search_index.registry', self.registry
        )
        self.registry_patcher.start()

    def tearDown(self):
        self.registry_patcher.stop()

    def test_get_models(self):
        cmd = Command()

        self.assertEqual(
            cmd._get_models(['foo']),
            {fixtures.ModelA, fixtures.ModelB}
        )

        self.assertEqual(
            cmd._get_models(['foo', 'bar.ModelC']),
            {fixtures.ModelA, fixtures.ModelB, fixtures.ModelC}
        )

        self.assertEqual(
            cmd._get_models([]),
            {fixtures.ModelA, fixtures.ModelB, fixtures.ModelC, fixtures.ModelD}
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
            'search_index.input',
            Mock(return_value="y")
        ):
            call_command('search_index', stdout=self.out,
                         action='delete', models=['foo'])
            self.index_1.delete.assert_called_once()
            self.assertFalse(self.index_2.delete.called)

    def test_force_delete_all_indices(self):
        call_command('search_index', stdout=self.out,
                     action='delete', force=True)
        self.index_1.delete.assert_called_once()
        self.index_2.delete.assert_called_once()

    def test_force_delete_bar_model_c_index(self):
        call_command('search_index', stdout=self.out,
                     models=['bar.ModelC'], action='delete', force=True)
        self.index_2.delete.assert_called_once()
        self.assertFalse(self.index_1.delete.called)

    def test_create_all_indices(self):
        call_command('search_index', stdout=self.out, action='create')
        self.index_1.create.assert_called_once()
        self.index_2.create.assert_called_once()

    def test_populate_all_doc_type(self):
        call_command('search_index', stdout=self.out, action='populate')
        fixtures.DocA1.get_queryset.assert_called_once()
        fixtures.DocA1.update.assert_called_once_with(
            fixtures.DocA1.get_queryset()
        )

        fixtures.DocA2.get_queryset.assert_called_once()
        fixtures.DocA2.update.assert_called_once_with(
            fixtures.DocA2.get_queryset()
        )

        fixtures.DocB1.get_queryset.assert_called_once()
        fixtures.DocB1.update.assert_called_once_with(
            fixtures.DocB1.get_queryset()
        )

        fixtures.DocC1.get_queryset.assert_called_once()
        fixtures.DocC1.update.assert_called_once_with(
            fixtures.DocC1.get_queryset()
        )

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
