from django.db.models import Case, When
from django.db.models.fields import IntegerField
from elasticsearch.dsl import Search as DSLSearch


class Search(DSLSearch):
    def __init__(self, **kwargs):
        self._model = kwargs.pop('model', None)
        super(Search, self).__init__(**kwargs)

    def _clone(self):
        s = super(Search, self)._clone()
        s._model = self._model
        return s

    def filter_queryset(self, queryset, keep_search_order=True):
        """
        Filter an existing django queryset using the elasticsearch result.
        It costs a query to the sql db.
        """
        s = self
        if s._model is not queryset.model:
            raise TypeError(
                'Unexpected queryset model '
                '(should be: %s, got: %s)' % (s._model, queryset.model)
            )

        # Do not query again if the es result is already cached
        if not hasattr(self, '_response'):
            # We only need the meta fields with the models ids
            s = self.source(excludes=['*'])
            s = s.execute()

        pks = [result.meta.id for result in s]
        queryset = queryset.filter(pk__in=pks)

        if keep_search_order:
            preserved_order = Case(
                *[When(pk=pk, then=pos) for pos, pk in enumerate(pks)],
                output_field=IntegerField()
            )
            queryset = queryset.order_by(preserved_order)

        return queryset

    def _get_queryset(self):
        """
        Return a django queryset that will be filtered by to_queryset method.
        """
        return self._model._default_manager.all()

    def to_queryset(self, keep_order=True):
        """
        Return a django queryset from the elasticsearch result.
        It costs a query to the sql db.
        """
        qs = self._get_queryset()
        return self.filter_queryset(qs, keep_order)
