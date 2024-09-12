from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import (
    Ad,
    Category,
    Car,
    Manufacturer,
    Article,
    CarBulkManager,
    CategoryBulkManager,
    AdBulkManager,
    ManufacturerBulkManager
)

index_settings = {
    'number_of_shards': 1,
    'number_of_replicas': 0,
}


html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)


@registry.register_document
class CarDocument(Document):
    # test can override __init__
    def __init__(self, *args, **kwargs):
        super(CarDocument, self).__init__(*args, **kwargs)

    manufacturer = fields.ObjectField(properties={
        'name': fields.TextField(),
        'country': fields.TextField(),
    })

    ads = fields.NestedField(properties={
        'description': fields.TextField(analyzer=html_strip),
        'title': fields.TextField(),
        'pk': fields.IntegerField(),
    })

    categories = fields.NestedField(properties={
        'title': fields.TextField(),
        'slug': fields.TextField(),
        'icon': fields.FileField(),
    })

    class Django:
        model = Car
        related_models = [Ad, Manufacturer, Category]
        fields = [
            'name',
            'launched',
            'type',
        ]

    class Index:
        name = 'test_cars'
        settings = index_settings

    def get_queryset(self):
        return super(CarDocument, self).get_queryset().select_related(
            'manufacturer')

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Ad):
            return related_instance.car

        # otherwise it's a Manufacturer or a Category
        return related_instance.car_set.all()


@registry.register_document
class ManufacturerDocument(Document):
    country = fields.TextField()

    class Django:
        model = Manufacturer
        fields = [
            'name',
            'created',
            'country_code',
            'logo',
        ]

    class Index:
        name = 'index_settings'
        settings = index_settings


@registry.register_document
class CarWithPrepareDocument(Document):
    manufacturer = fields.ObjectField(properties={
        'name': fields.TextField(),
        'country': fields.TextField(),
    })

    manufacturer_short = fields.ObjectField(properties={
        'name': fields.TextField(),
    })

    class Django:
        model = Car
        related_models = [Manufacturer]
        fields = [
            'name',
            'launched',
            'type',
        ]

    class Index:
        name = 'car_with_prepare_index'

    def prepare_manufacturer_with_related(self, car, related_to_ignore):
        if (car.manufacturer is not None and car.manufacturer !=
                related_to_ignore):
            return {
                'name': car.manufacturer.name,
                'country': car.manufacturer.country(),
            }
        return {}

    def prepare_manufacturer_short(self, car):
        if car.manufacturer is not None:
            return {
                'name': car.manufacturer.name,
            }
        return {}

    def get_instances_from_related(self, related_instance):
        return related_instance.car_set.all()


@registry.register_document
class AdDocument(Document):
    description = fields.TextField(
        analyzer=html_strip,
        fields={'raw': fields.KeywordField()}
    )

    class Django:
        model = Ad
        fields = [
            'title',
            'created',
            'modified',
            'url',
        ]

    class Index:
        name = 'test_ads'
        settings = index_settings


@registry.register_document
class ArticleDocument(Document):
    class Django:
        model = Article
        fields = [
            'slug',
        ]

    class Index:
        name = 'test_articles'
        settings = index_settings


@registry.register_document
class ArticleWithSlugAsIdDocument(Document):
    class Django:
        model = Article
        fields = [
            'slug',
        ]

    class Index:
        name = 'test_articles_with_slugs_as_doc_ids'
        settings = index_settings

    @classmethod
    def generate_id(cls, article):
        return article.slug


ad_index = AdDocument._index
car_index = CarDocument._index


@registry.register_document
class CarBulkDocument(Document):

    manufacturer = fields.ObjectField(properties={
        'name': fields.TextField(),
        'country': fields.TextField(),
    })

    ads = fields.NestedField(properties={
        'description': fields.TextField(analyzer=html_strip),
        'title': fields.TextField(),
        'pk': fields.IntegerField(),
    })

    categories = fields.NestedField(properties={
        'title': fields.TextField(),
        'slug': fields.TextField(),
        'icon': fields.FileField(),
    })

    class Django:
        model = CarBulkManager
        related_models = [AdBulkManager,
                          ManufacturerBulkManager,
                          CategoryBulkManager]
        fields = [
            'name',
            'launched',
            'type',
        ]

    class Index:
        name = 'test_cars_bulk'
        settings = index_settings

    def get_queryset(self):
        return super(CarBulkDocument, self).get_queryset().select_related(
            'manufacturer')

    def get_instances_from_many_related(self, cls, related_instance):
        if isinstance(related_instance, list):
            if cls == AdBulkManager:
                return CarBulkManager.objects.filter(
                    id__in=[
                        item.car_id for item in related_instance
                    ]
                )
            elif cls == ManufacturerBulkManager:
                return CarBulkManager.objects.filter(
                    manufacturer_id__in=[
                        item.id for item in related_instance
                    ]
                )
            elif cls == CategoryBulkManager:
                return CarBulkManager.objects.filter(
                    categories__id__in=[
                        item.id for item in related_instance
                    ]
                )
        else:
            if cls == AdBulkManager:
                return CarBulkManager.objects.filter(
                    id__in=related_instance.values_list("car_id", flat=True)
                )
            elif cls == ManufacturerBulkManager:
                return CarBulkManager.objects.filter(
                    manufacturer_id__in=related_instance.values_list(
                        "id", flat=True
                    )
                )
            elif cls == CategoryBulkManager:
                return CarBulkManager.objects.filter(
                    categories__id__in=related_instance.values_list(
                        "id", flat=True
                    )
                )


@registry.register_document
class ManufacturerBulkDocument(Document):
    country = fields.TextField()

    class Django:
        model = ManufacturerBulkManager
        fields = [
            'name',
            'created',
            'country_code',
            'logo',
        ]

    class Index:
        name = 'test_manufacturers_bulk'
        settings = index_settings


@registry.register_document
class AdBulkDocument(Document):
    description = fields.TextField(
        analyzer=html_strip,
        fields={'raw': fields.KeywordField()}
    )

    class Django:
        model = AdBulkManager
        fields = [
            'title',
            'created',
            'modified',
            'url',
        ]

    class Index:
        name = 'test_ads_bulk'
        settings = index_settings
