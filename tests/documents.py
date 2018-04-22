from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields

from .models import Ad, Category, Car, Manufacturer

index_settings = {
    'number_of_shards': 1,
    'number_of_replicas': 0,
}


car_index = Index('test_cars').settings(**index_settings)


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
        doc_type = 'car_document'

    def get_queryset(self):
        return super(CarDocument, self).get_queryset().select_related(
            'manufacturer')

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Ad):
            return related_instance.car

        # otherwise it's a Manufacturer or a Category
        return related_instance.car_set.all()


manufacturer_index = Index('test_manufacturers').settings(**index_settings)


@manufacturer_index.doc_type
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
        doc_type = 'manufacturer_document'


class CarWithPrepareDocument(DocType):
    manufacturer = fields.ObjectField(properties={
        'name': fields.StringField(),
        'country': fields.StringField(),
    })

    manufacturer_short = fields.ObjectField(properties={
        'name': fields.StringField(),
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


ad_index = Index('test_ads').settings(**index_settings)


@ad_index.doc_type
class AdDocument(DocType):
    description = fields.TextField(
        analyzer=html_strip,
        fields={'raw': fields.KeywordField()}
    )

    class Meta:
        model = Ad
        fields = [
            'title',
            'created',
            'modified',
            'url',
        ]
        doc_type = 'ad_document'


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
        doc_type = 'paginated_ad_document'

    def get_queryset(self):
        return Ad.objects.all().order_by('-id')
