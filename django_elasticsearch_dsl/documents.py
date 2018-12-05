from __future__ import unicode_literals

from collections import deque
from functools import partial

from django.db import models
from django.utils.six import add_metaclass, iteritems

from elasticsearch.helpers import bulk, parallel_bulk
from elasticsearch_dsl import DocType as DSLDocType
from elasticsearch_dsl.document import DocTypeMeta as DSLDocTypeMeta
from elasticsearch_dsl.field import Field


from .apps import DEDConfig
from .exceptions import ModelFieldNotMappedError, RedeclaredFieldError
from .fields import (
    BooleanField,
    DateField,
    DEDField,
    DoubleField,
    FileField,
    IntegerField,
    KeywordField,
    LongField,
    ShortField,
    TextField,
)
from .indices import Index
from .registries import registry
from .search import Search

model_field_class_to_field_class = {
    models.AutoField: IntegerField,
    models.BigIntegerField: LongField,
    models.BooleanField: BooleanField,
    models.CharField: TextField,
    models.DateField: DateField,
    models.DateTimeField: DateField,
    models.EmailField: TextField,
    models.FileField: FileField,
    models.FilePathField: KeywordField,
    models.FloatField: DoubleField,
    models.ImageField: FileField,
    models.IntegerField: IntegerField,
    models.NullBooleanField: BooleanField,
    models.PositiveIntegerField: IntegerField,
    models.PositiveSmallIntegerField: ShortField,
    models.SlugField: KeywordField,
    models.SmallIntegerField: ShortField,
    models.TextField: TextField,
    models.TimeField: LongField,
    models.URLField: TextField,
}

class PagingQuerysetProxy(object):
    """
    I am a tiny standin for Django Querysets that implements enough of
    the protocol (namely count() and __iter__) to be useful for indexing
    large data sets.

    When iterated over, I will:
        - use qs.iterator() to disable result set caching in queryset.
        - chunk fetching the results so that caching in database driver
            (especially psycopg2) is kept to a minimum, and database
            drivers that do not support streaming (eg. mysql) do not
            need to load the whole dataset at once.
    """
    def __init__(self, qs, chunk_size=10000):
        self.qs = qs
        self.chunk_size = chunk_size

    def count(self):
        """Pass through to underlying queryset"""
        return self.qs.count()

    def __iter__(self):
        """Iterate over result set. Internally uses iterator() as not
        to cache in the queryset; also supports chunking fetching data
        in smaller sets so that databases that do not use server side
        cursors (django docs say only postgres and oracle do) or other
        optimisations keep memory consumption manageable."""

        last_max_pk = None

        # Get a clone of the QuerySet so that the cache doesn't bloat up
        # in memory. Useful when reindexing large amounts of data.
        small_cache_qs = self.qs.order_by('pk')

        once = no_data = False
        while not no_data and not once:
            # If we got the max seen PK from last batch, use it to restrict the qs
            # to values above; this optimises the query for Postgres as not to
            # devolve into multi-second run time at large offsets.
            if self.chunk_size:
                print("chunk", last_max_pk)
                if last_max_pk is not None:
                    current_qs = small_cache_qs.filter(pk__gt=last_max_pk)[:self.chunk_size]
                else:
                    current_qs = small_cache_qs[:self.chunk_size]
            else: # Handle "no chunking"
                current_qs = small_cache_qs
                once = True	 # force loop exit after fetching all data

            no_data = True
            for obj in current_qs.iterator():
                # Remember maximum PK seen so far
                last_max_pk = obj.pk
                no_data = False
                yield obj

            current_qs = None  # I'm free!


class DocTypeMeta(DSLDocTypeMeta):
    def __new__(cls, name, bases, attrs):
        """
        Subclass default DocTypeMeta to generate ES fields from django
        models fields
        """
        super_new = super(DocTypeMeta, cls).__new__

        parents = [b for b in bases if isinstance(b, DocTypeMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        model = attrs['Meta'].model

        ignore_signals = getattr(attrs['Meta'], "ignore_signals", False)
        auto_refresh = getattr(
            attrs['Meta'], 'auto_refresh', DEDConfig.auto_refresh_enabled()
        )
        model_field_names = getattr(attrs['Meta'], "fields", [])
        related_models = getattr(attrs['Meta'], "related_models", [])
        queryset_pagination = getattr(attrs['Meta'], "queryset_pagination", None)

        class_fields = set(
            name for name, field in iteritems(attrs)
            if isinstance(field, Field)
        )

        cls = super_new(cls, name, bases, attrs)

        cls._doc_type.model = model
        cls._doc_type.ignore_signals = ignore_signals
        cls._doc_type.auto_refresh = auto_refresh
        cls._doc_type.related_models = related_models
        cls._doc_type.queryset_pagination = queryset_pagination

        fields = model._meta.get_fields()
        fields_lookup = dict((field.name, field) for field in fields)

        for field_name in model_field_names:
            if field_name in class_fields:
                raise RedeclaredFieldError(
                    "You cannot redeclare the field named '{}' on {}"
                    .format(field_name, cls.__name__)
                )

            field_instance = cls.to_field(field_name,
                                          fields_lookup[field_name])
            cls._doc_type.mapping.field(field_name, field_instance)

        cls._doc_type._fields = (
            lambda: cls._doc_type.mapping.properties.properties.to_dict())

        if getattr(cls._doc_type, 'index'):
            index = Index(cls._doc_type.index)
            index.doc_type(cls)
            registry.register(index, cls)

        return cls


@add_metaclass(DocTypeMeta)
class DocType(DSLDocType):
    def __init__(self, related_instance_to_ignore=None, **kwargs):
        super(DocType, self).__init__(**kwargs)
        self._related_instance_to_ignore = related_instance_to_ignore

    def __eq__(self, other):
        return id(self) == id(other)

    def __hash__(self):
        return id(self)

    @classmethod
    def search(cls, using=None, index=None):
        return Search(
            using=using or cls._doc_type.using,
            index=index or cls._doc_type.index,
            doc_type=[cls],
            model=cls._doc_type.model
        )

    def get_queryset(self):
        """
        Return the queryset that should be indexed by this doc type.
        """
        return self._doc_type.model._default_manager.all()

    def get_indexing_queryset(self):
        qs = self.get_queryset()
        # Note: PagingQuerysetProxy handles the "no chunking" case,
        #  but some tests check for the mock qs, so don't interfere.
        #  We could remove this check/branch if the tests are adapted.
        if self._doc_type.queryset_pagination is not None:
            return PagingQuerysetProxy(qs, chunk_size=self._doc_type.queryset_pagination)
        return qs

    def init_prepare(self):
        """
        Initialise the data model preparers once here. Extracts the preparers
        from the model and generate a list of callables to avoid doing that
        work on every object instance over.
        """
        fields = []
        for name, field in self._doc_type._fields().items():
            if not isinstance(field, DEDField):
                continue

            if not field._path:
                field._path = [name]

            prep_func = getattr(self, 'prepare_%s_with_related' % name, None)
            if prep_func:
                fn = partial(prep_func, related_to_ignore=self._related_instance_to_ignore)
            else:
                prep_func = getattr(self, 'prepare_%s' % name, None)
                if prep_func:
                    fn = prep_func
                else:
                    fn = partial(field.get_value_from_instance, field_value_to_ignore=self._related_instance_to_ignore)

            fields.append((name, field, fn))

        self._doc_type._prepared_fields = fields

    def prepare(self, instance):
        """
        Take a model instance, and turn it into a dict that can be serialized
        based on the fields defined on this DocType subclass
        """
        if getattr(self._doc_type, '_prepared_fields', None) is None:
            self.init_prepare()

        data = {
            name: prep_func(instance)
                for name, field, prep_func in self._doc_type._prepared_fields
            }
        return data

    @classmethod
    def to_field(cls, field_name, model_field):
        """
        Returns the elasticsearch field instance appropriate for the model
        field class. This is a good place to hook into if you have more complex
        model field to ES field logic
        """
        try:
            return model_field_class_to_field_class[
                model_field.__class__](attr=field_name)
        except KeyError:
            raise ModelFieldNotMappedError(
                "Cannot convert model field {} "
                "to an Elasticsearch field!".format(field_name)
            )

    def bulk(self, actions, **kwargs):
        return bulk(client=self.connection, actions=actions, **kwargs)

    def parallel_bulk(self, actions, **kwargs):
        deque(parallel_bulk(client=self.connection, actions=actions, **kwargs), maxlen=0)
        return (1, [])  # Fake return value to emulate bulk(), not used upstream

    def _prepare_action(self, object_instance, action):
        return {
            '_op_type': action,
            '_index': str(self._doc_type.index),
            '_type': self._doc_type.mapping.doc_type,
            '_id': object_instance.pk,
            '_source': (
                self.prepare(object_instance) if action != 'delete' else None
            ),
        }

    def _get_actions(self, object_list, action):
        for object_instance in object_list:
            yield self._prepare_action(object_instance, action)

    def update(self, thing, refresh=None, action='index', **kwargs):
        """
        Update each document in ES for a model, iterable of models or queryset
        """
        if refresh is True or (
            refresh is None and self._doc_type.auto_refresh
        ):
            kwargs['refresh'] = True

        if isinstance(thing, models.Model):
            object_list = [thing]
        else:
            object_list = thing

        return self.parallel_bulk(
            self._get_actions(object_list, action), **kwargs
        )
