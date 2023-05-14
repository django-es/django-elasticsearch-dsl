from typing import List

from django.db import models


def get_queryset_by_ids(model: models.Model, ids: List[int]):
    return model.objects.filter(
        id__in=ids
    )
