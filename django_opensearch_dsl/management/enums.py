from enum import Enum


class OpensearchAction(str, Enum):
    """Opensearch's action available."""

    INDEX = ("index", "indexing", "indexed")
    UPDATE = ("update", "updating", "updated")
    CREATE = ("create", "creating", "created")
    REBUILD = ("rebuild", "rebuilding", "rebuilded")
    LIST = ("list", "listing", "listed")
    DELETE = ("delete", "deleting", "deleted")
    MANAGE = ("manage", "managing", "managed")

    def __new__(cls, value: str, present_participle: str, past: str):  # noqa: D102
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.present_participle = present_participle
        obj.past = past
        return obj
