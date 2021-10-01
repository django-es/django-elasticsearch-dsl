from unittest import TestCase

from mock import Mock, patch

from django_elasticsearch_dsl.documents import DocType
from django_elasticsearch_dsl.registries import registry
from django_elasticsearch_dsl.signals import post_index

from .models import Car


class PostIndexSignalTestCase(TestCase):

    @patch('django_elasticsearch_dsl.documents.DocType._get_actions')
    @patch('django_elasticsearch_dsl.documents.bulk')
    def test_post_index_signal_sent(self, bulk, get_actions):

        @registry.register_document
        class CarDocument(DocType):
            class Django:
                fields = ['name']
                model = Car

        bulk.return_value = (1, [])

        # register a mock signal receiver
        mock_receiver = Mock()
        post_index.connect(mock_receiver)

        doc = CarDocument()
        car = Car(
            pk=51,
            name="Type 57"
        )
        doc.update(car)

        bulk.assert_called_once()

        mock_receiver.assert_called_once_with(
            signal=post_index,
            sender=CarDocument,
            instance=doc,
            actions=get_actions(),
            response=(1, [])
        )
