from unittest import TestCase

from mock import patch

from django_elasticsearch_dsl.documents import DocType
from django_elasticsearch_dsl.registries import registry

from .models import Car


class PostIndexSignalTestCase(TestCase):

    @patch('django_elasticsearch_dsl.documents.bulk')
    @patch('django_elasticsearch_dsl.documents.post_index')
    def test_post_index_signal_sent(self, post_index, bulk):

        @registry.register_document
        class CarDocument(DocType):
            class Django:
                fields = ['name']
                model = Car

        bulk.return_value = (1, [])

        doc = CarDocument()
        car = Car(
            pk=51,
            name="Type 57"
        )

        doc.update(car)

        bulk.assert_called_once()

        post_index.send.assert_called_once_with(
            sender=CarDocument,
            instance=doc,
            response=(1, [])
        )
