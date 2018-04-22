from unittest import TestCase

from django.db import connections
from mock import patch

from django_elasticsearch_dsl import signals
from tests import fixtures


class BaseSignalProcessorTestCase(fixtures.WithFixturesMixin, TestCase):
    def setUp(self):
        super(BaseSignalProcessorTestCase, self).setUp()

        self.registry.register(self.index_1, fixtures.DocA1)
        self.registry.register(self.index_1, fixtures.DocA2)
        self.registry.register(self.index_2, fixtures.DocB1)
        self.registry.register(self.index_1, fixtures.DocC1)
        self.registry.register(self.index_1, fixtures.DocD1)

        self.processor = signals.BaseSignalProcessor(connections)
        signals.registry = self.registry

        self.bulk_patcher = patch('django_elasticsearch_dsl.actions.bulk')
        self.bulk_mock = self.bulk_patcher.start()

    def tearDown(self):
        self.bulk_patcher.stop()

    def test_handle_save(self):
        instance = fixtures.ModelD()
        self.processor.handle_save(None, instance=instance)

        self.bulk_mock.assert_called_once()
        cargs, ckwargs = self.bulk_mock.call_args

        self.assertEqual([
            {
                '_type': 'doc_d1',
                '_id': None,
                '_source': {},
                '_op_type': 'index',
                '_index': 'None',
            },
        ], list(ckwargs['actions']))

        self.assertEqual(fixtures.DocD1().connection, ckwargs['client'])

    def test_handle_save_related(self):
        instance = fixtures.ModelE()
        self.processor.handle_save(None, instance=instance)

        self.bulk_mock.assert_called_once()
        cargs, ckwargs = self.bulk_mock.call_args

        self.assertEqual([
            {
                '_type': 'doc_d1',
                '_id': None,
                '_source': {},
                '_op_type': 'index',
                '_index': 'None',
            },
        ], list(ckwargs['actions']))

        self.assertEqual(fixtures.DocD1().connection, ckwargs['client'])

    def test_handle_save_ignore_signals(self):
        instance = fixtures.ModelC()
        self.processor.handle_save(None, instance=instance)

        self.bulk_mock.assert_not_called()

    def test_handle_delete(self):
        instance = fixtures.ModelD()
        self.processor.handle_delete(None, instance=instance)

        self.bulk_mock.assert_called_once()
        cargs, ckwargs = self.bulk_mock.call_args

        self.assertEqual([
            {
                '_type': 'doc_d1',
                '_id': None,
                '_source': None,
                '_op_type': 'delete',
                '_index': 'None',
            },
        ], list(ckwargs['actions']))

        self.assertEqual(fixtures.DocD1().connection, ckwargs['client'])

    def test_handle_delete_related(self):
        instance = fixtures.ModelE()
        self.processor.handle_pre_delete(None, instance=instance)

        self.bulk_mock.assert_called_once()
        cargs, ckwargs = self.bulk_mock.call_args

        self.assertEqual([
            {
                '_type': 'doc_d1',
                '_id': None,
                '_source': {},
                '_op_type': 'index',
                '_index': 'None',
            },
        ], list(ckwargs['actions']))

        self.assertEqual(fixtures.DocD1().connection, ckwargs['client'])

    def test_handle_delete_ignore_signals(self):
        instance = fixtures.ModelC()
        self.processor.handle_delete(None, instance=instance)

        self.bulk_mock.assert_not_called()
