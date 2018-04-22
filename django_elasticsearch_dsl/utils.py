from itertools import islice


def batch_iterate(qs, size=100):
    """Efficient batching queryset

    Django paginator can lead to performance issue with huge
    queryset, make custom one based on pks presents in db right
    now
    """
    qs_pks = qs.order_by('pk').values_list('pk', flat=True)
    last_pk = qs_pks.last()
    pks = list(islice(qs_pks, 0, None, size))
    pks.append(last_pk + 1)

    for lower, upper in zip(pks, pks[1:]):
        ranged_qs = qs.filter(pk__range=(lower, upper - 1))
        yield ranged_qs
