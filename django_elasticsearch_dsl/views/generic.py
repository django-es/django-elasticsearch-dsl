from collections import Mapping
import json

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from django.http import HttpRequest
from django.views.generic.list import ListView
from elasticsearch.exceptions import ConnectionError, AuthenticationException, \
    AuthorizationException
import six
from six.moves.urllib_error import HTTPError

from ..paginator import ElasticPaginator
from ..search import Search


class ElasticExceptionHandler(object):
    """
    Common exception handling for elastic-related callables

    :param func: The function or method
    :type func: callable
    :param request: A request object
    :param error_return_value: Default return value in case an exception was
                               raised
    """
    def __init__(self, func, request=None, error_return_value=None):
        self.func = func
        self.request = request
        self.return_value = error_return_value

    def _message(self, msg):
        if isinstance(self.request, HttpRequest):
            messages.error(
                self.request,
                "Cannot query external search engine: {}".format(msg)
            )

    def __call__(self, *args, **kwargs):
        try:
            return self.func(*args, **kwargs)
        except (HTTPError, ConnectionError) as error:
            self._message(error.args[-1])
            return self.return_value
        except (AuthenticationException, AuthorizationException) as error:
            if not isinstance(error.args[-1], Mapping):
                try:
                    data = json.loads(error.args[-1])
                except (ValueError, TypeError):
                    data = {'reason': error.args[-1]}
            else:
                data = error.args[-1]

            msg = data.get(
                "reason",
                data.get("error", {}).get("reason", "Unknown")
            )
            self._message(msg)
            return self.return_value


class ElasticListView(ListView):
    """
    Mixin to paginate ElasticSearch result sets before conversion to QuerySet

    This is needed because ElasticSearch enforces pagination prior to the type
    conversion. So we have to deal with it.

    .. note::

        In the context of ElasticSearch the ``Search`` object replaces the
        ``QuerySet`` object entirely. Only in the assembled context a page of
        search results will be cast into a QuerySet.
    """
    document = None
    paginator_class = ElasticPaginator

    def _get_queryset(self):
        if isinstance(self.queryset, Search):
            queryset = self.queryset
        elif self.document and hasattr(self.document, "search"):
            queryset = self.document.search()
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a Search object. Define "
                "%(cls)s.document, %(cls)s.queryset, or override "
                "%(cls)s.get_queryset()." % {
                    'cls': self.__class__.__name__
                }
            )

        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, six.string_types):
                ordering = (ordering,)
            queryset = queryset.sort(*ordering)

        return queryset

    def get_queryset(self):
        default = None
        if issubclass(self.model, Model):
            default = self.model.objects.none()

        return ElasticExceptionHandler(
            self._get_queryset,
            request=self.request,
            error_return_value=default
        )()

    def get_context_object_name(self, object_list):
        if object_list is not None and not hasattr(object_list, "model"):
            object_list.model = getattr(object_list, "_model", None)
            if object_list.model is None:
                if issubclass(self.model, Model):
                    object_list.model = self.model
        return super(ElasticListView, self).get_context_object_name(
            object_list
        )

    def _get_context_data(self, context, **kwargs):
        for key in ['object_list',
                    self.get_context_object_name(context["object_list"])]:
            if isinstance(context[key], Search):
                context[key] = context[key].to_queryset()

            if hasattr(context[key], "prefetch"):
                context[key].prefetch()

        return context

    def get_context_data(self, **kwargs):
        context = ElasticExceptionHandler(
            super(ElasticListView, self).get_context_data,
            request=self.request,
            error_return_value={},
        )(**kwargs)

        return ElasticExceptionHandler(
            self._get_context_data,
            request=self.request,
            error_return_value=context
        )(context, **kwargs)
