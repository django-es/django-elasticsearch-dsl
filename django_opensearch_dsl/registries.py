from collections import defaultdict
from copy import deepcopy

from django.core.exceptions import ImproperlyConfigured
from opensearch_dsl import AttrDict

from .apps import DEDConfig
from .exceptions import RedeclaredFieldError


class DocumentRegistry:
    """Registry of models classes to a set of Document classes."""

    def __init__(self):
        self._indices = defaultdict(set)
        self._models = defaultdict(set)

    def register(self, index, doc_class):
        """Register the model with the registry."""
        self._models[doc_class.django.model].add(doc_class)

        for idx, docs in self._indices.items():
            if index._name == idx._name:  # noqa pragma: no cover
                docs.add(doc_class)
                return

        self._indices[index].add(doc_class)

    def register_document(self, document):
        django_meta = getattr(document, 'Django')
        # Raise error if Django class can not be found
        if not django_meta:  # pragma: no cover
            message = f"You must declare the Django class inside {document.__name__}"
            raise ImproperlyConfigured(message)

        # Keep all django related attribute in a django_attr AttrDict
        django_attr = AttrDict({
            'model': getattr(document.Django, 'model'),
            'queryset_pagination': getattr(
                document.Django, 'queryset_pagination', DEDConfig.default_queryset_pagination()
            ),
            'ignore_signals': getattr(django_meta, 'ignore_signals', False),
            'auto_refresh': getattr(
                django_meta, 'auto_refresh', DEDConfig.auto_refresh_enabled()
            ),
        })
        if not django_attr.model:  # pragma: no cover
            raise ImproperlyConfigured("You must specify the django model")

        # Add The model fields into opensearch mapping field
        model_field_names = getattr(document.Django, "fields", [])
        mapping_fields = document._doc_type.mapping.properties.properties.to_dict().keys()  # noqa

        for field_name in model_field_names:
            if field_name in mapping_fields:  # pragma: no cover
                raise RedeclaredFieldError(
                    f"You cannot redeclare the field named '{field_name}' on {document.__name__}"
                )

            django_field = django_attr.model._meta.get_field(field_name)  # noqa

            field_instance = document.to_field(field_name, django_field)
            document._doc_type.mapping.field(field_name, field_instance)  # noqa

        # Add django attribute with all the django attribute
        setattr(document, 'django', django_attr)

        # Set the fields of the mappings
        fields = document._doc_type.mapping.properties.properties.to_dict()  # noqa
        setattr(document, '_fields', fields)

        # Update settings of the document index
        default_index_settings = deepcopy(DEDConfig.default_index_settings())
        document._index.settings(**{**default_index_settings, **document._index._settings})  # noqa

        # Register the document and index class to our registry
        self.register(index=document._index, doc_class=document)  # noqa

        return document

    def update(self, instance, action='index', **kwargs):
        """
        Update all the elasticsearch documents attached to this model (if their
        ignore_signals flag allows it)
        """
        if not DEDConfig.autosync_enabled():
            return

        if instance.__class__ in self._models:
            for doc in self._models[instance.__class__]:
                if not doc.django.ignore_signals:
                    doc().update(instance, action, **kwargs)

    def delete(self, instance, **kwargs):
        """
        Delete all the elasticsearch documents attached to this model (if their
        ignore_signals flag allows it)
        """
        self.update(instance, action='delete', **kwargs)

    def get_indices(self):
        """Get all indices in the registry."""
        return set(self._indices.keys())


registry = DocumentRegistry()
