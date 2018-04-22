from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields

from .models import Ad, Category, Car, Manufacturer


car = Index('test_cars')
car.settings(
    number_of_shards=1,
    number_of_replicas=0
)


html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)


@car.doc_type
class CarDocument(DocType):
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

    class Meta:
        model = Car
        related_models = [Ad, Manufacturer, Category]
        fields = [
            'name',
            'launched',
            'type',
        ]

    def get_queryset(self):
        return super(CarDocument, self).get_queryset().select_related(
            'manufacturer'
        )

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Ad):
            return related_instance.car

        # otherwise it's a Manufacturer or a Category
        return related_instance.car_set.all()


@car.doc_type
class ManufacturerDocument(DocType):
    country = fields.TextField()

    class Meta:
        model = Manufacturer
        fields = [
            'name',
            'created',
            'country_code',
            'logo',
        ]


class CarWithPrepareDocument(DocType):
    manufacturer = fields.ObjectField(properties={
        'name': fields.TextField(),
        'country': fields.TextField(),
    })

    manufacturer_short = fields.ObjectField(properties={
        'name': fields.TextField(),
    })

    class Meta:
        model = Car
        related_models = [Manufacturer]
        index = 'car_with_prepare_index'
        fields = [
            'name',
            'launched',
            'type',
        ]

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


class AdDocument(DocType):
    description = fields.TextField(
        analyzer=html_strip,
        fields={'raw': fields.KeywordField()}
    )

    class Meta:
        model = Ad
        index = 'test_ads'
        fields = [
            'title',
            'created',
            'modified',
            'url',
        ]


class AdDocument2(DocType):
    def __init__(self, *args, **kwargs):
        super(AdDocument2, self).__init__(*args, **kwargs)

    class Meta:
        model = Ad
        index = 'test_ads2'
        fields = [
            'title',
        ]
