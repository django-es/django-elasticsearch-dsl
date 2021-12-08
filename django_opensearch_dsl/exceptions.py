class DjangoOpensearchDslError(Exception):
    pass


class VariableLookupError(DjangoOpensearchDslError):
    pass


class RedeclaredFieldError(DjangoOpensearchDslError):
    pass


class ModelFieldNotMappedError(DjangoOpensearchDslError):
    pass
