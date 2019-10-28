from unittest import TestCase

from django.db import models
from django.utils.translation import ugettext_lazy as _
from elasticsearch_dsl import GeoPoint, MetaField
from mock import patch, Mock, PropertyMock

from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.documents import DocType
from django_elasticsearch_dsl.exceptions import (ModelFieldNotMappedError,
                                                 RedeclaredFieldError)
from django_elasticsearch_dsl.registries import registry
from tests import ES_MAJOR_VERSION


class Car(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    not_indexed = models.TextField()
    manufacturer = models.ForeignKey(
        'Manufacturer', null=True, on_delete=models.SET_NULL
    )

    class Meta:
        app_label = 'car'

    def type(self):
        return "break"


class Manufacturer(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'car'


@registry.register_document
class CarDocument(DocType):
    color = fields.TextField()
    type = fields.StringField()

    def prepare_color(self, instance):
        return "blue"

    class Meta:
        doc_type = 'car_document'

    class Django:
        fields = ['name', 'price']
        model = Car
        related_models = [Manufacturer]

    class Index:
        name = 'car_index'
        doc_type = 'car_document'


class DocTypeTestCase(TestCase):

    def test_model_class_added(self):
        self.assertEqual(CarDocument.django.model, Car)

    def test_ignore_signal_default(self):
        self.assertFalse(CarDocument.django.ignore_signals)

    def test_auto_refresh_default(self):
        self.assertTrue(CarDocument.django.auto_refresh)

    def test_ignore_signal_added(self):

        @registry.register_document
        class CarDocument2(DocType):
            class Django:
                model = Car
                ignore_signals = True

        self.assertTrue(CarDocument2.django.ignore_signals)

    def test_auto_refresh_added(self):
        @registry.register_document
        class CarDocument2(DocType):
            class Django:
                model = Car
                auto_refresh = False

        self.assertFalse(CarDocument2.django.auto_refresh)

    def test_queryset_pagination_added(self):
        @registry.register_document
        class CarDocument2(DocType):
            class Django:
                model = Car
                queryset_pagination = 120

        self.assertIsNone(CarDocument.django.queryset_pagination)
        self.assertEqual(CarDocument2.django.queryset_pagination, 120)

    def test_fields_populated(self):
        mapping = CarDocument._doc_type.mapping
        self.assertEqual(
            set(mapping.properties.properties.to_dict().keys()),
            set(['color', 'name', 'price', 'type'])
        )

    def test_related_models_added(self):
        related_models = CarDocument.django.related_models
        self.assertEqual([Manufacturer], related_models)

    def test_duplicate_field_names_not_allowed(self):
        with self.assertRaises(RedeclaredFieldError):
            @registry.register_document
            class CarDocument(DocType):
                color = fields.StringField()
                name = fields.StringField()

                class Django:
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

        self.assertEqual(
            CarDocument._doc_type.mapping.to_dict(), {
                    'properties': {
                        'name': {
                            'type': text_type
                        },
                        'color': {
                            'type': text_type
                        },
                        'type': {
                            'type': text_type
                        },
                        'price': {
                            'type': 'double'
                        }
                    }
            }
        )

    def test_get_queryset(self):
        qs = CarDocument().get_queryset()
        self.assertIsInstance(qs, models.QuerySet)
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
        @registry.register_document
        class CarDocumentDSlBaseField(DocType):
            position = GeoPoint()

            class Django:
                model = Car
                fields = ['name', 'price']

            class Index:
                name = 'car_index'

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
            }]
            self.assertEqual(1, mock.call_count)
            self.assertEqual(
                actions, list(mock.call_args_list[0][1]['actions'])
            )
            self.assertTrue(mock.call_args_list[0][1]['refresh'])
            self.assertEqual(
                doc._index.connection, mock.call_args_list[0][1]['client']
            )

    def test_model_instance_iterable_update(self):
        doc = CarDocument()
        car = Car(name="Type 57", price=5400000.0,
                  not_indexed="not_indexex", pk=51)
        car2 = Car(name=_("Type 42"), price=50000.0,
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
                    '_index': 'car_index'
                }]
            self.assertEqual(1, mock.call_count)
            self.assertEqual(
                actions, list(mock.call_args_list[0][1]['actions'])
            )
            self.assertTrue(mock.call_args_list[0][1]['refresh'])
            self.assertEqual(
                doc._index.connection, mock.call_args_list[0][1]['client']
            )

    def test_model_instance_update_no_refresh(self):
        doc = CarDocument()
        doc.django.auto_refresh = False
        car = Car()
        with patch('django_elasticsearch_dsl.documents.bulk') as mock:
            doc.update(car)
            self.assertNotIn('refresh', mock.call_args_list[0][1])

    def test_model_instance_iterable_update_with_pagination(self):
        class CarDocument2(DocType):
            class Django:
                model = Car
                queryset_pagination = 2

        doc = CarDocument()
        car1 = Car()
        car2 = Car()
        car3 = Car()

        bulk = "django_elasticsearch_dsl.documents.bulk"
        parallel_bulk = "django_elasticsearch_dsl.documents.parallel_bulk"
        with patch(bulk) as mock_bulk, patch(parallel_bulk) as mock_parallel_bulk:
            doc.update([car3, car2, car3])
            self.assertEqual(
                3, len(list(mock_bulk.call_args_list[0][1]['actions']))
            )
            self.assertEqual(mock_bulk.call_count, 1, "bulk is called")
            self.assertEqual(mock_parallel_bulk.call_count, 0, "parallel bulk is not called")

    def test_model_instance_iterable_update_with_parallel(self):
        class CarDocument2(DocType):
            class Django:
                model = Car

        doc = CarDocument()
        car1 = Car()
        car2 = Car()
        car3 = Car()
        bulk = "django_elasticsearch_dsl.documents.bulk"
        parallel_bulk = "django_elasticsearch_dsl.documents.parallel_bulk"
        with patch(bulk) as mock_bulk, patch(parallel_bulk) as mock_parallel_bulk:
            doc.update([car1, car2, car3], parallel=True)
            self.assertEqual(mock_bulk.call_count, 0, "bulk is not called")
            self.assertEqual(mock_parallel_bulk.call_count, 1, "parallel bulk is called")

    def test_init_prepare_correct(self):
        """Does init_prepare() run and collect the right preparation functions?"""

        d = CarDocument()
        self.assertEqual(len(d._prepared_fields), 4)

        expect = {
            'color': ("<class 'django_elasticsearch_dsl.fields.TextField'>",
                    ("<class 'method'>", "<type 'instancemethod'>")), # py3, py2
            'type': ("<class 'django_elasticsearch_dsl.fields.StringField'>",
                    ("<class 'functools.partial'>","<type 'functools.partial'>")),
            'name': ("<class 'django_elasticsearch_dsl.fields.TextField'>",
                    ("<class 'functools.partial'>","<type 'functools.partial'>")),
            'price': ("<class 'django_elasticsearch_dsl.fields.DoubleField'>",
                    ("<class 'functools.partial'>","<type 'functools.partial'>")),
        }

        for name, field, prep in d._prepared_fields:
            e = expect[name]
            self.assertEqual(str(type(field)), e[0], 'field type should be copied over')
            self.assertTrue('__call__' in dir(prep), 'prep function should be callable')
            self.assertTrue(str(type(prep)) in e[1], 'prep function is correct partial or method')

    def test_init_prepare_results(self):
        """Are the results from init_prepare() actually used in prepare()?"""
        d = CarDocument()

        car = Car()
        setattr(car, 'name', "Tusla")
        setattr(car, 'price', 340123.21)
        setattr(car, 'color', "polka-dots") # Overwritten by prepare function
        setattr(car, 'pk', 4701) # Ignored, not in document
        setattr(car, 'type', "imaginary")

        self.assertEqual(d.prepare(car), {'color': 'blue', 'type': 'imaginary', 'name': 'Tusla', 'price': 340123.21})

        m = Mock()
        # This will blow up should we access _fields and try to iterate over it.
        # Since init_prepare compiles a list of prepare functions, while
        # preparing no access to _fields should happen
        with patch.object(CarDocument, '_fields', 33):
            d.prepare(m)
        self.assertEqual(sorted([tuple(x) for x in m.method_calls], key=lambda _: _[0]),
                         [('name', (), {}),  ('price', (), {}), ('type', (), {})]
        )
