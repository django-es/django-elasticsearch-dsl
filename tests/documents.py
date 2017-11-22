from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields

from .models import Ad, Category, Car, Manufacturer


car_index = Index('test_cars')
car_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)


html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)


@car_index.doc_type
class CarDocument(DocType):
    # test can override __init__
    def __init__(self, *args, **kwargs):
        super(CarDocument, self).__init__(*args, **kwargs)

    manufacturer = fields.ObjectField(properties={
        'name': fields.StringField(),
        'country': fields.StringField(),
    })

    ads = fields.NestedField(properties={
        'description': fields.StringField(analyzer=html_strip),
        'title': fields.StringField(),
        'pk': fields.IntegerField(),
    })

    categories = fields.NestedField(properties={
        'title': fields.StringField(),
        'slug': fields.StringField(),
        'icon': fields.FileField(),
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
            'manufacturer')

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Ad):
            return related_instance.car

        # otherwise it's a Manufacturer or a Category
        return related_instance.car_set.all()


@car_index.doc_type
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


ad_index = Index('test_ads')
ad_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)


@ad_index.doc_type
class AdDocument(DocType):
    description = fields.StringField(
        analyzer=html_strip,
        fields={'raw': fields.StringField(index='not_analyzed')}
    )

    class Meta:
        model = Ad
        fields = [
            'title',
            'created',
            'modified',
            'url',
        ]


class PaginatedAdDocument(DocType):
    class Meta:
        model = Ad
        index = 'ad_index'
        queryset_pagination = 2
        fields = [
            'title',
            'created',
            'modified',
            'url',
        ]

    def get_queryset(self):
        return Ad.objects.all().order_by('-id')
