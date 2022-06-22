from typing import Optional

from django.db.models import QuerySet
from opensearch_dsl import Q

from django_opensearch_dsl import Document, fields
from django_opensearch_dsl.registries import registry
from .models import Country, Continent, Event


@registry.register_document
class ContinentDocument(Document):
    class Index:
        name = "continent"

    class Django:
        model = Continent
        fields = [
            "name",
        ]

    id = fields.LongField()
    countries = fields.NestedField(
        properties={
            "id": fields.LongField(),
            "name": fields.KeywordField(),
            "area": fields.LongField(),
            "population": fields.LongField(),
        }
    )


@registry.register_document
class CountryDocument(Document):
    class Index:
        name = "country"
        refresh = True

    class Django:
        model = Country
        fields = [
            "name",
            "area",
            "population",
        ]

    id = fields.LongField()
    continent = fields.ObjectField(
        properties={
            "id": fields.LongField(),
            "name": fields.KeywordField(),
        }
    )
    events_id = fields.LongField(multi=True)
    event_count_property = fields.LongField(attr="event_count")
    event_count_func = fields.LongField(attr="event_count_func")

    def prepare_events_id(self, obj):
        return list(obj.events.all().values_list("pk", flat=True))

    def get_queryset(self, filter_: Optional[Q] = None, exclude: Optional[Q] = None, count: int = None) -> QuerySet:
        """Return the queryset that should be indexed by this doc type."""
        return super().get_queryset(filter_=filter_, exclude=exclude, count=count).prefetch_related("events")


@registry.register_document
class EventDocument(Document):
    class Index:
        name = "event"
        auto_refresh = True

    class Django:
        model = Event
        queryset_pagination = 512
        fields = [
            "name",
            "date",
            "source",
            "comment",
            "null_field",
        ]

    country = fields.ObjectField(doc_class=CountryDocument)
    unknown = fields.LongField(required=False)

    def get_queryset(self, filter_: Optional[Q] = None, exclude: Optional[Q] = None, count: int = None) -> QuerySet:
        """Return the queryset that should be indexed by this doc type."""
        return super().get_queryset(filter_=filter_, exclude=exclude, count=count).select_related("country")

    def should_index_object(self, obj):
        return obj.country.name != "France"
