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
    'DEDField', 'ObjectField', 'ListField', 'BooleanField', 'ByteField', 'CompletionField', 'DateField', 'DoubleField',
    'FloatField', 'ScaledFloatField', 'GeoPointField', 'GeoShapeField', 'IntegerField', 'IpField', 'LongField',
    'NestedField', 'ShortField', 'KeywordField', 'TextField', 'SearchAsYouTypeField', 'FileFieldMixin', 'FileField',
]


class DEDField(fields.Field):

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
        if instance is None:
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
                except ObjectDoesNotExist:  # pragma: no cover
                    return None
                except (TypeError, AttributeError):
                    try:
                        instance = instance[int(attr)]
                    except (
                        IndexError, ValueError,
                        KeyError, TypeError
                    ):
                        if self._required:
                            raise VariableLookupError(
                                "Failed lookup for key [{}] in "
                                "{!r}".format(attr, instance)
                            )
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


class ObjectField(DEDField, fields.Object):

    def _get_inner_field_data(self, obj, field_value_to_ignore=None):
        data = {}

        properties = self._doc_class._doc_type.mapping.properties._params.get(  # noqa
            'properties', {}
        ).items()
        for name, field in properties:
            if not isinstance(field, DEDField):  # pragma: no cover
                continue

            if field._path == []:  # noqa
                field._path = [name]

            # This allows for retrieving data from an InnerDoc with
            # 'prepare_field_[name]' functions.
            doc_instance = self._doc_class()
            prep_func = getattr(doc_instance, 'prepare_%s' % name, None)

            if prep_func:
                data[name] = prep_func(obj)
            else:
                data[name] = field.get_value_from_instance(
                    obj, field_value_to_ignore
                )

        # This allows for ObjectFields to be indexed from dicts with
        # dynamic keys (i.e. keys/fields not defined in 'properties')
        if not data and obj and isinstance(obj, dict):
            data = obj

        return data

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        objs: Iterable = super(ObjectField, self).get_value_from_instance(
            instance, field_value_to_ignore
        )

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

    def get_value_from_instance(self, instance):
        if not original_get_value_from_instance(instance):  # pragma: no cover
            return []
        return [value for value in original_get_value_from_instance(instance)]

    field.get_value_from_instance = MethodType(get_value_from_instance, field)
    return field


class BooleanField(DEDField, fields.Boolean):
    pass


class ByteField(DEDField, fields.Byte):
    pass


class CompletionField(DEDField, fields.Completion):
    pass


class DateField(DEDField, fields.Date):
    pass


class DoubleField(DEDField, fields.Double):
    pass


class FloatField(DEDField, fields.Float):
    pass


class ScaledFloatField(DEDField, fields.ScaledFloat):
    pass


class GeoPointField(DEDField, fields.GeoPoint):
    pass


class GeoShapeField(DEDField, fields.GeoShape):
    pass


class IntegerField(DEDField, fields.Integer):
    pass


class IpField(DEDField, fields.Ip):
    pass


class LongField(DEDField, fields.Long):
    pass


class NestedField(fields.Nested, ObjectField):
    pass


class ShortField(DEDField, fields.Short):
    pass


class KeywordField(DEDField, fields.Keyword):
    pass


class TextField(DEDField, fields.Text):
    pass


class SearchAsYouTypeField(DEDField, fields.SearchAsYouType):
    pass


class FileFieldMixin:

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        _file = super(FileFieldMixin, self).get_value_from_instance(
            instance, field_value_to_ignore
        )

        if isinstance(_file, FieldFile):
            return _file.url if _file else ''
        return _file if _file else ''


class FileField(FileFieldMixin, DEDField, fields.Text):
    pass
