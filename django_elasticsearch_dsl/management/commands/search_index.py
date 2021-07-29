from __future__ import unicode_literals, absolute_import
from datetime import datetime

from elasticsearch_dsl import connections
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from six.moves import input
from ...registries import registry


class Command(BaseCommand):
    help = 'Manage elasticsearch index.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            metavar='app[.model]',
            type=str,
            nargs='*',
            help="Specify the model or app to be updated in elasticsearch"
        )
        parser.add_argument(
            '--create',
            action='store_const',
            dest='action',
            const='create',
            help="Create the indices in elasticsearch"
        )
        parser.add_argument(
            '--populate',
            action='store_const',
            dest='action',
            const='populate',
            help="Populate elasticsearch indices with models data"
        )
        parser.add_argument(
            '--delete',
            action='store_const',
            dest='action',
            const='delete',
            help="Delete the indices in elasticsearch"
        )
        parser.add_argument(
            '--rebuild',
            action='store_const',
            dest='action',
            const='rebuild',
            help="Delete the indices and then recreate and populate them"
        )
        parser.add_argument(
            '-f',
            action='store_true',
            dest='force',
            help="Force operations without asking"
        )
        parser.add_argument(
            '--parallel',
            action='store_true',
            dest='parallel',
            help='Run populate/rebuild update multi threaded'
        )
        parser.add_argument(
            '--no-parallel',
            action='store_false',
            dest='parallel',
            help='Run populate/rebuild update single threaded'
        )
        parser.add_argument(
            '--atomic',
            action='store_true',
            dest='atomic',
            help='Rebuild and replace indices with aliases'
        )
        parser.add_argument(
            '--atomic-no-delete',
            action='store_true',
            dest='atomic_no_delete',
            help="Do not delete replaced indices when used with '--atomic' arg"
        )
        parser.set_defaults(parallel=getattr(settings, 'ELASTICSEARCH_DSL_PARALLEL', False))
        parser.add_argument(
            '--refresh',
            action='store_true',
            dest='refresh',
            default=None,
            help='Refresh indices after populate/rebuild'
        )
        parser.add_argument(
            '--no-count',
            action='store_false',
            default=True,
            dest='count',
            help='Do not include a total count in the summary log line'
        )

    def _get_models(self, args):
        """
        Get Models from registry that match the --models args
        """
        if args:
            models = []
            for arg in args:
                arg = arg.lower()
                match_found = False

                for model in registry.get_models():
                    if model._meta.app_label == arg:
                        models.append(model)
                        match_found = True
                    elif '{}.{}'.format(
                        model._meta.app_label.lower(),
                        model._meta.model_name.lower()
                    ) == arg:
                        models.append(model)
                        match_found = True

                if not match_found:
                    raise CommandError("No model or app named {}".format(arg))
        else:
            models = registry.get_models()

        return set(models)

    def _create(self, models, options):
        for index in registry.get_indices(models):
            self.stdout.write("Creating index '{}'".format(index._name))
            index.create()

    def _populate(self, models, options):
        parallel = options['parallel']
        for doc in registry.get_documents(models):
            self.stdout.write("Indexing {} '{}' objects {}".format(
                doc().get_queryset().count() if options['count'] else "all",
                doc.django.model.__name__,
                "(parallel)" if parallel else "")
            )
            qs = doc().get_indexing_queryset()
            doc().update(qs, parallel=parallel, refresh=options['refresh'])

    def _delete(self, models, options):
        index_names = [index._name for index in registry.get_indices(models)]

        if not options['force']:
            response = input(
                "Are you sure you want to delete "
                "the '{}' indexes? [y/N]: ".format(", ".join(index_names)))
            if response.lower() != 'y':
                self.stdout.write('Aborted')
                return False

        for index in registry.get_indices(models):
            self.stdout.write("Deleting index '{}'".format(index._name))
            index.delete(ignore=404)
        return True

    def _update_alias(self, es_conn, alias, new_index, alias_exists, options):
        alias_actions = [{"add": {"alias": alias, "index": new_index}}]
        old_indices = []
        alias_delete_actions = []
        if alias_exists:
            # Elasticsearch will return an error if we search for
            # indices by alias but the alias doesn't exist. Therefore,
            # we want to be sure the alias exists.
            old_alias_indices = es_conn.indices.get_alias(name=alias)
            old_indices = list(old_alias_indices.keys())
            alias_actions.append(
                {"remove": {"alias": alias, "indices": old_indices}}
            )
            alias_delete_actions = [
                {"remove_index": {"index": index}} for index in old_indices
            ]

        es_conn.indices.update_aliases({"actions": alias_actions})
        self.stdout.write(
            "Added alias '{}' to index '{}'".format(alias, new_index)
        )

        if old_indices:
            if len(old_indices) == 1:
                stdout_term = "index"
            else:
                stdout_term = "indices"

            old_indices_str = ", ".join(old_indices)
            self.stdout.write(
                "Removed alias '{}' from {} '{}'".format(
                    alias, stdout_term, old_indices_str
                )
            )
            if alias_delete_actions and options['atomic_no_delete'] is False:
                es_conn.indices.update_aliases(
                    {"actions": alias_delete_actions}
                )
                self.stdout.write(
                    "Deleted {} '{}'".format(stdout_term, old_indices_str)
                )

    def _rebuild(self, models, options):
        if options['atomic'] is False and not self._delete(models, options):
            return

        if options['atomic'] is True:
            alias_index_pairs = []
            index_suffix = "-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
            for index in registry.get_indices(models):
                # The alias takes the original index name value. The
                # index name sent to Elasticsearch will be the alias
                # plus the suffix from above.
                new_index = index._name + index_suffix
                alias_index_pairs.append(
                    {'alias': index._name, 'index': new_index}
                )
                index._name = new_index

        self._create(models, options)
        self._populate(models, options)

        if options['atomic'] is True:
            es_conn = connections.get_connection()
            existing_aliases = []
            for index in es_conn.indices.get_alias().values():
                existing_aliases += index['aliases'].keys()

            for alias_index_pair in alias_index_pairs:
                alias = alias_index_pair['alias']
                alias_exists = alias in existing_aliases
                self._update_alias(
                    es_conn,
                    alias,
                    alias_index_pair['index'],
                    alias_exists,
                    options
                )

    def handle(self, *args, **options):
        if not options['action']:
            raise CommandError(
                "No action specified. Must be one of"
                " '--create','--populate', '--delete' or '--rebuild' ."
            )

        action = options['action']
        models = self._get_models(options['models'])

        if action == 'create':
            self._create(models, options)
        elif action == 'populate':
            self._populate(models, options)
        elif action == 'delete':
            self._delete(models, options)
        elif action == 'rebuild':
            self._rebuild(models, options)
        else:
            raise CommandError(
                "Invalid action. Must be one of"
                " '--create','--populate', '--delete' or '--rebuild' ."
            )
