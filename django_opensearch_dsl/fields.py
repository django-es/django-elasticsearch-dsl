from types import MethodType
from typing import Iterable

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.fields.files import FieldFile
from django.utils.encoding import force_str
from django.utils.functional import Promise
from opensearch_dsl import field as fields

from .exceptions import VariableLookupError

__all__ = [
    "DODField",
    "ObjectField",
    "ListField",
    "BooleanField",
    "ByteField",
    "CompletionField",
    "DateField",
    "DoubleField",
    "FloatField",
    "ScaledFloatField",
    "GeoPointField",
    "GeoShapeField",
    "IntegerField",
    "IpField",
    "LongField",
    "NestedField",
    "ShortField",
    "KeywordField",
    "TextField",
    "SearchAsYouTypeField",
    "FileFieldMixin",
    "FileField",
]


class DODField(fields.Field):
    """Field allowing to retrieve a value from a `Model` instance."""

    def __init__(self, attr=None, **kwargs):
        super(DODField, self).__init__(**kwargs)
        self._path = attr.split(".") if attr else []

    def __setattr__(self, key, value):
        if key == "get_value_from_instance":
            self.__dict__[key] = value
        else:
            super(DODField, self).__setattr__(key, value)

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        """Retrieve the value to index for the given instance."""
        if instance is None:
            return None

        for attr in self._path:
            try:
                instance = instance[attr]
            except (TypeError, AttributeError, KeyError, ValueError, IndexError):
                try:
                    instance = getattr(instance, attr)
                except ObjectDoesNotExist:  # pragma: no cover
                    return None
                except (TypeError, AttributeError):
                    try:
                        instance = instance[int(attr)]
                    except (IndexError, ValueError, KeyError, TypeError):
                        if self._required:
                            raise VariableLookupError("Failed lookup for key [{}] in " "{!r}".format(attr, instance))
                        return None

            if isinstance(instance, models.manager.Manager):
                instance = instance.all()
            elif callable(instance):
                instance = instance()
            elif instance is None:
                return None

        if instance == field_value_to_ignore:
            return None

        # convert lazy object like lazy translations to string
        if isinstance(instance, Promise):
            return force_str(instance)

        return instance


class ObjectField(DODField, fields.Object):
    """Allow indexing of `OneToOneRel`, `OneToOneField` or `ForeignKey`."""

    def _get_inner_field_data(self, obj, field_value_to_ignore=None):
        """Compute the dictionary to index according to the field parameters."""
        data = {}

        properties = self._doc_class._doc_type.mapping.properties._params.get("properties", {}).items()  # noqa
        for name, field in properties:
            if not isinstance(field, DODField):  # pragma: no cover
                continue

            if field._path == []:  # noqa
                field._path = [name]

            # This allows for retrieving data from an InnerDoc with
            # 'prepare_field_[name]' functions.
            doc_instance = self._doc_class()
            prep_func = getattr(doc_instance, "prepare_%s" % name, None)

            if prep_func:
                data[name] = prep_func(obj)
            else:
                data[name] = field.get_value_from_instance(obj, field_value_to_ignore)

        # This allows for ObjectFields to be indexed from dicts with
        # dynamic keys (i.e. keys/fields not defined in 'properties')
        if not data and obj and isinstance(obj, dict):
            data = obj

        return data

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        """Return the dictionary to index."""
        objs: Iterable = super(ObjectField, self).get_value_from_instance(instance, field_value_to_ignore)

        if objs is None:
            return {}
        try:
            is_iterable = bool(iter(objs))
        except TypeError:
            is_iterable = False

        # While dicts are iterable, they need to be excluded here so
        # their full data is indexed
        if is_iterable and not isinstance(objs, dict):
            return [
                self._get_inner_field_data(obj, field_value_to_ignore) for obj in objs if obj != field_value_to_ignore
            ]

        return self._get_inner_field_data(objs, field_value_to_ignore)


def ListField(field):  # noqa
    """Wrap a field so that its value is iterated over."""

    original_get_value_from_instance = field.get_value_from_instance

    def get_value_from_instance(self, instance):
        if not original_get_value_from_instance(instance):  # pragma: no cover
            return []
        return [value for value in original_get_value_from_instance(instance)]

    field.get_value_from_instance = MethodType(get_value_from_instance, field)
    return field


class BooleanField(DODField, fields.Boolean):
    """Allow indexing of `bool`."""


class ByteField(DODField, fields.Byte):
    """Allow indexing of byte.

    Should be used for integer with a minimum value of -128 and a maximum value
    of 127.
    """


class CompletionField(DODField, fields.Completion):
    """Used for auto-complete suggestions."""


class DateField(DODField, fields.Date):
    """Allow indexing of date and timestamp."""


class DoubleField(DODField, fields.Double):
    """Allow indexing of double.

    Should be used for double-precision 64-bit IEEE 754 floating point number,
    restricted to finite values.
    """


class FloatField(DODField, fields.Float):
    """Allow indexing of float.

    Should be used for single-precision 32-bit IEEE 754 floating point number,
    restricted to finite values.
    """


class ScaledFloatField(DODField, fields.ScaledFloat):
    """Allow indexing of scaled float.

    Should be used for floating point number that is backed by a long,
    scaled by a fixed double scaling factor. .
    """


class GeoPointField(DODField, fields.GeoPoint):
    """Allow indexing of latitude and longitude points."""


class GeoShapeField(DODField, fields.GeoShape):
    """Allow indexing of complex shapes, such as polygons."""


class IntegerField(DODField, fields.Integer):
    """Allow indexing of integer.

    Should be used for integer with a minimum value of -2^31 and a maximum value
    of 2^31 - 1.
    """


class IpField(DODField, fields.Ip):
    """Allow indexing of IPv4 and IPv6 addresses."""


class LongField(DODField, fields.Long):
    """Allow indexing of long.

    Should be used for integer with a minimum value of -2^63 and a
    maximum value of 2^63 - 1.
    """


class NestedField(fields.Nested, ObjectField):
    """Allow indexing of ManyToOneRel, ManyToManyField or ManyToManyRel."""


class ShortField(DODField, fields.Short):
    """Allow indexing or long.

    Should be used for integer with a minimum value of -32768 and a maximum
    value of 32767.
    """


class KeywordField(DODField, fields.Keyword):
    """Allow indexing of structured text (ID, zip codes, tags, ...)."""


class TextField(DODField, fields.Text):
    """Allow indexing of unstructured text."""


class SearchAsYouTypeField(DODField, fields.SearchAsYouType):
    """Allow indexing of text-like type for as-you-type completion."""


class FileFieldMixin:
    """Mixin allowing the indexing of Django `FileField`."""

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        """Retrieve the url from the `FileField`."""
        _file = super(FileFieldMixin, self).get_value_from_instance(instance, field_value_to_ignore)

        if isinstance(_file, FieldFile):
            return _file.url if _file else ""
        return _file if _file else ""


class FileField(FileFieldMixin, DODField, fields.Text):
    """Index the URL associated with a Django `FileField`."""
