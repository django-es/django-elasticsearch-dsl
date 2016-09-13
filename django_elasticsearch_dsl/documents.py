from __future__ import unicode_literals
from django.utils.six import add_metaclass, iteritems
from django.db import models
from elasticsearch.helpers import bulk
from elasticsearch_dsl.document import DocTypeMeta as DSLDocTypeMeta
from elasticsearch_dsl.field import Field
from elasticsearch_dsl import DocType as DSLDocType

from .exceptions import RedeclaredFieldError, ModelFieldNotMappedError
from .fields import (
    DEDField,
    StringField,
    DoubleField,
    ShortField,
    IntegerField,
    LongField,
    DateField,
    BooleanField,
)


model_field_class_to_field_class = {
    models.AutoField: IntegerField,
    models.BigIntegerField: LongField,
    models.BooleanField: BooleanField,
    models.CharField: StringField,
    models.DateField: DateField,
    models.DateTimeField: DateField,
    models.EmailField: StringField,
    models.FileField: StringField,
    models.FilePathField: StringField,
    models.FloatField: DoubleField,
    models.ImageField: StringField,
    models.IntegerField: IntegerField,
    models.NullBooleanField: BooleanField,
    models.PositiveIntegerField: IntegerField,
    models.PositiveSmallIntegerField: ShortField,
    models.SlugField: StringField,
    models.SmallIntegerField: ShortField,
    models.TextField: StringField,
    models.TimeField: LongField,
    models.URLField: StringField,
}


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
        model_field_names = getattr(attrs['Meta'], "fields", [])
        class_fields = set(
            name for name, field in iteritems(attrs)
            if isinstance(field, Field)
        )

        cls = super_new(cls, name, bases, attrs)

        cls._doc_type.model = model
        cls._doc_type.ignore_signals = ignore_signals

        doc = cls()

        fields = model._meta.get_fields()
        fields_lookup = dict((field.name, field) for field in fields)

        for field_name in model_field_names:
            if field_name in class_fields:
                raise RedeclaredFieldError(
                    "You cannot redeclare the field named '{}' on {}"
                    .format(field_name, cls.__name__)
                )

            field_instance = doc.to_field(field_name,
                                          fields_lookup[field_name])
            cls._doc_type.mapping.field(field_name, field_instance)

        cls._doc_type._fields = (
            lambda: cls._doc_type.mapping.properties.properties.to_dict())
        return cls


@add_metaclass(DocTypeMeta)
class DocType(DSLDocType):

    def __eq__(self, other):
        return id(self) == id(other)

    def __hash__(self):
        return id(self)

    def get_queryset(self):
        """
        Return the queryset that should be indexed by this doc type.
        """
        qs = self._doc_type.model._default_manager
        return qs

    def prepare(self, instance):
        """
        Take a model instance, and turn it into a dict that can be serialized
        based on the fields defined on this DocType subclass
        """
        data = {}
        for name, field in iteritems(self._doc_type._fields()):
            if not isinstance(field, DEDField):
                continue

            if field._path == []:
                field._path = [name]

            prep_func = getattr(
                self,
                "prepare_" + name,
                field.get_value_from_instance
            )
            data[name] = prep_func(instance)

        return data

    def to_field(self, field_name, model_field):
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

    def bulk(self, actions, refresh=True, **kwargs):
        return bulk(client=self.connection, actions=actions,
                    refresh=refresh, **kwargs)

    def update(self, thing, refresh=True, action='index', **kwargs):
        """
        Update each document in ES for a model, iterable of models or queryset
        """
        kwargs['refresh'] = refresh
        if isinstance(thing, models.Model):
            thing = [thing]

        actions = ({
            '_op_type': action,
            '_index': str(self._doc_type.index),
            '_type': self._doc_type.mapping.doc_type,
            '_id': model.pk,
            '_source': self.prepare(model) if action != 'delete' else None,
        } for model in thing)

        return self.bulk(actions, **kwargs)
