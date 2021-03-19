from mock import DEFAULT, Mock, patch
from unittest import TestCase

from django.core.management.base import CommandError
from django.core.management import call_command
from six import StringIO

from django_elasticsearch_dsl import Index
from django_elasticsearch_dsl.management.commands.search_index import Command
from django_elasticsearch_dsl.registries import DocumentRegistry

from .fixtures import WithFixturesMixin


class SearchIndexTestCase(WithFixturesMixin, TestCase):
    def _mock_setup(self):
        # Mock Patch object
        patch_registry = patch(
            'django_elasticsearch_dsl.management.commands.search_index.registry', self.registry)

        patch_registry.start()

        methods = ['delete', 'create']
        for index in [self.index_a, self.index_b]:
            for method in methods:
                obj_patch = patch.object(index, method)
                obj_patch.start()

        self.addCleanup(patch.stopall)

    def setUp(self):
        self.out = StringIO()
        self.registry = DocumentRegistry()
        self.index_a = Index('foo')
        self.index_b = Index('bar')

        self.doc_a1_qs = Mock()
        self.doc_a1 = self._generate_doc_mock(
            self.ModelA, self.index_a, self.doc_a1_qs
        )

        self.doc_a2_qs = Mock()
        self.doc_a2 = self._generate_doc_mock(
            self.ModelA, self.index_a, self.doc_a2_qs
        )

        self.doc_b1_qs = Mock()
        self.doc_b1 = self._generate_doc_mock(
            self.ModelB, self.index_a, self.doc_b1_qs
        )

        self.doc_c1_qs = Mock()
        self.doc_c1 = self._generate_doc_mock(
            self.ModelC, self.index_b, self.doc_c1_qs
        )

        self._mock_setup()

    def test_get_models(self):
        cmd = Command()
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
            'django_elasticsearch_dsl.management.commands.search_index.input',
            Mock(return_value="y")
        ):
            call_command('search_index', stdout=self.out,
                         action='delete', models=['foo'])
            self.index_a.delete.assert_called_once()
            self.assertFalse(self.index_b.delete.called)

    def test_force_delete_all_indices(self):

        call_command('search_index', stdout=self.out,
                     action='delete', force=True)
        self.index_a.delete.assert_called_once()
        self.index_b.delete.assert_called_once()

    def test_force_delete_bar_model_c_index(self):
        call_command('search_index', stdout=self.out,
                     models=[self.ModelC._meta.label],
                     action='delete', force=True)
        self.index_b.delete.assert_called_once()
        self.assertFalse(self.index_a.delete.called)

    def test_create_all_indices(self):
        call_command('search_index', stdout=self.out, action='create')
        self.index_a.create.assert_called_once()
        self.index_b.create.assert_called_once()

    def test_populate_all_doc_type(self):
        call_command('search_index', stdout=self.out, action='populate')
        expected_kwargs = {'parallel': False, 'refresh': None}
        # One call for "Indexing NNN documents", one for indexing itself (via get_index_queryset).
        assert self.doc_a1.get_queryset.call_count == 2
        self.doc_a1.update.assert_called_once_with(self.doc_a1_qs.iterator(), **expected_kwargs)
        assert self.doc_a2.get_queryset.call_count == 2
        self.doc_a2.update.assert_called_once_with(self.doc_a2_qs.iterator(), **expected_kwargs)
        assert self.doc_b1.get_queryset.call_count == 2
        self.doc_b1.update.assert_called_once_with(self.doc_b1_qs.iterator(), **expected_kwargs)
        assert self.doc_c1.get_queryset.call_count == 2
        self.doc_c1.update.assert_called_once_with(self.doc_c1_qs.iterator(), **expected_kwargs)

    def test_populate_all_doc_type_refresh(self):
        call_command('search_index', stdout=self.out, action='populate', refresh=True)
        expected_kwargs = {'parallel': False, 'refresh': True}
        self.doc_a1.update.assert_called_once_with(self.doc_a1_qs.iterator(), **expected_kwargs)
        self.doc_a2.update.assert_called_once_with(self.doc_a2_qs.iterator(), **expected_kwargs)
        self.doc_b1.update.assert_called_once_with(self.doc_b1_qs.iterator(), **expected_kwargs)
        self.doc_c1.update.assert_called_once_with(self.doc_c1_qs.iterator(), **expected_kwargs)

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
