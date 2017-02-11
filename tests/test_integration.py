from datetime import datetime
import os
import unittest

from django.core.management import call_command
from django.test import TestCase

from django.utils.six import StringIO
from django_elasticsearch_dsl.test import ESTestCase

from .documents import CarDocument, AdDocument, ad_index, car_index
from .models import Car, Manufacturer, Ad, Category, COUNTRIES


@unittest.skipUnless(
    os.environ.get('ELASTICSEARCH_URL', False),
    "--elasticsearch not set"
)
class IntegrationTestCase(ESTestCase, TestCase):
    def setUp(self):
        super(IntegrationTestCase, self).setUp()
        self.manufacturer = Manufacturer(name="Peugeot",
                                         created=datetime(1900, 10, 9, 0, 0),
                                         country_code="FR")
        self.manufacturer.save()
        self.car1 = Car(name="508", launched=datetime(2010, 9, 9, 0, 0),
                        manufacturer=self.manufacturer)
        self.car1.save()
        self.car2 = Car(name="208", launched=datetime(2010, 10, 9, 0, 0),
                        manufacturer=self.manufacturer)
        self.car2.save()
        self.category1 = Category(title="Category 1", slug="category-1")
        self.category1.save()
        self.car2.categories.add(self.category1)
        self.car2.save()

        self.car3 = Car(name="308", launched=datetime(2010, 11, 9, 0, 0))
        self.car3.save()
        self.category2 = Category(title="Category 2", slug="category-2")
        self.category2.save()
        self.car3.categories.add(self.category1, self.category2)
        self.car3.save()

        self.ad1 = Ad(title="Ad number 1", url="www.ad1.com",
                      description="My super ad description 1",
                      car=self.car1)
        self.ad1.save()
        self.ad2 = Ad(title="Ad number 2", url="www.ad2.com",
                      description="My super ad descriptio 2",
                      car=self.car1)
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
            },
            {
                'title': self.category2.title,
                'slug': self.category2.slug,
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
                },
                {
                    'title': self.category2.title,
                    'slug': self.category2.slug,
                }
            ]
        })

    def test_index_to_dict(self):
        index_dict = car_index.to_dict()
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
                    'name': {'type': 'string'},
                    'country': {'type': 'string'},
                    'country_code': {'type': 'string'},
                }
            },
            'car_document': {
                'properties': {
                    'ads': {
                        'type': 'nested',
                        'properties': {
                            'description': {
                                'type': 'string', 'analyzer':
                                'html_strip'
                            },
                            'pk': {'type': 'integer'},
                            'title': {'type': 'string'},
                        },
                    },
                    'categories': {
                        'type': 'nested',
                        'properties': {
                            'title': {'type': 'string'},
                            'slug': {'type': 'string'},
                        },
                    },
                    'manufacturer': {
                        'type': 'object',
                        'properties': {
                            'country': {'type': 'string'},
                            'name': {'type': 'string'},
                        },
                    },
                    'name': {'type': 'string'},
                    'launched': {'type': 'date'},
                    'type': {'type': 'string'},
                }
            }
        })

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
        result = AdDocument().search().execute()
        self.assertEqual(len(result), 0)
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
                     force=True, stdout=out)
        result = AdDocument().search().execute()
        self.assertEqual(len(result), 3)
