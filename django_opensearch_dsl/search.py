from django.db.models import Case, When
from django.db.models.fields import IntegerField

from opensearch_dsl import Search as DSLSearch
from opensearch_dsl.connections import connections


class Search(DSLSearch):
    def __init__(self, **kwargs):
        self._model = kwargs.pop('model', None)
        super(Search, self).__init__(**kwargs)

    def _clone(self):
        s = super(Search, self)._clone()
        s._model = self._model
        return s

    def to_queryset(self, keep_order=False):
        """
        This method return a django queryset from the an opensearch result.
        It cost a query to the sql db.
        """
        s = self

        # Do not query again if the search result is already cached
        if not hasattr(self, '_response'):
            # We only need the meta fields with the models ids
            s = self.source(excludes=['*'])
            s = s.execute()

        pks = [result.meta.id for result in s]

        qs = self._model.objects.filter(pk__in=pks)

        if keep_order:
            preserved_order = Case(
                *[When(pk=pk, then=pos) for pos, pk in enumerate(pks)],
                output_field=IntegerField()
            )
            qs = qs.order_by(preserved_order)

        return qs

    def validate(self, explain=False):
        response = connections.get_connection().indices.validate_query(
            body=self.to_dict(), index=self._index[0], explain=True
        )

        if not explain:
            return response["valid"]

        if response["valid"]:
            return True, []

        try:
            return False, [response["error"]]
        except KeyError:
            return False, response["explanations"]
