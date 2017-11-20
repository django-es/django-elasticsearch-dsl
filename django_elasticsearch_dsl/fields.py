import collections
from types import MethodType

from django.db import models
from django.db.models.fields.files import FieldFile
from django.utils.encoding import force_text
from django.utils.functional import Promise

from elasticsearch_dsl.field import (
    Attachment,
    Boolean,
    Byte,
    Completion,
    Date,
    Double,
    Field,
    Float,
    GeoPoint,
    GeoShape,
    Integer,
    Ip,
    Long,
    Nested,
    Object,
    Short,
    String,
)
from .exceptions import VariableLookupError


class DEDField(Field):
    def __init__(self, attr=None, **kwargs):
        super(DEDField, self).__init__(**kwargs)
        self._path = attr.split('.') if attr else []

    def __setattr__(self, key, value):
        if key == 'get_value_from_instance':
            self.__dict__[key] = value
        else:
            super(DEDField, self).__setattr__(key, value)

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        """
        Given an model instance to index with ES, return the value that
        should be put into ES for this field.
        """
        if not instance:
            return None

        for attr in self._path:
            try:
                instance = instance[attr]
            except (
                TypeError, AttributeError,
                KeyError, ValueError, IndexError
            ):
                try:
                    instance = getattr(instance, attr)
                except (TypeError, AttributeError):
                    try:
                        instance = instance[int(attr)]
                    except (
                        IndexError, ValueError,
                        KeyError, TypeError
                    ):
                        raise VariableLookupError(
                            "Failed lookup for key [{}] in "
                            "{!r}".format(attr, instance)
                        )

            if (isinstance(instance, models.manager.Manager)):
                instance = instance.all()
            elif callable(instance):
                instance = instance()
            elif instance is None:
                return None

        if instance == field_value_to_ignore:
            return None

        # convert lazy object like lazy translations to string
        if isinstance(instance, Promise):
            return force_text(instance)

        return instance


class ObjectField(DEDField, Object):
    def _get_inner_field_data(self, obj, field_value_to_ignore=None):
        data = {}
        for name, field in self.properties.to_dict().items():
            if not isinstance(field, DEDField):
                continue

            if field._path == []:
                field._path = [name]

            data[name] = field.get_value_from_instance(
                obj, field_value_to_ignore
            )

        return data

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        objs = super(ObjectField, self).get_value_from_instance(
            instance, field_value_to_ignore
        )

        if objs is None:
            return {}
        if isinstance(objs, collections.Iterable):
            return [
                self._get_inner_field_data(obj, field_value_to_ignore)
                for obj in objs if obj != field_value_to_ignore
            ]

        return self._get_inner_field_data(objs, field_value_to_ignore)


def ListField(field):
    """
    This wraps a field so that when get_value_from_instance
    is called, the field's values are iterated over
    """
    original_get_value_from_instance = field.get_value_from_instance

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        return [value for value in original_get_value_from_instance(instance)]

    field.get_value_from_instance = MethodType(get_value_from_instance, field)
    return field


class AttachmentField(DEDField, Attachment):
    pass


class BooleanField(DEDField, Boolean):
    pass


class ByteField(DEDField, Byte):
    pass


class CompletionField(DEDField, Completion):
    pass


class DateField(DEDField, Date):
    pass


class DoubleField(DEDField, Double):
    pass


class FloatField(DEDField, Float):
    pass


class GeoPointField(DEDField, GeoPoint):
    pass


class GeoShapeField(DEDField, GeoShape):
    pass


class IntegerField(DEDField, Integer):
    pass


class IpField(DEDField, Ip):
    pass


class LongField(DEDField, Long):
    pass


class NestedField(Nested, ObjectField):
    pass


class ShortField(DEDField, Short):
    pass


class StringField(DEDField, String):
    pass


class FileField(DEDField, String):
    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        _file = super(FileField, self).get_value_from_instance(
            instance, field_value_to_ignore)

        if isinstance(_file, FieldFile):
            return _file.url if _file else ''
        return _file


# ES5 specific fields
try:
    from elasticsearch_dsl.field import (
        Keyword,
        Text,
    )

    class KeywordField(DEDField, Keyword):
        pass

    class TextField(DEDField, Text):
        pass
except ImportError:
    pass
