import io
import sys
import time
from collections import deque
from functools import partial
from typing import Optional, Iterable

from django.db import models
from django.db.models import QuerySet, Q
from opensearch_dsl import Document as DSLDocument
from opensearchpy.helpers import bulk, parallel_bulk

from . import fields
from .apps import DEDConfig
from .exceptions import ModelFieldNotMappedError
from .management.enums import OpensearchAction
from .search import Search
from .signals import post_index

model_field_class_to_field_class = {
    models.AutoField: fields.IntegerField,
    models.BigAutoField: fields.LongField,
    models.BigIntegerField: fields.LongField,
    models.BooleanField: fields.BooleanField,
    models.CharField: fields.TextField,
    models.DateField: fields.DateField,
    models.DateTimeField: fields.DateField,
    models.DecimalField: fields.DoubleField,
    models.EmailField: fields.TextField,
    models.FileField: fields.FileField,
    models.FilePathField: fields.KeywordField,
    models.FloatField: fields.DoubleField,
    models.ImageField: fields.FileField,
    models.IntegerField: fields.IntegerField,
    models.NullBooleanField: fields.BooleanField,
    models.PositiveIntegerField: fields.IntegerField,
    models.PositiveSmallIntegerField: fields.ShortField,
    models.SlugField: fields.KeywordField,
    models.SmallIntegerField: fields.ShortField,
    models.TextField: fields.TextField,
    models.TimeField: fields.LongField,
    models.URLField: fields.TextField,
    models.UUIDField: fields.KeywordField,
}


class Document(DSLDocument):
    _prepared_fields = []

    def __init__(self, **kwargs):
        super(Document, self).__init__(**kwargs)
        self._prepared_fields = self.init_prepare()

    @classmethod
    def search(cls, using=None, index=None):
        return Search(
            using=cls._get_using(using), index=cls._default_index(index), doc_type=[cls], model=cls.django.model
        )

    def get_queryset(self, filter_: Optional[Q] = None, exclude: Optional[Q] = None, count: int = None) -> QuerySet:
        """Return the queryset that should be indexed by this doc type."""
        qs = self.django.model.objects.all()

        if filter_:
            qs = qs.filter(filter_)
        if exclude:
            qs = qs.exclude(exclude)
        if count is not None:
            qs = qs[:count]

        return qs

    def _eta(self, start, done, total):  # pragma: no cover
        if done == 0:
            return "~"
        eta = round((time.time() - start) / done * (total - done))
        unit = "secs"
        if eta > 120:
            eta //= 60
            unit = "mins"
        return f"{eta} {unit}"

    def get_indexing_queryset(self, verbose: bool = False, filter_: Optional[Q] = None, exclude: Optional[Q] = None,
                              count: int = None, action: OpensearchAction = OpensearchAction.INDEX,
                              stdout: io.FileIO = sys.stdout) -> Iterable:
        """Divide the queryset into chunks."""
        chunk_size = self.django.queryset_pagination
        qs = self.get_queryset(filter_=filter_, exclude=exclude, count=count)
        count = qs.count()
        model = self.django.model.__name__
        action = action.present_participle.title()

        i = 0
        done = 0
        start = time.time()
        if verbose:
            stdout.write(f"{action} {model}: 0% ({self._eta(start, done, count)})\r")
        while done < count:
            if verbose:
                stdout.write(f"{action} {model}: {round(i / count * 100)}% ({self._eta(start, done, count)})\r")

            for obj in qs[i: i + chunk_size]:
                done += 1
                yield obj

            i = min(i + chunk_size, count)

        if verbose:
            stdout.write(f"{action} {count} {model}: OK          \n")

    def init_prepare(self):
        """Initialise the data model preparers once here.

        Extracts the preparers from the model and generate a list of callables
        to avoid doing that work on every object instance over.
        """
        index_fields = getattr(self, '_fields', {})
        preparers = []
        for name, field in iter(index_fields.items()):
            if not isinstance(field, fields.DEDField):  # pragma: no cover
                continue

            if not field._path:  # noqa
                field._path = [name]

            prep_func = getattr(self, 'prepare_%s' % name, None)
            fn = prep_func if prep_func else partial(field.get_value_from_instance)

            preparers.append((name, field, fn))

        return preparers

    def prepare(self, instance):
        """
        Take a model instance, and turn it into a dict that can be serialized
        based on the fields defined on this DocType subclass
        """
        data = {
            name: prep_func(instance)
            for name, field, prep_func in self._prepared_fields
        }
        return data

    @classmethod
    def to_field(cls, field_name, model_field):
        """
        Returns the opensearch field instance appropriate for the model
        field class. This is a good place to hook into if you have more complex
        model field to ES field logic
        """
        try:
            return model_field_class_to_field_class[
                model_field.__class__](attr=field_name)
        except KeyError:  # pragma: no cover
            raise ModelFieldNotMappedError(
                f"Cannot convert model field {field_name} to an Opensearch field!"
            )

    def bulk(self, actions, **kwargs):

        response = bulk(client=self._get_connection(), actions=actions, **kwargs)
        # send post index signal
        post_index.send(
            sender=self.__class__,
            instance=self,
            actions=actions,
            response=response
        )
        return response

    def parallel_bulk(self, actions, **kwargs):
        kwargs.setdefault('chunk_size', self.django.queryset_pagination)
        bulk_actions = parallel_bulk(client=self._get_connection(), actions=actions, **kwargs)
        # As the `parallel_bulk` is lazy, we need to get it into `deque` to run
        # it instantly.
        # See https://discuss.elastic.co/t/helpers-parallel-bulk-in-python-not-working/39498/2  # noqa
        deque(bulk_actions, maxlen=0)
        # Fake return value to emulate bulk() since we don't have a result yet,
        # the result is currently not used upstream anyway.
        return 1, []

    @classmethod
    def generate_id(cls, object_instance):
        """
        The default behavior is to use the Django object's pk (id) as the
        opensearch index id (_id). If needed, this method can be overloaded
        to change this default behavior.
        """
        return object_instance.pk

    def _prepare_action(self, object_instance, action):
        return {
            '_op_type': action,
            '_index': self._index._name,  # noqa
            '_id': self.generate_id(object_instance),
            '_source' if action != 'update' else 'doc': (
                self.prepare(object_instance) if action != 'delete' else None
            ),
        }

    def _get_actions(self, object_list, action):
        for object_instance in object_list:
            if action == 'delete' or self.should_index_object(object_instance):
                yield self._prepare_action(object_instance, action)

    def _bulk(self, *args, parallel=False, **kwargs):
        """Helper for switching between normal and parallel bulk operation"""
        if parallel:
            return self.parallel_bulk(*args, **kwargs)
        return self.bulk(*args, **kwargs)

    def should_index_object(self, obj):
        """
        Overwriting this method and returning a boolean value
        should determine whether the object should be indexed.
        """
        return True

    def update(self, thing, action, *args, refresh=None, **kwargs):  # noqa
        """Update document in ES for a model, iterable of models or queryset."""
        if refresh is None:
            refresh = getattr(self.Index, "auto_refresh", DEDConfig.auto_refresh_enabled())

        if isinstance(thing, models.Model):
            object_list = [thing]
        else:
            object_list = thing

        return self._bulk(self._get_actions(object_list, action), *args, refresh=refresh, **kwargs)
