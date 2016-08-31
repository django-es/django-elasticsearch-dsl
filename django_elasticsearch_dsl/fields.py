import collections
from types import MethodType
from elasticsearch_dsl.field import (Object, Nested, Date, String,
                                     FIELDS, Field, Boolean)
from elasticsearch_dsl.utils import _make_dsl_class
from .exceptions import VariableLookupError


class DEDField(Field):
    def __init__(self, attr=None, **kwargs):
        super(DEDField, self).__init__(**kwargs)
        self._path = attr.split(".") if attr else []

    def __setattr__(self, key, value):
        if key == "get_value_from_instance":
            self.__dict__[key] = value
        else:
            super(DEDField, self).__setattr__(key, value)

    def get_value_from_instance(self, instance):
        """
        Given an model instance to index with ES, return the value that
        should be put into ES for this field.
        """
        if not instance:
            return None

        for attr in self._path:
            try:
                instance = instance[attr]
            except (TypeError, AttributeError,
                    KeyError, ValueError, IndexError):
                try:
                    instance = getattr(instance, attr)
                except (TypeError, AttributeError):
                    try:
                        instance = instance[int(attr)]
                    except (IndexError,
                            ValueError,
                            KeyError,
                            TypeError):
                                raise VariableLookupError(
                                    "Failed lookup for key [{}] in "
                                    "{!r}".format(attr, instance)
                                )

            if callable(instance):
                instance = instance()
            elif instance is None:
                return None

        return instance


class StringField(DEDField, String):
    pass


class BooleanField(DEDField, Boolean):
    pass


class DateField(DEDField, Date):
    pass


class ObjectField(DEDField, Object):
    def _get_inner_field_data(self, obj):
        data = {}
        for name, field in self.properties.to_dict().items():
            if not isinstance(field, DEDField):
                continue

            if field._path == []:
                field._path = [name]

            data[name] = field.get_value_from_instance(obj)

        return data

    def get_value_from_instance(self, instance):
        objs = super(ObjectField, self).get_value_from_instance(instance)

        if objs is None:
            return None
        if isinstance(objs, collections.Iterable):
            return [self._get_inner_field_data(obj) for obj in objs]

        return self._get_inner_field_data(objs)


class NestedField(ObjectField, Nested):
    pass


def ListField(field):
    """
    This wraps a field so that when get_value_from_instance
    is called, the field's values are iterated over
    """
    original_get_value_from_instance = field.get_value_from_instance

    def get_value_from_instance(self, instance):
        return [value for value in original_get_value_from_instance(instance)]

    field.get_value_from_instance = MethodType(get_value_from_instance, field)
    return field


for f in FIELDS:
    fclass = _make_dsl_class(DEDField, f, suffix="Field")
    globals()[fclass.__name__] = fclass
