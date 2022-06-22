class DjangoOpensearchDslError(Exception):
    """Base Exception for Django Opensearch DSL."""


class VariableLookupError(DjangoOpensearchDslError):
    """Raised when a value could not be retrieved using field's definition."""


class RedeclaredFieldError(DjangoOpensearchDslError):
    """Raised when a field is redeclared within a `Document`."""


class ModelFieldNotMappedError(DjangoOpensearchDslError):
    """Raised when no Opensearch's field could be mapped to a Django's field."""
