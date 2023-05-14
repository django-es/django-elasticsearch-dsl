from typing import List, Union

from django.db import models

from .utils import get_queryset_by_ids
from ..registries import registry


class DjangoElasticsearchDslManagerMixin(object):
    """Elasticsearch DSL manager mixin for processing mass work with objects.

    Performs normalization by supported types and causes updating the
    search engine appropriately.

    It acts similarly to a signal processor.
    """
    _registry = registry

    def _normalize_results(self, result) -> Union[List[models.Model], models.QuerySet]:
        if isinstance(result, models.Model):
            return [result]
        elif isinstance(result, (list, models.QuerySet)):
            return result
        else:
            raise TypeError(
                "Incorrect results type. "
                "Expected 'django.db.models.Model', <class 'list'> or 'django.db.models.Queryset', "
                "but got %s" % type(result)
            )

    def _handle_save(self, result):
        """Handle save.

        Given a many model instances, update the objects in the index.
        Update the related objects either.
        """
        results = self._normalize_results(result)

        self._registry.update(results)
        self._registry.update_related(results, many=True)

    def _handle_pre_delete(self, result):
        """Handle removing of objects from related models instances.

        We need to do this before the real delete otherwise the relation
        doesn't exist anymore, and we can't get the related models instances.
        """
        results = self._normalize_results(result)

        self._registry.delete_related(
            results,
            many=True,
            raise_on_error=False,
        )

    def _handle_delete(self, result):
        """Handle delete.

        Given a many model instances, delete the objects in the index.
        """
        results = self._normalize_results(result)

        self._registry.delete(
            results,
            raise_on_error=False,
        )


class DjangoElasticsearchDslModelManager(models.QuerySet, DjangoElasticsearchDslManagerMixin):
    """Django Elasticsearch Dsl model manager.

    Working with possible bulk operations, updates documents accordingly.
    """

    def bulk_create(self, objs, *args, **kwargs):
        """Bulk create.

        Calls `handle_save` after saving is completed
        """
        result = super().bulk_create(objs, *args, **kwargs)
        self._handle_save(result)
        return result

    def bulk_update(self, objs, *args, **kwargs):
        """Bulk update.

        Calls `handle_save` after saving is completed
        """
        result = super().bulk_update(objs, *args, **kwargs)
        self._handle_save(objs)
        return result

    def update(self, **kwargs):
        """Update.

        Calls `handle_save` after saving is completed
        """
        ids = list(self.values_list("id", flat=True))
        result = super().update(**kwargs)
        if not ids:
            return result
        self._handle_save(get_queryset_by_ids(self.model, ids))
        return result

    def delete(self):
        """Delete.

        Calls `handle_pre_delete` before performing the deletion.

        After deleting it causes `handle_delete`.
        """
        objs = get_queryset_by_ids(self.model, list(self.values_list("id", flat=True)))
        self._handle_pre_delete(objs)
        objs = list(objs)

        result = super().delete()

        self._handle_delete(objs)

        return result
