from datetime import datetime
import os
import unittest

from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from django.utils.translation import ugettext_lazy as _

from elasticsearch_dsl import Index as DSLIndex
from django_elasticsearch_dsl.test import ESTestCase
from tests import ES_MAJOR_VERSION

from .documents import (
    ad_index,
    AdDocument,
    car_index,
    CarDocument,
    CarWithPrepareDocument,
    PaginatedAdDocument,
    ManufacturerDocument,
    index_settings
)
from .models import Car, Manufacturer, Ad, Category, COUNTRIES


@unittest.skipUnless(
    os.environ.get('ELASTICSEARCH_URL', False),
    "--elasticsearch not set"
)
class IntegrationTestCase(ESTestCase, TestCase):
    def setUp(self):
        super(IntegrationTestCase, self).setUp()
        self.manufacturer = Manufacturer(
            name="Peugeot", created=datetime(1900, 10, 9, 0, 0),
            country_code="FR", logo='logo.jpg'
        )
        self.manufacturer.save()
        self.car1 = Car(
            name="508", launched=datetime(2010, 9, 9, 0, 0),
            manufacturer=self.manufacturer
        )

        self.car1.save()
        self.car2 = Car(
            name="208", launched=datetime(2010, 10, 9, 0, 0),
            manufacturer=self.manufacturer
        )
        self.car2.save()
        self.category1 = Category(
            title="Category 1", slug="category-1", icon="icon.jpeg"
        )
        self.category1.save()
        self.car2.categories.add(self.category1)
        self.car2.save()

        self.car3 = Car(name="308", launched=datetime(2010, 11, 9, 0, 0))
        self.car3.save()
        self.category2 = Category(title="Category 2", slug="category-2")
        self.category2.save()
        self.car3.categories.add(self.category1, self.category2)
        self.car3.save()

        self.ad1 = Ad(
            title=_("Ad number 1"), url="www.ad1.com",
            description="My super ad description 1",
            car=self.car1
        )
        self.ad1.save()
        self.ad2 = Ad(
            title="Ad number 2", url="www.ad2.com",
            description="My super ad descriptio 2",
            car=self.car1
        )
        self.ad2.save()
        self.car1.save()

    def test_get_doc_with_relationships(self):
        s = CarDocument.search().query("match", name=self.car2.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car2_doc = result[0]
        self.assertEqual(car2_doc.ads, [])
        self.assertEqual(car2_doc.name, self.car2.name)
        self.assertEqual(int(car2_doc.meta.id), self.car2.pk)
        self.assertEqual(car2_doc.launched, self.car2.launched)
        self.assertEqual(car2_doc.manufacturer.name,
                         self.car2.manufacturer.name)
        self.assertEqual(car2_doc.manufacturer.country,
                         COUNTRIES[self.manufacturer.country_code])

        s = CarDocument.search().query("match", name=self.car3.name)
        result = s.execute()
        car3_doc = result[0]
        self.assertEqual(car3_doc.manufacturer, {})
        self.assertEqual(car3_doc.name, self.car3.name)
        self.assertEqual(int(car3_doc.meta.id), self.car3.pk)

    def test_get_doc_with_reverse_relationships(self):
        s = CarDocument.search().query("match", name=self.car1.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car1_doc = result[0]
        self.assertEqual(car1_doc.ads, [
            {
                'title': self.ad1.title,
                'description': self.ad1.description,
                'pk': self.ad1.pk,
            },
            {
                'title': self.ad2.title,
                'description': self.ad2.description,
                'pk': self.ad2.pk,
            },
        ])
        self.assertEqual(car1_doc.name, self.car1.name)
        self.assertEqual(int(car1_doc.meta.id), self.car1.pk)

    def test_get_doc_with_many_to_many_relationships(self):
        s = CarDocument.search().query("match", name=self.car3.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car1_doc = result[0]
        self.assertEqual(car1_doc.categories, [
            {
                'title': self.category1.title,
                'slug': self.category1.slug,
                'icon': self.category1.icon,
            },
            {
                'title': self.category2.title,
                'slug': self.category2.slug,
                'icon': '',
            }
        ])

    def test_doc_to_dict(self):
        s = CarDocument.search().query("match", name=self.car2.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car2_doc = result[0]
        self.assertEqual(car2_doc.to_dict(), {
            'type': self.car2.type,
            'launched': self.car2.launched,
            'name': self.car2.name,
            'manufacturer': {
                'name': self.manufacturer.name,
                'country': COUNTRIES[self.manufacturer.country_code],
            },
            'categories': [{
                'title': self.category1.title,
                'slug': self.category1.slug,
                'icon': self.category1.icon,
            }]
        })

        s = CarDocument.search().query("match", name=self.car3.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car3_doc = result[0]
        self.assertEqual(car3_doc.to_dict(), {
            'type': self.car3.type,
            'launched': self.car3.launched,
            'name': self.car3.name,
            'categories': [
                {
                    'title': self.category1.title,
                    'slug': self.category1.slug,
                    'icon': self.category1.icon,
                },
                {
                    'title': self.category2.title,
                    'slug': self.category2.slug,
                    'icon': '',
                }
            ]
        })

    def test_index_to_dict(self):
        self.maxDiff = None
        index_dict = car_index.to_dict()
        text_type = 'string' if ES_MAJOR_VERSION == 2 else 'text'

        test_index = DSLIndex('test_index').settings(**index_settings)
        test_index.doc_type(CarDocument)
        test_index.doc_type(ManufacturerDocument)

        index_dict = test_index.to_dict()

        self.assertEqual(index_dict['settings'], {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': {
                    'html_strip': {
                        'tokenizer': 'standard',
                        'filter': ['standard', 'lowercase',
                                   'stop', 'snowball'],
                        'type': 'custom',
                        'char_filter': ['html_strip']
                    }
                }
            }
        })
        self.assertEqual(index_dict['mappings'], {
            'manufacturer_document': {
                'properties': {
                    'created': {'type': 'date'},
                    'name': {'type': text_type},
                    'country': {'type': text_type},
                    'country_code': {'type': text_type},
                    'logo': {'type': text_type},
                }
            },
            'car_document': {
                'properties': {
                    'ads': {
                        'type': 'nested',
                        'properties': {
                            'description': {
                                'type': text_type, 'analyzer':
                                'html_strip'
                            },
                            'pk': {'type': 'integer'},
                            'title': {'type': text_type},
                        },
                    },
                    'categories': {
                        'type': 'nested',
                        'properties': {
                            'title': {'type': text_type},
                            'slug': {'type': text_type},
                            'icon': {'type': text_type},
                        },
                    },
                    'manufacturer': {
                        'type': 'object',
                        'properties': {
                            'country': {'type': text_type},
                            'name': {'type': text_type},
                        },
                    },
                    'name': {'type': text_type},
                    'launched': {'type': 'date'},
                    'type': {'type': text_type},
                }
            },
        })

    def test_related_docs_are_updated(self):
        # test foreignkey relation
        self.manufacturer.name = 'Citroen'
        self.manufacturer.save()

        s = CarDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(car2_doc.manufacturer.name, 'Citroen')
        self.assertEqual(len(car2_doc.ads), 0)

        ad3 = Ad.objects.create(
            title=_("Ad number 3"), url="www.ad3.com",
            description="My super ad description 3",
            car=self.car2
        )
        s = CarDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(len(car2_doc.ads), 1)
        ad3.delete()
        s = CarDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(len(car2_doc.ads), 0)

        self.manufacturer.delete()
        s = CarDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(car2_doc.manufacturer, {})

    def test_m2m_related_docs_are_updated(self):
        # test m2m add
        category = Category(
            title="Category", slug="category", icon="icon.jpeg"
        )
        category.save()
        self.car2.categories.add(category)
        s = CarDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(len(car2_doc.categories), 2)

        # test m2m deletion
        self.car2.categories.remove(category)
        s = CarDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(len(car2_doc.categories), 1)

        self.category1.car_set.clear()
        s = CarDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(len(car2_doc.categories), 0)

    def test_related_docs_with_prepare_are_updated(self):
        s = CarWithPrepareDocument.search().query("match", name=self.car2.name)
        self.assertEqual(s.execute()[0].manufacturer.name, 'Peugeot')
        self.assertEqual(s.execute()[0].manufacturer_short.name, 'Peugeot')

        self.manufacturer.name = 'Citroen'
        self.manufacturer.save()
        s = CarWithPrepareDocument.search().query("match", name=self.car2.name)
        self.assertEqual(s.execute()[0].manufacturer.name, 'Citroen')
        self.assertEqual(s.execute()[0].manufacturer_short.name, 'Citroen')

        self.manufacturer.delete()
        s = CarWithPrepareDocument.search().query("match", name=self.car2.name)
        self.assertEqual(s.execute()[0].manufacturer, {})

    def test_delete_create_populate_commands(self):
        out = StringIO()
        self.assertTrue(ad_index.exists())
        self.assertTrue(car_index.exists())

        call_command('search_index', action='delete',
                     force=True, stdout=out, models=['tests.ad'])
        self.assertFalse(ad_index.exists())
        self.assertTrue(car_index.exists())

        call_command('search_index', action='create',
                     models=['tests.ad'], stdout=out)
        self.assertTrue(ad_index.exists())
        call_command('search_index', action='populate',
                     models=['tests.ad'], stdout=out)
        result = AdDocument().search().execute()
        self.assertEqual(len(result), 2)

    def test_rebuild_command(self):
        out = StringIO()
        result = AdDocument().search().execute()
        self.assertEqual(len(result), 2)

        Ad(title="Ad title 3").save()

        call_command('search_index', action='populate',
                     force=True, stdout=out, models=['tests.ad'])
        result = AdDocument().search().execute()
        self.assertEqual(len(result), 3)

    def test_to_queryset(self):
        Ad(title="Nothing that match",  car=self.car1).save()
        qs = AdDocument().search().query(
            'match', title="Ad number 2").to_queryset()
        self.assertEqual(qs.count(), 2)
        self.assertEqual(list(qs), [self.ad2, self.ad1])

    def test_queryset_pagination(self):
        ad3 = Ad(title="Ad 3",  car=self.car1)
        ad3.save()
        with self.assertNumQueries(1):
            AdDocument().update(Ad.objects.all())

        doc = PaginatedAdDocument()

        with self.assertNumQueries(3):
            doc.update(Ad.objects.all().order_by('-id'))
            self.assertEqual(
                set(int(instance.meta.id) for instance in
                    doc.search().query('match', title="Ad")),
                set([ad3.pk, self.ad1.pk, self.ad2.pk])
            )
