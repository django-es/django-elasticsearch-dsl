Document Field Reference
========================

The `django_opensearch_dsl.fields` are subclasses
of [`opensearch-dsl-py`'s fields](http://elasticsearch-dsl.readthedocs.io/en/stable/persistence.html#mappings). They
just add support for retrieving data from Django models.

## Available Fields

- Simple Fields

    - `BooleanField(attr=None, **opensearch_properties)`
    - `ByteField(attr=None, **opensearch_properties)`
    - `CompletionField(attr=None, **opensearch_properties)`
    - `DateField(attr=None, **opensearch_properties)`
    - `DoubleField(attr=None, **opensearch_properties)`
    - `FileField(attr=None, **opensearch_properties)`
    - `FloatField(attr=None, **opensearch_properties)`
    - `IntegerField(attr=None, **opensearch_properties)`
    - `IpField(attr=None, **opensearch_properties)`
    - `KeywordField(attr=None, **opensearch_properties)`
    - `GeoPointField(attr=None, **opensearch_properties)`
    - `GeoShapeField(attr=None, **opensearch_properties)`
    - `ShortField(attr=None, **opensearch_properties)`
    - `TextField(attr=None, **opensearch_properties)`

- Complex Fields

    - `ObjectField(properties, attr=None, **opensearch_properties)`
    - `NestedField(properties, attr=None, **opensearch_properties)`
      <br><br>
      `properties` is a `dict` where the key is a field name, and the value is a field instance.

## Using `attr` Argument

The `attr` argument allows you to retrieve the value from an attribute named differently than the Opensearch's fields. Such
an attribute can be :

* An actual attribute.
* A property.
* A method with no positional argument.
* An key (if the instance is a `Mapping`).

For example, let's say you don't want to store the type of the car as an `int`, but as the corresponding `str` instead.
You need some way to convert the type field on the model to a string, so we'll just add a method for it:

```python
# models.py

class Car(models.Model):

    # ... #
    def type_to_string(self):
        """Convert the type field to its string representation
        (the boneheaded way).
        """
        if self.type == 1:
            return "Sedan"
        elif self.type == 2:
            return "Truck"
        else:
            return "SUV"
```

Now we need to tell our `Document` subclass to use that method instead of just accessing the `type` field on the model
directly. Change the `CarDocument` to look like this:

```python
# documents.py

@registry.register_document
class CarDocument(Document):
    # add a string field to the Opensearch mapping called type, the
    # value of which is derived from the model's type_to_string attribute
    type = fields.TextField(attr="type_to_string")

    class Django:
        model = Car
        # we removed the type field from here
        fields = [
            'name',
            'color',
            'description',
        ]
```

## Using `prepare_[field]`

Sometimes, you need to do some extra prepping before a field should be saved to Opensearch. You can add
a `prepare_[field](self, instance)` method to a `Document` (where `foo` is the name of the field), and that method will
be called when the field needs to be saved.

```python
# documents.py

class CarDocument(Document):
    # ... #

    foo = TextField()

    def prepare_foo(self, instance):
        return " ".join(instance.foos)
```

## Using `prepare_[field]_with_related`

Allows you to do extra prepping before a field with related models should be saved to Opensearch. This ensures that
the index is updated appropriately. You can add a `prepare_[field]_with_related(self, instance)` method to a 
`Document` (where `foo` is the name of the field), and that method will be called when the field needs to be saved.

```python
# documents.py

class CarDocument(Document):
    # ... #

    class Django:
        fields = ["name", "price"]
        model = Car
        related_models = [Manufacturer]

    foo = TextField()

    def prepare_foo_with_related(self, instance):
        return " ".join(instance.foos)
```

## Handle relationship with `NestedField` / `ObjectField`

To represent relationships, you can use `NestedField` for :

* `ManyToManyField`
* `ManyToManyRel`
* `ManyToOneRel`

and `ObjectField` for :

* `ForeignKey`
* `OneToOneField`
* `OneToOneRel`

For example for a model with `ForeignKey` relationships.

```python
# models.py

class Car(models.Model):
    name = models.CharField()
    color = models.CharField()
    manufacturer = models.ForeignKey('Manufacturer')


class Manufacturer(models.Model):
    name = models.CharField()
    country_code = models.CharField(max_length=2)
    created = models.DateField()


class Ad(models.Model):
    title = models.CharField()
    description = models.TextField()
    created = models.DateField(auto_now_add=True)
    modified = models.DateField(auto_now=True)
    url = models.URLField()
    car = models.ForeignKey('Car', related_name='ads')
```

You can use an `ObjectField` or a `NestedField` as such :

```python
# documents.py

@registry.register_document
class CarDocument(Document):
  manufacturer = fields.ObjectField(properties={
    'name': fields.TextField(),
    'country_code': fields.TextField(),
  })
  ads = fields.NestedField(properties={
    'description': fields.TextField(analyzer=html_strip),
    'title': fields.TextField(),
    'pk': fields.IntegerField(),
  })

  class Index:
    name = 'cars'

  class Django:
    model = Car
    fields = [
      'name',
      'color',
    ]

  def get_queryset(self, filters: Optional[Dict[str, Any]] = None, count: int = 0) -> 'QuerySet':
    """Not mandatory but to improve performance we can select related in one sql request"""
    return super().get_queryset(count=count).select_related(
      'manufacturer'
    )
```

## Field Classes


Most [Opensearch field types](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/mapping-types.html) are
supported. The `attr` argument is a dotted "attribute path" which will be looked up on the model using Django template
semantics (dict lookup, attribute lookup, list index lookup). By default, the `attr` argument is set to the field name.

For the rest, the field properties are the same as opensearch-dsl.

So for example you can
use [a custom analyzer](http://elasticsearch-dsl.readthedocs.io/en/stable/persistence.html#analysis):

```python
# documents.py

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)


@registry.register_document
class CarDocument(Document):
    description = fields.TextField(
        analyzer=html_strip,
        fields={'raw': fields.KeywordField()}
    )

    class Django:
        model = Car
        fields = [
            'name',
            'color',
        ]
```
