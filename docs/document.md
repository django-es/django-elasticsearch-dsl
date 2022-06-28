Documents Classes
================

## `Django` subclass

The `Django` subclass contains parameters related to Django's side of the document :

* `model` (*required*) - Model that will be used for the indexing.
* `fields` (*optional*) - List model's field name that should be indexed. Do not add the fields you manually declare
  into this list. See [Document Field Reference](fields.md) for how to manually define fields.
* `queryset_pagination` (*optional*) - Size of the chunk when indexing,
  override [`OPENSEARCH_DSL_QUERYSET_PAGINATION`](settings.md#opensearch_dsl_queryset_pagination.md).
* `related_models` (*optional*) - List of related Django models. Specifies a relation between models that allows for
  index updating based on these defined relationships.

```python
class Country(models.Model):
    name = models.CharField(max_length=255, unique=True)
    area = models.BigIntegerField()
    population = models.BigIntegerField()
    continent = models.ForeignKey(Continent, models.CASCADE, related_name="countries")


@registry.register_document
class CountryDocument(Document):
    class Django:
        model = Country
        queryset_pagination = 128
        fields = [
            'name',
            'area',
            'population',
        ]
        related_models = []

    id = fields.LongField()
    continent = fields.ObjectField(properties={
        'id': fields.LongField(),
        'name': fields.KeywordField(),
    })
```

These parameters can be access through the `django` attribute of `Document`'s instance (
e.g `CountryDocument().django.model`)

## `Index` subclass

This subclass contains parameters about Opensearch :

* `name` (*required*) - Name of the index.
* `auto_refresh` (*required*) - Perform an index refresh after every update if `True` (
  overrides [`OPENSEARCH_DSL_AUTO_REFRESH`](settings.md#opensearch_dsl_auto_refresh))
* `settings` (*optional*) - Settings of the index, will be merged
  with [`OPENSEARCH_DSL_INDEX_SETTINGS`](settings.md#opensearch_dsl_index_settings) (settings define here prevail over
  the ones defined in `OPENSEARCH_DSL_INDEX_SETTINGS`).

  For a list of settings,
  see [Opensearch's index settings](https://opensearch.org/docs/latest/opensearch/rest-api/index-apis/create-index/#index-settings)
  .

## Manually defined fields

In addition to `Document.Django.fields`, you can manually define any number of fields. For more information about
fields, see the [Document Field Reference](fields.md).

## Indexing data

The data to index is obtained through 3 methods :

* `get_queryset()` which return the base queryset.
* `get_indexing_queryset()` which divide the queryset into manageable chunk for Opensearch.
* `should_index_object()` Which individually filter out objects that should not be indexed.

By subclassing one or more of these methods, you can choose which objects you want to index, as well as optimize the
queryset used to fetch the data.

---

* `def get_queryset(self, filter_=None, exclude=None, count=None)`

    * `filter_` (`Optional[Q]`) - `Q` object given to the queryset's `filter()` method.
    * `exclude` (`Optional[Q]`) - `Q` object given to the queryset's `exclude()` method.
    * `count` (`Optional[int]`) - Limit the queryset with the given number.

By default, this method retrieves all objects from the model associated with the `Document`, optionally filtering and
excluding elements according to the given arguments. You can also limit the number of results using the `count` argument.

You can inherit this method to modify the queryset, this can be useful if you need to select or prefetch related models
to make the indexing faster, or to create an annotation to use as a field.

Example:

```python
@registry.register_document
class EventDocument(Document):
    class Index:
        name = 'event'

    class Django:
        model = Event

    country = fields.ObjectField(doc_class=CountryDocument)

    def get_queryset(self, filter_: Optional[Q] = None, exclude: Optional[Q] = None, count: int = 0) -> QuerySet:
        """Select country to improve indexing performance."""
        return super().get_queryset(filter_=filter_, exclude=exclude, count=count).select_related('country')
```

---

* `def get_indexing_queryset(self, filter_=None, exclude=None, count=None, verbose=False, action=OpensearchAction.INDEX, stdout=sys.stdout)`

    * `filter_` (`Optional[Q]`) - Given to `get_queryset()`.
    * `exclude` (`Optional[Q]`) - Given to `get_queryset()`.
    * `count` (`Optional[int]`) - Given to `get_queryset()`.
    * `verbose` (`bool`) - If set to `True`, will display the progression of the action on standard output.
    * `action` (`OpensearchAction`) - Used by the verbose.
    * `stdout` (`io.FileIO`) - Standard output used when verbose is `True` (default to `stdout`).

This method chunks manually the queryset before sending them to Opensearch while displaying the progression and time
remaining on stdout.

You can override this method to change the method of chunking (default implementation create a generator by chunking
manually the queryset into smaller queryset), or the way the verbose is handled.

Example:

```python
@registry.register_document
class EventDocument(Document):
    class Index:
        name = 'event'

    class Django:
        model = Event

    def get_indexing_queryset(self):
        """Use iterator to chunk the queryset, discarding any verbose."""
        qs = self.get_queryset()
        return qs.iterator()
```

* `def should_index_object(self, obj)`

    * `obj` (`Model`) - Object about to be indexed

This method is called for every object in the queryset. Return `False` if the object should not be indexed.


## Document ID

The Opensearch document id (`_id`) is not strictly speaking a field, as it is not part of the document itself. The
default behavior of `django_opensearch_dsl` is to use the primary key of the model as the document's id (`pk` or `id`).
Nevertheless, it can sometimes be useful to change this default behavior. For this, one can redefine
the `generate_id(cls, instance)` class method of the `Document` class.

For example, to use an article's slug as the Opensearch `_id` instead of the article's integer id, one could use:

```python
# models.py

class Article(models.Model):
    # ... #

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    # ... #
```

```python
# documents.py

class ArticleDocument(Document):
    class Django:
        model = Article

    # ... #

    @classmethod
    def generate_id(cls, article):
        return article.slug
```
