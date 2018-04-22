import datetime

from django.db import models
from django.test import TestCase
from elasticsearch_dsl import GeoPoint
from mock import patch

from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.documents import DocType
from django_elasticsearch_dsl.exceptions import (ModelFieldNotMappedError,
                                                 RedeclaredFieldError)
from tests import ES_MAJOR_VERSION

from .documents import CarDocument
from .models import Ad, Car, Category, Manufacturer


class DocTypeTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.break_car = Car(
            name="Type 51",
            type=Car.TYPE_BREAK,
            launched=datetime.date.today(),
            pk=51,
        )
        cls.coupe_car = Car(
            name="Type 52",
            type=Car.TYPE_COUPE,
            launched=datetime.date.today() - datetime.timedelta(days=50),
            pk=52,
        )

    def test_model_class_added(self):
        self.assertEqual(CarDocument._doc_type.model, Car)

    def test_ignore_signal_default(self):
        self.assertFalse(CarDocument._doc_type.ignore_signals)

    def test_auto_refresh_default(self):
        self.assertTrue(CarDocument._doc_type.auto_refresh)

    def test_ignore_signal_added(self):
        class CarDocument2(DocType):
            class Meta:
                model = Car
                ignore_signals = True

        self.assertTrue(CarDocument2._doc_type.ignore_signals)

    def test_auto_refresh_added(self):
        class CarDocument2(DocType):
            class Meta:
                model = Car
                auto_refresh = False

        self.assertFalse(CarDocument2._doc_type.auto_refresh)

    def test_queryset_pagination_added(self):
        class CarDocument2(DocType):
            class Meta:
                model = Car
                queryset_pagination = 120

        self.assertIsNone(CarDocument._doc_type.queryset_pagination)
        self.assertEqual(CarDocument2._doc_type.queryset_pagination, 120)

    def test_fields_populated(self):
        mapping = CarDocument._doc_type.mapping
        self.assertEqual(
            set(mapping.properties.properties.to_dict().keys()),
            set(['price', 'manufacturer', 'categories', 'name', 'type', 'ads', 'launched'])
        )

    def test_related_models_added(self):
        related_models = CarDocument._doc_type.related_models
        self.assertEqual([Ad, Manufacturer, Category], related_models)

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
        self.assertIsInstance(nameField, fields.TextField)
        self.assertEqual(nameField._path, ['name'])

    def test_to_field_with_unknown_field(self):
        doc = DocType()
        with self.assertRaises(ModelFieldNotMappedError):
            doc.to_field('manufacturer', Car._meta.get_field('manufacturer'))

    def test_mapping(self):
        text_type = 'string' if ES_MAJOR_VERSION == 2 else 'text'
        expected = {
            'ads': {
                'type': 'nested',
                'properties': {
                    'pk': {'type': 'integer'},
                    'title': {'type': text_type},
                    'description': {'analyzer': 'html_strip', 'type': text_type}
                }
            },
            'name': {'type': text_type},
            'categories': {
                'type': 'nested',
                'properties': {
                    'icon': {'type': text_type},
                    'slug': {'type': text_type},
                    'title': {'type': text_type}
                }
            },
            'type': {'type': text_type},
            'manufacturer': {
                'type': 'object',
                'properties': {
                    'name': {'type': text_type},
                    'country': {'type': text_type}
                }
            },
            'launched': {'type': 'date'},
            'price': {'type': 'double'}
        }
        self.assertEqual(
            CarDocument._doc_type.mapping.to_dict()['car_document']['properties'],
            expected
        )

    def test_get_queryset(self):
        qs = CarDocument().get_queryset()
        self.assertIsInstance(qs, models.QuerySet)
        self.assertEqual(qs.model, Car)

    def test_prepare(self):
        doc = CarDocument()
        prepared_data = doc.prepare(self.break_car)
        expected = {
            'type': self.break_car.type,
            'launched': self.break_car.launched,
            'ads': [],
            'categories': [],
            'manufacturer': {},
            'name': self.break_car.name,
            'price': self.break_car.price,
        }
        self.assertEqual(prepared_data, expected)

    def test_prepare_ignore_dsl_base_field(self):
        class CarDocumentDSlBaseField(DocType):
            position = GeoPoint()

            class Meta:
                model = Car
                index = 'car_index'
                fields = ['name', 'price']

        doc = CarDocumentDSlBaseField()
        prepared_data = doc.prepare(self.break_car)
        expected = {
            'name': self.break_car.name,
            'price': self.break_car.price
        }
        self.assertEqual(prepared_data, expected)

    def test_model_instance_update(self):
        doc = CarDocument()
        with patch('django_elasticsearch_dsl.documents.bulk') as mock:
            doc.update(self.break_car)
            actions = [{
                '_id': self.break_car.pk,
                '_op_type': 'index',
                '_source': {
                    'ads': [],
                    'categories': [],
                    'manufacturer': {},
                    'name': self.break_car.name,
                    'type': self.break_car.type,
                    'price': self.break_car.price,
                    'launched': self.break_car.launched,
                },
                '_index': CarDocument._doc_type.index,
                '_type': CarDocument._doc_type.mapping.properties._name
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
        with patch('django_elasticsearch_dsl.documents.bulk') as mock:
            doc.update([self.break_car, self.coupe_car], action='update')
            actions = [{
                '_id': self.break_car.pk,
                '_index': 'test_cars',
                '_op_type': 'update',
                '_source': {
                    'ads': [],
                    'categories': [],
                    'launched': self.break_car.launched,
                    'manufacturer': {},
                    'name': self.break_car.name,
                    'price': self.break_car.price,
                    'type': self.break_car.type},
                '_type': 'car_document'
            }, {
                '_id': self.coupe_car.pk,
                '_index': 'test_cars',
                '_op_type': 'update',
                '_source': {
                    'ads': [],
                    'categories': [],
                    'launched': self.coupe_car.launched,
                    'manufacturer': {},
                    'name': self.coupe_car.name,
                    'price': self.coupe_car.price,
                    'type': self.coupe_car.type},
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

    def test_model_instance_update_no_refresh(self):
        class CarDocumentNotAutoRefresh(DocType):
            class Meta:
                model = Car
                auto_refresh = False

        with patch('django_elasticsearch_dsl.documents.bulk') as mock:
            CarDocumentNotAutoRefresh().update(self.break_car)
            self.assertNotIn('refresh', mock.call_args_list[0][1])

    def test_model_instance_iterable_update_with_pagination(self):
        class CarDocument2(DocType):
            class Meta:
                model = Car
                queryset_pagination = 2

        doc = CarDocument2()
        car1 = Car()
        car2 = Car()
        car3 = Car()
        with patch('django_elasticsearch_dsl.documents.bulk') as mock:
            doc.update([car1, car2, car3])
            self.assertEqual(
                3, len(list(mock.call_args_list[0][1]['actions']))
            )

    def test_queryset_update_with_pagination(self):
        class CarDocument2(DocType):
            class Meta:
                model = Car
                queryset_pagination = 6

        doc = CarDocument2()
        count = 10
        cars = [
            Car(launched=datetime.date.today(), price=12000)
            for i in range(count)
        ]

        Car.objects.bulk_create(cars)  # bypass django signal
        with patch('django_elasticsearch_dsl.documents.bulk') as mock:
            # force querying in disorder
            cars_from_db = Car.objects.all().order_by('?')
            doc.update(cars_from_db)
            pks = set(r['_id'] for r in mock.call_args_list[0][1]['actions'])
            self.assertEqual(count, len(pks))
