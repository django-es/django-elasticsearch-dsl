from django.db.models import Case, When
from django.shortcuts import _get_queryset

from elasticsearch_dsl import Search as DSLSearch


class Search(DSLSearch):
    def __init__(self, **kwargs):
        self._model = kwargs.pop('model', None)
        super(Search, self).__init__(**kwargs)

    def _clone(self):
        s = super(Search, self)._clone()
        s._model = self._model
        return s

    def filter_queryset(self, klass, keep_search_order=True):
        """
        Filter an existing django queryset using the elasticsearch result.
        It costs a query to the sql db.
        klass may be a Model, Manager, or QuerySet object.
        """

        qs = _get_queryset(klass)
        s = self
        if s._model is not qs.model:
            raise TypeError(
                'Unexpected queryset model '
                '(should be: %s, got: %s)' % (s._model, qs.model)
            )

        # Do not query again if the es result is already cached
        if not hasattr(self, '_response'):
            # We only need the meta fields with the models ids
            s = self.source(excludes=['*'])
            s = s.execute()

        pks = [result.meta.id for result in s]
        qs = qs.filter(pk__in=pks)

        if keep_search_order:
            preserved_order = Case(
                *[When(pk=pk, then=pos) for pos, pk in enumerate(pks)]
            )
            qs = qs.order_by(preserved_order)

        return qs

    def to_queryset(self, keep_order=True):
        """
        Return a django queryset from the elasticsearch result.
        It costs a query to the sql db.
        """
        return self.filter_queryset(self._model, keep_order)
