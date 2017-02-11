from unittest import TestCase
from mock import patch
from django.db import models
from elasticsearch_dsl import GeoPoint
from django_elasticsearch_dsl.documents import DocType
from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.exceptions import (ModelFieldNotMappedError,
                                                 RedeclaredFieldError)


class Car(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    not_indexed = models.TextField()
    manufacturer = models.ForeignKey('Manufacturer')

    class Meta:
        app_label = 'car'

    def type(self):
        return "break"


class Manufacturer(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'car'


class CarDocument(DocType):
    color = fields.StringField()
    type = fields.StringField()

    def prepare_color(self, instance):
        return "blue"

    class Meta:
        fields = ['name', 'price']
        model = Car
        index = 'car_index'


class DocTypeTestCase(TestCase):

    def test_model_class_added(self):
        self.assertEqual(CarDocument._doc_type.model, Car)

    def test_ignore_signal_default(self):
        self.assertFalse(CarDocument._doc_type.ignore_signals)

    def test_ignore_signal_added(self):
        class Car2Document(DocType):
            class Meta:
                model = Car
                ignore_signals = True
        self.assertTrue(Car2Document._doc_type.ignore_signals)

    def test_fields_populated(self):
        mapping = CarDocument._doc_type.mapping
        self.assertEqual(
            set(mapping.properties.properties.to_dict().keys()),
            set(['color', 'name', 'price', 'type'])
        )

    def test_duplicate_field_names_not_allowed(self):
        with self.assertRaises(RedeclaredFieldError):
            class CarDocument(DocType):
                color = fields.StringField()
                name = fields.StringField()

                class Meta:
                    fields = ['name']
                    model = Car

    def test_to_field(self):
        doc = DocType()
        nameField = doc.to_field('name', Car._meta.get_field('name'))
        self.assertIsInstance(nameField, fields.StringField)
        self.assertEqual(nameField._path, ['name'])

    def test_to_field_with_unknown_field(self):
        doc = DocType()
        with self.assertRaises(ModelFieldNotMappedError):
            doc.to_field('manufacturer', Car._meta.get_field('manufacturer'))

    def test_mapping(self):
        self.assertEqual(
            CarDocument._doc_type.mapping.to_dict(), {
                'car_document': {
                    'properties': {
                        'name': {
                            'type': 'string'
                        },
                        'color': {
                            'type': 'string'
                        },
                        'type': {
                            'type': 'string'
                        },
                        'price': {
                            'type': 'double'
                        }
                    }
                }
            }
        )

    def test_get_queryset(self):
        qs = CarDocument().get_queryset()
        self.assertIsInstance(qs, models.Manager)
        self.assertEqual(qs.model, Car)

    def test_prepare(self):
        car = Car(name="Type 57", price=5400000.0, not_indexed="not_indexex")
        doc = CarDocument()
        prepared_data = doc.prepare(car)
        self.assertEqual(
            prepared_data, {
                'color': doc.prepare_color(None),
                'type': car.type(),
                'name': car.name,
                'price': car.price
            }
        )

    def test_prepare_ignore_dsl_base_field(self):
        class CarDocumentDSlBaseField(DocType):
            position = GeoPoint()

            class Meta:
                model = Car
                index = 'car_index'
                fields = ['name', 'price']

        car = Car(name="Type 57", price=5400000.0, not_indexed="not_indexex")
        doc = CarDocumentDSlBaseField()
        prepared_data = doc.prepare(car)
        self.assertEqual(
            prepared_data, {
                'name': car.name,
                'price': car.price
            }
        )

    def test_model_instance_update(self):
        doc = CarDocument()
        car = Car(name="Type 57", price=5400000.0,
                  not_indexed="not_indexex", pk=51)
        with patch('django_elasticsearch_dsl.documents.bulk') as mock:
            doc.update(car)
            actions = [{
                    '_id': car.pk,
                    '_op_type': 'index',
                    '_source': {
                        'name': car.name,
                        'price': car.price,
                        'type': car.type(),
                        'color': doc.prepare_color(None),
                    },
                    '_index': 'car_index',
                    '_type': 'car_document'
            }]
            self.assertEqual(1, mock.call_count)
            self.assertEqual(
                actions, list(mock.call_args_list[0][1]['actions'])
            )
            self.assertTrue(mock.call_args_list[0][1]['refresh'])
            self.assertEqual(
                doc.connection, mock.call_args_list[0][1]['client']
            )

    def test_model_instance_iterable_update(self):
        doc = CarDocument()
        car = Car(name="Type 57", price=5400000.0,
                  not_indexed="not_indexex", pk=51)
        car2 = Car(name="Type 42", price=50000.0,
                   not_indexed="not_indexex", pk=31)
        with patch('django_elasticsearch_dsl.documents.bulk') as mock:
            doc.update([car, car2], action='update')
            actions = [{
                    '_id': car.pk,
                    '_op_type': 'update',
                    '_source': {
                        'name': car.name,
                        'price': car.price,
                        'type': car.type(),
                        'color': doc.prepare_color(None),
                    },
                    '_index': 'car_index',
                    '_type': 'car_document'
                },
                {
                    '_id': car2.pk,
                    '_op_type': 'update',
                    '_source': {
                        'name': car2.name,
                        'price': car2.price,
                        'type': car2.type(),
                        'color': doc.prepare_color(None),
                    },
                    '_index': 'car_index',
                    '_type': 'car_document'
            }]
            self.assertEqual(1, mock.call_count)
            self.assertEqual(
                actions, list(mock.call_args_list[0][1]['actions'])
            )
            self.assertTrue(mock.call_args_list[0][1]['refresh'])
            self.assertEqual(
                doc.connection, mock.call_args_list[0][1]['client']
            )
