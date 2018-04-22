from itertools import chain
from unittest import TestCase

from django_elasticsearch_dsl import DocType
from django_elasticsearch_dsl.actions import ActionBuffer
from tests import fixtures
from tests.models import Car


class ActionBufferTestCase(fixtures.WithFixturesMixin, TestCase):

    def setUp(self):
        super(ActionBufferTestCase, self).setUp()

        self.registry.register(self.index_1, fixtures.DocA1)
        self.registry.register(self.index_1, fixtures.DocA2)
        self.registry.register(self.index_1, fixtures.DocD1)

        self.action_buffer = ActionBuffer(registry=self.registry)

    def test_add_doc_actions(self):
        instance = fixtures.ModelA()

        self.action_buffer.add_doc_actions(
            fixtures.DocA1(), instance, action='my_action'
        )

        self.assertEqual(1, len(self.action_buffer._actions))

        self.assertEqual([{
            '_type': 'doc_a1',
            '_id': None,
            '_source': {},
            '_op_type': 'my_action',
            '_index': 'None',
        }], list(chain(
            *self.action_buffer._actions[fixtures.DocA1().connection]
        )))

    def test_add_doc_actions_iterable(self):
        instances = [fixtures.ModelA(), fixtures.ModelA()]

        self.action_buffer.add_doc_actions(
            fixtures.DocA1(), instances, action='my_action'
        )

        self.assertEqual(1, len(self.action_buffer._actions))

        self.assertEqual([
            {
                '_type': 'doc_a1',
                '_id': None,
                '_source': {},
                '_op_type': 'my_action',
                '_index': 'None',
            },
            {
                '_type': 'doc_a1',
                '_id': None,
                '_source': {},
                '_op_type': 'my_action',
                '_index': 'None',
            },
        ], list(chain(
            *self.action_buffer._actions[fixtures.DocA1().connection]
        )))

    def test_add_doc_actons_with_pagination(self):
        class CarDocument2(DocType):
            class Meta:
                model = Car
                queryset_pagination = 2

        car1 = Car()
        car2 = Car()
        car3 = Car()

        self.action_buffer.add_doc_actions(CarDocument2(), [car1, car2, car3])

        self.assertEqual(1, len(self.action_buffer._actions))

        self.assertEqual(3, len(list(chain(
            *self.action_buffer._actions[CarDocument2().connection]
        ))))

    def test_add_model_actions(self):
        instance = fixtures.ModelA()

        self.action_buffer.add_model_actions(instance, action='my_action')
        self.assertEqual(1, len(self.action_buffer._actions))

        self.assertEqual([
            {
                '_type': 'doc_a1',
                '_id': None,
                '_source': {},
                '_op_type': 'my_action',
                '_index': 'None',
            },
            {
                '_type': 'doc_a2',
                '_id': None,
                '_source': {},
                '_op_type': 'my_action',
                '_index': 'None',
            },
        ], sorted(list(chain(
            *self.action_buffer._actions[fixtures.DocA1().connection]
        )), key=lambda k: k['_type']))

    def test_add_model_actions_related(self):
        instance = fixtures.ModelE()

        self.action_buffer.add_model_actions(instance, action='delete')
        self.assertEqual(1, len(self.action_buffer._actions))

        self.assertEqual([
            {
                '_type': 'doc_d1',
                '_id': None,
                '_source': {},
                '_op_type': 'index',
                '_index': 'None',
            },
        ], list(chain(
            *self.action_buffer._actions[fixtures.DocA1().connection]
        )))
