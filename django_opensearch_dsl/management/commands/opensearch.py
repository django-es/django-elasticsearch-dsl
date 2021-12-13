import argparse
import functools
import operator
import os
import sys
from argparse import ArgumentParser
from collections import defaultdict
from typing import Any, Callable

import opensearchpy
from django.conf import settings
from django.core.exceptions import FieldError
from django.core.management import BaseCommand
from django.core.management.base import OutputWrapper
from django.db.models import Q

from django_opensearch_dsl.registries import registry
from ..enums import OpensearchAction
from ..types import parse



class Command(BaseCommand):
    help = (
        "Allow to create and delete indices, as well as indexing, updating or deleting specific "
        "documents from specific indices.\n"
    )

    def __init__(self, *args, **kwargs):  # noqa
        super(Command, self).__init__()
        self.usage = None
        if settings.TESTING:  # pragma: no cover
            self.stderr = OutputWrapper(open(os.devnull, 'w'))
            self.stdout = OutputWrapper(open(os.devnull, 'w'))

    def db_filter(self, parser: ArgumentParser) -> Callable[[str], Any]:
        """Return a function to parse the filters."""

        def wrap(value):  # pragma: no cover
            try:
                lookup, v = value.split("=")
                v = parse(v)
            except ValueError:
                sys.stderr.write(parser._subparsers._group_actions[0].choices['document'].format_usage())  # noqa
                sys.stderr.write(
                    f"manage.py index: error: invalid filter: '{value}' (filter must be formatted as "
                    f"'[Field Lookups]=[value]')\n",
                )
                exit(1)
            return lookup, v  # noqa

        return wrap

    def __list_index(self, **options):  # noqa pragma: no cover
        """List all known index and indicate whether they are created or not."""
        indices = registry.get_indices()
        result = defaultdict(list)
        for index in indices:
            module = index._doc_types[0].__module__.split(".")[-2]  # noqa
            exists = index.exists()
            checkbox = f"[{'X' if exists else ' '}]"
            count = f" ({index.search().count()} documents)" if exists else ''
            result[module].append(f"{checkbox} {index._name}{count}")
        for app, indices in result.items():
            self.stdout.write(self.style.MIGRATE_LABEL(app))
            self.stdout.write('\n'.join(indices))

    def _manage_index(self, action, indices, force, verbosity, ignore_error, **options):  # noqa
        """Manage the creation and deletion of indices."""
        action = OpensearchAction(action)
        known = registry.get_indices()

        # Filter indices
        if indices:
            # Ensure every given indices exists
            known_name = [i._name for i in known]  # noqa
            unknown = set(indices) - set(known_name)
            if unknown:
                self.stderr.write(f"Unknown indices '{list(unknown)}', choices are: '{known_name}'")
                exit(1)

            # Only keep given indices
            indices = list(filter(lambda i: i._name in indices, known))  # noqa
        else:
            indices = known

        # Display expected action
        if verbosity or not force:
            self.stdout.write(f"The following indices will be {action.past}:")
            for index in indices:
                self.stdout.write(f"\t- {index._name}.")  # noqa
            self.stdout.write("")

        # Ask for confirmation to continue
        if not force:  # pragma: no cover
            while True:
                p = input("Continue ? [y]es [n]o : ")
                if p.lower() in ["yes", "y"]:
                    self.stdout.write("")
                    break
                elif p.lower() in ["no", "n"]:
                    exit(1)

        pp = action.present_participle.title()
        for index in indices:
            if verbosity:
                self.stdout.write(f"{pp} index '{index._name}'...\r", ending="", )  # noqa
                self.stdout.flush()
            try:
                if action == OpensearchAction.CREATE:
                    index.create()
                elif action == OpensearchAction.DELETE:
                    index.delete()
                else:
                    try:
                        index.delete()
                    except opensearchpy.exceptions.NotFoundError:
                        pass
                    index.create()
            except opensearchpy.exceptions.NotFoundError:
                if verbosity or not ignore_error:
                    self.stderr.write(f"{pp} index '{index._name}'...{self.style.ERROR('Error (not found)')}")  # noqa
                if not ignore_error:
                    self.stderr.write("exiting...")
                    exit(1)
            except opensearchpy.exceptions.RequestError:
                if verbosity or not ignore_error:
                    self.stderr.write(
                        f"{pp} index '{index._name}'... {self.style.ERROR('Error (already exists)')}")  # noqa
                if not ignore_error:
                    self.stderr.write("exiting...")
                    exit(1)
            else:
                if verbosity:
                    self.stdout.write(f"{pp} index '{index._name}'... {self.style.SUCCESS('OK')}")  # noqa

    def _manage_document(self, action, indices, force, filters, excludes, verbosity, parallel, count, refresh,
                         missing, **options):  # noqa
        """Manage the creation and deletion of indices."""
        action = OpensearchAction(action)
        known = registry.get_indices()
        filter_ = functools.reduce(operator.and_, (Q(**{k: v}) for k, v in filters)) if filters else None
        exclude = functools.reduce(operator.and_, (Q(**{k: v}) for k, v in excludes)) if excludes else None

        # Filter indices
        if indices:
            # Ensure every given indices exists
            known_name = [i._name for i in known]  # noqa
            unknown = set(indices) - set(known_name)
            if unknown:
                self.stderr.write(f"Unknown indices '{list(unknown)}', choices are: '{known_name}'")
                exit(1)

            # Only keep given indices
            indices = list(filter(lambda i: i._name in indices, known))  # noqa
        else:
            indices = known

        # Ensure every indices needed are created
        not_created = [i._name for i in indices if not i.exists()]  # noqa
        if not_created:
            self.stderr.write(f"The following indices are not created : {not_created}")
            self.stderr.write("Use 'python3 manage.py opensearch list' to list indices' state.")
            exit(1)

        # Check field, preparing to display expected actions
        s = f"The following documents will be {action.past}:"
        kwargs_list = []
        for index in indices:
            # Handle --missing
            exclude_ = exclude
            if missing and action == OpensearchAction.INDEX:
                q = Q(pk__in=[h.meta.id for h in index.search().extra(stored_fields=[]).scan()])
                exclude_ = exclude_ & q if exclude_ is not None else q

            document = index._doc_types[0]()  # noqa
            try:
                kwargs_list.append({'filter_': filter_, 'exclude': exclude_, 'count': count})
                qs = document.get_queryset(filter_=filter_, exclude=exclude_, count=count).count()
            except FieldError as e:
                model = index._doc_types[0].django.model.__name__  # noqa
                self.stderr.write(f"Error while filtering on '{model}' (from index '{index._name}'):\n{e}'")  # noqa
                exit(1)
            else:
                s += f"\n\t- {qs} {document.django.model.__name__}."

        # Display expected actions
        if verbosity or not force:
            self.stdout.write(s + "\n\n")

        # Ask for confirmation to continue
        if not force:  # pragma: no cover
            while True:
                p = input("Continue ? [y]es [n]o : ")
                if p.lower() in ["yes", "y"]:
                    self.stdout.write("\n")
                    break
                elif p.lower() in ["no", "n"]:
                    exit(1)

        result = "\n"
        for index, kwargs in zip(indices, kwargs_list):
            document = index._doc_types[0]()  # noqa
            qs = document.get_indexing_queryset(stdout=self.stdout._out, verbose=verbosity, action=action, **kwargs)
            success, errors = document.update(
                qs, parallel=parallel, refresh=refresh, action=action, raise_on_error=False
            )

            success_str = self.style.SUCCESS(success) if success else success
            errors_str = self.style.ERROR(len(errors)) if errors else len(errors)
            model = document.django.model.__name__

            if verbosity == 1:
                result += f"{success_str} {model} successfully {action.past}, {errors_str} errors:\n"
                reasons = defaultdict(int)
                for e in errors:  # Count occurrence of each error
                    error = e.get(action, {'result': 'unknown error'}).get('result', 'unknown error')
                    reasons[error] += 1
                for reasons, total in reasons.items():
                    result += f"    - {reasons} : {total}\n"

            if verbosity > 1:
                result += f"{success_str} {model} successfully {action}d, {errors_str} errors:\n {errors}\n"

        if verbosity:
            self.stdout.write(result + "\n")

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        subparsers = parser.add_subparsers()

        # 'list' subcommand
        subparser = subparsers.add_parser(
            'list', help='Show all available indices (and their state) for the current project.',
            description='Show all available indices (and their state) for the current project.'
        )
        subparser.set_defaults(func=self.__list_index)

        # 'manage' subcommand
        subparser = subparsers.add_parser(
            'index', help='Manage the creation an deletion of indices.',
            description='Manage the creation an deletion of indices.'
        )
        subparser.set_defaults(func=self._manage_index)
        subparser.add_argument(
            'action', type=str, help="Whether you want to create, delete or rebuild the indices.",
            choices=[
                OpensearchAction.CREATE.value, OpensearchAction.DELETE.value, OpensearchAction.REBUILD.value,
            ]
        )
        subparser.add_argument('--force', action="store_true", default=False, help="Do not ask for confirmation.")
        subparser.add_argument('--ignore-error', action="store_true", default=False, help="Do not stop on error.")
        subparser.add_argument(
            "indices", type=str, nargs="*", metavar="INDEX", help="Only manage the given indices.",
        )

        # 'document' subcommand
        subparser = subparsers.add_parser(
            'document', help='Manage the indexation and creation of documents.',
            description='Manage the indexation and creation of documents.',
            formatter_class=argparse.RawTextHelpFormatter
        )
        subparser.set_defaults(func=self._manage_document)
        subparser.add_argument(
            'action', type=str, help="Whether you want to create, delete or rebuild the indices.",
            choices=[
                OpensearchAction.INDEX.value, OpensearchAction.DELETE.value, OpensearchAction.UPDATE.value,
            ]
        )
        subparser.add_argument(
            '-f', '--filters', type=self.db_filter(parser), nargs="*",
            help=(
                "Filter object in the queryset. Argument must be formatted as '[lookup]=[value]', e.g. "
                "'document_date__gte=2020-05-21.\n"
                "The accepted value type are:\n"
                "  - 'None' ('[lookup]=')\n"
                "  - 'float' ('[lookup]=1.12')\n"
                "  - 'int' ('[lookup]=23')\n"
                "  - 'datetime.date' ('[lookup]=2020-10-08')\n"
                "  - 'list' ('[lookup]=1,2,3,4') Value between comma ',' can be of any other accepted value type\n"
                "  - 'str' ('[lookup]=week') Value that didn't match any type above will be interpreted as a str\n"
                "The list of lookup function can be found here: "
                "https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups"
            ))
        subparser.add_argument(
            '-e', '--excludes', type=self.db_filter(parser), nargs="*",
            help=(
                "Exclude objects from the queryset. Argument must be formatted as '[lookup]=[value]', see '--filters' "
                "for more information"
            ))
        subparser.add_argument('--force', action="store_true", default=False, help="Do not ask for confirmation.")
        subparser.add_argument(
            '-i', '--indices', type=str, nargs="*",
            help="Only update documents on the given indices."
        )
        subparser.add_argument(
            '-c', '--count', type=int, default=None,
            help="Update at most COUNT objects (0 to index everything)."
        )
        subparser.add_argument(
            '-p', '--parallel', action="store_true", default=False,
            help="Parallelize the communication with Opensearch."
        )
        subparser.add_argument(
            '-r', '--refresh', action="store_true", default=False,
            help="Make operations performed on the indices immediatly available for search."
        )
        subparser.add_argument(
            '-m', '--missing', action="store_true", default=False,
            help="When used with 'index' action, only index documents not indexed yet."
        )

        self.usage = parser.format_usage()

    def handle(self, *args, **options):
        if "func" not in options:  # pragma: no cover
            self.stderr.write(self.usage)
            self.stderr.write(f"manage.py opensearch: error: no subcommand provided.")
            exit(1)

        options["func"](**options)
