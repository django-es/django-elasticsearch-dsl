from copy import copy
from unittest.mock import patch

from django.test import TestCase

from django_dummy_app.models import Continent, Country


class SignalsTestCase(TestCase):
    def test_saving_model_instance_triggers_update(self):
        with patch('django_opensearch_dsl.documents.bulk') as mock:
            # GIVEN successive names for a continent to be created/updated
            initial_name = 'MyOwnContinent'
            new_name = 'MyOwnPeacefulContinent'

            # WHEN creating a model instance
            # AND updating it
            continent = Continent.objects.create(name=initial_name)
            continent.name = new_name
            continent.save()

            # THEN it should have been indexed twice, with successive names
            self.assertEqual(2, mock.call_count)
            create_bulk_actions = [{
                '_id': continent.pk,
                '_op_type': 'index',
                '_source': {
                    'countries': [],
                    'id': continent.pk,
                    'name': initial_name,
                },
                '_index': 'continent',
            }]
            update_bulk_actions = copy(create_bulk_actions)
            update_bulk_actions[0]['_source']['name'] = new_name
            self.assertEqual(
                create_bulk_actions, list(mock.call_args_list[0][1]['actions'])
            )
            self.assertEqual(
                update_bulk_actions, list(mock.call_args_list[1][1]['actions'])
            )

    def test_deleting_model_instance_triggers_unindex(self):
        with patch('django_opensearch_dsl.documents.bulk') as mock:
            # GIVEN an existing model instance
            continent = Continent.objects.create(name="MyOwnContinent")

            # WHEN deleting it
            continent.delete()

            # THEN it should have been unindexed
            # AND its dependant objects should have been unindexed first
            self.assertGreaterEqual(mock.call_count, 2)
            unindex_bulk_actions = [{
                '_id': continent.pk,
                '_op_type': 'delete',
                '_index': 'continent',
                '_source': None,
            }]
            self.assertEqual(
                unindex_bulk_actions, list(mock.call_args_list[-1][1]['actions'])
            )

    def test_updating_model_instance_does_nothing_if_autosync_disabled(self):
        with patch('django_opensearch_dsl.documents.bulk') as mock:
            # GIVEN OPENSEARCH_DSL_AUTOSYNC is False
            with patch(
                'django_opensearch_dsl.apps.DEDConfig.autosync_enabled',
                return_value=False
            ):
                # WHEN creating a new model instance
                Continent.objects.create(name='MyOwnContinent')

                # THEN it should not have been indexed
                self.assertEqual(mock.call_count, 0)

    def test_updating_model_instance_does_nothing_if_document_ignores_signals(self):
        with patch('django_opensearch_dsl.documents.bulk') as mock:
            # GIVEN ContinentDocument.django.ignore_signals is True
            with patch(
                'django_dummy_app.documents.ContinentDocument.django.ignore_signals',
                return_value=True
            ):
                # WHEN creating a new model instance
                Continent.objects.create(name='MyOwnContinent')

                # THEN it should not have been indexed
                self.assertEqual(mock.call_count, 0)
