from math import ceil

from django.core.paginator import Page, Paginator
from django.utils.functional import cached_property


class ElasticPage(Page):
    def __len__(self):
        if hasattr(self.object_list, "count"):
            return self.object_list.count()

        return len(self.object_list)


class ElasticPaginator(Paginator):
    max_result_window = 10000

    @cached_property
    def num_pages(self):
        """
        Returns the total number of pages.

        We are aware of the ElasticSearch's internal limit for retrieving result
        pages. Therefore we do not offer more results!
        """
        if self.count == 0 and not self.allow_empty_first_page:
            return 0
        hits = min(
            max(1, self.count - self.orphans),
            self.max_result_window
        )
        return int(ceil(hits / float(self.per_page)))

    def _get_page(self, *args, **kwargs):
        return ElasticPage(*args, **kwargs)

    def _check_object_list_is_ordered(self):
        pass
