from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import Document, Index, fields
from django_elasticsearch_dsl.registries import registry

from .models import Ad, Car, Manufacturer


car = Index('test_cars')
car.settings(
    number_of_shards=1,
    number_of_replicas=0
)


html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)


@registry.register_document
class CarDocument(Document):
    manufacturer = fields.ObjectField(properties={
        'name': fields.TextField(),
        'country': fields.TextField(),
        'logo': fields.FileField(),
    })

    ads = fields.NestedField(properties={
        'description': fields.TextField(analyzer=html_strip),
        'title': fields.TextField(),
        'pk': fields.IntegerField(),
    })

    categories = fields.NestedField(properties={
        'title': fields.TextField(),
    })

    class Django:
        model = Car
        fields = [
            'name',
            'launched',
            'type',
        ]

    class Index:
        name = "car"

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
        name = "manufacturer"


# @registry.register_document
# class CarWithPrepareDocument(Document):
#     manufacturer = fields.ObjectField(properties={
#         'name': fields.TextField(),
#         'country': fields.TextField(),
#     })
#
#     manufacturer_short = fields.ObjectField(properties={
#         'name': fields.TextField(),
#     })
#
#     class Index:
#         name = "car_with_prepare_index"
#
#     class Django:
#         model = Car
#         related_models = [Manufacturer]
#         fields = [
#             'name',
#             'launched',
#             'type',
#         ]
#
#     def prepare_manufacturer_with_related(self, car, related_to_ignore):
#         if (car.manufacturer is not None and car.manufacturer !=
#                 related_to_ignore):
#             return {
#                 'name': car.manufacturer.name,
#                 'country': car.manufacturer.country(),
#             }
#         return {}
#
#     def prepare_manufacturer_short(self, car):
#         if car.manufacturer is not None:
#             return {
#                 'name': car.manufacturer.name,
#             }
#         return {}
#
#     def get_instances_from_related(self, related_instance):
#         return related_instance.car_set.all()


@registry.register_document
class AdDocument(Document):
    description = fields.TextField(
        analyzer=html_strip,
        fields={'raw': fields.KeywordField()}
    )

    class Django:
        model = Ad
        index = 'test_ads'
        fields = [
            'title',
            'created',
            'modified',
            'url',
        ]

    class Index:
        name = "add"


@registry.register_document
class AdDocument2(Document):
    def __init__(self, *args, **kwargs):
        super(AdDocument2, self).__init__(*args, **kwargs)

    class Django:
        model = Ad
        index = 'test_ads2'
        fields = [
            'title',
        ]

    class Index:
        name = "add2"
