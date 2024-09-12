from datetime import datetime
import unittest

import django
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
if django.VERSION < (4, 0):
    from django.utils.translation import ugettext_lazy as _
else:
    from django.utils.translation import gettext_lazy as _
from six import StringIO

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index as DSLIndex
from django_elasticsearch_dsl.test import ESTestCase, is_es_online
from tests import ES_MAJOR_VERSION

from .documents import (
    ad_index,
    AdDocument,
    car_index,
    CarDocument,
    CarWithPrepareDocument,
    ArticleDocument,
    ArticleWithSlugAsIdDocument,
    index_settings,
    CarBulkDocument,
    ManufacturerBulkDocument
)
from .models import (
    Car,
    Manufacturer,
    Ad,
    Category,
    Article,
    COUNTRIES,
    CarBulkManager,
    ManufacturerBulkManager,
    AdBulkManager,
    CategoryBulkManager
)


@unittest.skipUnless(is_es_online(), 'Elasticsearch is offline')
class IntegrationTestCase(ESTestCase, TransactionTestCase):
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
                'icon': self.category1.icon.url,
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
                'icon': self.category1.icon.url,
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
                    'icon': self.category1.icon.url,
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
        test_index.document(CarDocument)

        index_dict = test_index.to_dict()

        self.assertEqual(index_dict['settings'], {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': {
                    'html_strip': {
                        'tokenizer': 'standard',
                        'filter': ['lowercase',
                                   'stop', 'snowball'],
                        'type': 'custom',
                        'char_filter': ['html_strip']
                    }
                }
            }
        })
        self.assertEqual(index_dict['mappings'], {
                'properties': {
                    'ads': {
                        'type': 'nested',
                        'properties': {
                            'description': {
                                'type': text_type, 'analyzer':
                                'html_strip'
                            },
                            'pk': {'type': 'integer'},
                            'title': {'type': text_type}
                        },
                    },
                    'categories': {
                        'type': 'nested',
                        'properties': {
                            'title': {'type': text_type},
                            'slug': {'type': text_type},
                            'icon': {'type': text_type}
                        },
                    },
                    'manufacturer': {
                        'type': 'object',
                        'properties': {
                            'country': {'type': text_type},
                            'name': {'type': text_type}
                        },
                    },
                    'name': {'type': text_type},
                    'launched': {'type': 'date'},
                    'type': {'type': text_type}
                }
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

    def test_filter_queryset(self):
        Ad(title="Nothing that match",  car=self.car1).save()

        qs = AdDocument().search().query(
            'match', title="Ad number 2").filter_queryset(Ad.objects)
        self.assertEqual(qs.count(), 2)
        self.assertEqual(list(qs), [self.ad2, self.ad1])

        qs = AdDocument().search().query(
            'match', title="Ad number 2"
        ).filter_queryset(Ad.objects.filter(url="www.ad2.com"))
        self.assertEqual(qs.count(), 1)
        self.assertEqual(list(qs), [self.ad2])

        with self.assertRaisesMessage(TypeError, 'Unexpected queryset model'):
            AdDocument().search().query(
                'match', title="Ad number 2").filter_queryset(Category.objects)

    def test_to_queryset(self):
        Ad(title="Nothing that match",  car=self.car1).save()
        qs = AdDocument().search().query(
            'match', title="Ad number 2").to_queryset()
        self.assertEqual(qs.count(), 2)
        self.assertEqual(list(qs), [self.ad2, self.ad1])

    def test_queryset_iterator_queries(self):
        ad3 = Ad(title="Ad 3",  car=self.car1)
        ad3.save()
        with self.assertNumQueries(1):
            AdDocument().update(Ad.objects.all())

        doc = AdDocument()

        with self.assertNumQueries(1):
            doc.update(Ad.objects.all().order_by('-id'))
            self.assertEqual(
                set(int(instance.meta.id) for instance in
                    doc.search().query('match', title="Ad")),
                set([ad3.pk, self.ad1.pk, self.ad2.pk])
            )

    def test_default_document_id(self):
        obj_id = 12458
        article_slug = "some-article"
        article = Article(
            id=obj_id,
            slug=article_slug,
        )

        # saving should create two documents (in the two indices): one with the
        # Django object's id as the ES doc _id, and the other with the slug
        # as the ES _id
        article.save()

        # assert that the document's id is the id of the Django object
        try:
            es_obj = ArticleDocument.get(id=obj_id)
        except NotFoundError:
            self.fail("document with _id {} not found").format(obj_id)
        self.assertEqual(es_obj.slug, article.slug)

    def test_custom_document_id(self):
        article_slug = "my-very-first-article"
        article = Article(
            slug=article_slug,
        )

        # saving should create two documents (in the two indices): one with the
        # Django object's id as the ES doc _id, and the other with the slug
        # as the ES _id
        article.save()

        # assert that the document's id is its the slug
        try:
            es_obj = ArticleWithSlugAsIdDocument.get(id=article_slug)
        except NotFoundError:
            self.fail(
                "document with _id '{}' not found: "
                "using a custom id is broken".format(article_slug)
            )
        self.assertEqual(es_obj.slug, article.slug)


@unittest.skipUnless(is_es_online(), 'Elasticsearch is offline')
class IntegrationBulkOperationConfTestCase(ESTestCase, TestCase):

    def setUp(self):
        super().setUp()

        manufacturers = ManufacturerBulkManager.objects.bulk_create([
            ManufacturerBulkManager(
                name="Peugeot", created=datetime(1900, 10, 9, 0, 0),
                country_code="FR", logo='logo.jpg'
            )
        ])
        self.manufacturer = manufacturers[0]

        cars = CarBulkManager.objects.bulk_create([
            CarBulkManager(
                name="508", launched=datetime(2010, 9, 9, 0, 0),
                manufacturer=self.manufacturer
            ),
            CarBulkManager(
                name="208", launched=datetime(2010, 10, 9, 0, 0),
                manufacturer=self.manufacturer
            ),
            CarBulkManager(
                name="308", launched=datetime(2010, 11, 9, 0, 0)
            )
        ])
        self.car1 = cars[0]
        self.car2 = cars[1]
        self.car3 = cars[2]

        self.assertEqual(self.car1.name, "508")
        self.assertEqual(self.car2.name, "208")
        self.assertEqual(self.car3.name, "308")

        categories = CategoryBulkManager.objects.bulk_create([
            CategoryBulkManager(
                title="Category 1", slug="category-1", icon="icon.jpeg"
            ),
            CategoryBulkManager(title="Category 2", slug="category-2")
        ])
        self.category1 = categories[0]
        self.category2 = categories[1]

        self.assertEqual(self.category1.title, "Category 1")
        self.assertEqual(self.category2.title, "Category 2")

        self.car2.categories.add(self.category1)
        self.car2.save()

        self.car3.categories.add(self.category1, self.category2)
        self.car3.save()

        ads = AdBulkManager.objects.bulk_create([
            AdBulkManager(
                title=_("Ad number 1"), url="www.ad1.com",
                description="My super ad description 1",
                car=self.car1
            ),
            AdBulkManager(
                title="Ad number 2", url="www.ad2.com",
                description="My super ad descriptio 2",
                car=self.car1
            )
        ])
        self.ad1 = ads[0]
        self.ad2 = ads[1]

        self.assertEqual(self.ad1.title, _("Ad number 1"))
        self.assertEqual(self.ad2.title, "Ad number 2")

    def test_docs_are_updated_by_bulk_operations(self):
        old_car2_name = self.car2.name
        car2_name = "1008"

        s = CarBulkDocument.search().query("match", name=old_car2_name)
        self.assertEqual(s.count(), 1)

        s = CarBulkDocument.search().query("match", name=car2_name)
        self.assertEqual(s.count(), 0)

        CarBulkManager.objects.filter(id=self.car2.id).update(name=car2_name)

        s = CarBulkDocument.search().query("match", name=old_car2_name)
        self.assertEqual(s.count(), 0)

        s = CarBulkDocument.search().query("match", name=car2_name)
        self.assertEqual(s.count(), 1)

        s = CarBulkDocument.search().query("match", name=self.car3.name)
        car3_doc = s.execute()[0]
        self.assertEqual(car3_doc.manufacturer.name, None)

        CarBulkManager.objects.filter(
            id=self.car3.id
        ).update(manufacturer_id=self.manufacturer.pk)

        s = CarBulkDocument.search().query("match", name=self.car3.name)
        car3_doc = s.execute()[0]
        self.assertEqual(car3_doc.manufacturer.name, self.manufacturer.name)

        s = CarBulkDocument.search().query("match", name=self.car3.name)
        self.assertEqual(s.count(), 1)

        CarBulkManager.objects.filter(id=self.car3.id).delete()
        s = CarBulkDocument.search().query("match", name=self.car3.name)
        self.assertEqual(s.count(), 0)

        s = CarBulkDocument.search()
        self.assertEqual(s.count(), 2)

        s = ManufacturerBulkDocument.search()
        self.assertEqual(s.count(), 1)

        ManufacturerBulkManager.objects.all().delete()
        s = ManufacturerBulkDocument.search()
        self.assertEqual(s.count(), 0)

        s = CarBulkDocument.search()
        for result in s.execute():
            self.assertEqual(result.manufacturer.name, None)

    def test_related_docs_are_updated_by_bulk_operations(self):
        ManufacturerBulkManager.objects.filter(id=self.manufacturer.id).update(
            name="Citroen"
        )

        s = CarBulkDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(car2_doc.manufacturer.name, 'Citroen')
        self.assertEqual(len(car2_doc.ads), 0)

        ad3 = AdBulkManager.objects.bulk_create([
            AdBulkManager(title=_("Ad number 3"), url="www.ad3.com",
                          description="My super ad description 3",
                          car=self.car2)
        ])
        s = CarBulkDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(len(car2_doc.ads), 1)

        AdBulkManager.objects.filter(id__in=[ad.id for ad in ad3]).delete()
        s = CarBulkDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]
        self.assertEqual(len(car2_doc.ads), 0)

        ManufacturerBulkManager.objects.filter(
            id=self.manufacturer.id
        ).delete()
        s = CarBulkDocument.search().query("match", name=self.car2.name)
        car2_doc = s.execute()[0]

        self.assertEqual(car2_doc.manufacturer.name, None)
