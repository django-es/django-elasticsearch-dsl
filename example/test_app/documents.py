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
        'name': fields.StringField(),
        'country': fields.StringField(),
        'logo': fields.FileField(),
    })

    ads = fields.NestedField(properties={
        'description': fields.StringField(analyzer=html_strip),
        'title': fields.StringField(),
        'pk': fields.IntegerField(),
    })

    categories = fields.NestedField(properties={
        'title': fields.StringField(),
    })

    class Meta:
        model = Car
        related_models = [Manufacturer, Category]
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
        return related_instance.car_set.all()


@car.doc_type
class ManufacturerDocument(DocType):
    country = fields.StringField()

    class Meta:
        model = Manufacturer
        fields = [
            'name',
            'created',
            'country_code',
            'logo',
        ]


class AdDocument(DocType):
    description = fields.StringField(
        analyzer=html_strip,
        fields={'raw': fields.StringField(index='not_analyzed')}
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
    class Meta:
        model = Ad
        index = 'test_ads'
        fields = [
            'title',
        ]
