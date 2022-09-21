from __future__ import unicode_literals, absolute_import
from datetime import datetime
from sys import stdout
from time import sleep

from elasticsearch_dsl import connections
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from six.moves import input
from ...registries import registry


class Command(BaseCommand):
    help = 'Manage elasticsearch index.'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.es_conn = connections.get_connection()

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
        parser.set_defaults(
            parallel=getattr(settings, "ELASTICSEARCH_DSL_PARALLEL", False)
        )
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

    def _get_index_suffix(index):
        return '-' + datetime.now().strftime('%Y%m%d%H%M%S%f')

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
                    elif (
                        "{}.{}".format(
                        model._meta.app_label.lower(),
                            model._meta.model_name.lower(),
                        )
                        == arg
                    ):
                        models.append(model)
                        match_found = True

                if not match_found:
                    raise CommandError("No model or app named {}".format(arg))
        else:
            models = registry.get_models()

        return set(models)

    def _create(self, models, aliases, options):
        class AliasIndexPair:
            def __init__(self, alias, index):
                self.alias = alias
                self.index = index
        alias_index_pairs = []
        for index in registry.get_indices(models):
            # The alias takes the original index name value. The
            # index name sent to Elasticsearch will be the alias
            # plus the suffix from above. In addition, the index
            # name needs to be limited to 255 characters, of which
            # 21 will always be taken by the suffix, leaving 234
            # characters from the original index name value.
            alias_name=index._name
            try:
                alias = list(index.get_alias()[alias_name]['aliases'].keys())
            except:
                alias = False
            if not alias or ('without-aliases' in options and options['without-aliases']):
                index._name = index._name[:234] + self._get_index_suffix()
            else:
                self.stdout.write(
                    "'{}' already exists as an alias. Run '--delete' with"
                    " '--use-alias' arg to delete indices pointed at the "
                    "alias to make index name available.".format(index._name)
                )
                return
            self.stdout.write("Creating index '{}'".format(alias_name))
            index.create()
            if 'without-aliases' in options and options['without-aliases']:
                alias_index_pairs.append(AliasIndexPair(alias_name, index))
                continue
            self.es_conn.indices.update_aliases({"actions": [{"add": {"alias": alias_name, "index": index._name}}]})
        if 'without-aliases' in options and options['without-aliases']:
            return alias_index_pairs
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

    def _get_alias_indices(self, alias):
        alias_indices = self.es_conn.indices.get_alias(name=alias)
        return list(alias_indices.keys())

    def _delete_alias_indices(self, alias):
        alias_indices = self._get_alias_indices(alias)
        alias_delete_actions = [
            {"remove_index": {"index": index}} for index in alias_indices
        ]
        self.es_conn.indices.update_aliases({"actions": alias_delete_actions})
        for index in alias_indices:
            self.stdout.write("Deleted index '{}'".format(index))

    def _delete(self, models, aliases, options):
        index_names = [index._name for index in registry.get_indices(models)]

        if not options['force']:
            response = input(
                "Are you sure you want to delete "
                "the '{}' indices? [y/N]: ".format(", ".join(index_names))
            )
            if response.lower() != 'y':
                self.stdout.write('Aborted')
                return False

            for index in index_names:
                alias_exists = index in aliases
                if alias_exists:
                    self._delete_alias_indices(index)
                elif self.es_conn.indices.exists(index=index):
                    self.stdout.write(
                    "'{}' refers to an index, not an alias. ".format(index)
                    )
                    return False

        return True

    def _rebuild(self, models, aliases, options):
        options['without-aliases']=True
        new_indices = self._create(models, aliases, options)
        self._populate(models, options)
        for new_index in new_indices:
            try:
                action_list = []
                alias = new_index.alias
                alias_exists = alias in aliases
                alias_delete_actions = []
                if not alias_exists and self.es_conn.indices.exists(index=alias):
                    raise
                action_list.append({"add": {"alias": alias, "index": new_index.index._name}})
                alias_delete_actions=[]
                try:
                    alias_indices = self._get_alias_indices(alias)
                except:
                    alias_indices = []
                for old_index in alias_indices:
                    action_list.append({"remove": {"alias": alias, "indices": old_index}})
                    alias_delete_actions.append({"remove_index": {"index": old_index}})

                self.stdout.write("Rebuild '{}'".format(alias))
                try:
                    self.es_conn.indices.update_aliases({"actions": action_list})
                except Exception as e:
                    self.stdout.write("Failed to run action")
                    if alias_indices:
                        self.es_conn.indices.update_aliases({"actions": [{"add": {"alias": alias, "index": old_index}}for old_index in alias_indices]})
                    raise
                if alias_delete_actions:
                    self.stdout.write("Remove old indices")
                    if alias_delete_actions:
                        self.es_conn.indices.update_aliases({"actions": alias_delete_actions})
            except:
                self.stdout.write("Failed to rebuild index '{}'".format(new_index.index._name))
                self.stdout.write("Remove new indices".format(new_index.index._name))
                self.es_conn.indices.delete(index=new_index.index._name,ignore=[400, 404])
                alias_delete_actions=[]
                continue
    def handle(self, *args, **options):
        if not options['action']:
            raise CommandError(
                "No action specified. Must be one of"
                " '--create','--populate', '--delete' or '--rebuild' ."
            )

        action = options['action']
        models = self._get_models(options['models'])

        # We need to know if and which aliases exist to mitigate naming
        # conflicts with indices, therefore this is needed regardless
        # of using the '--use-alias' arg.
        aliases = []
        for index in self.es_conn.indices.get_alias().values():
            aliases += index['aliases'].keys()

        if action == 'create':
            self._create(models, aliases, options)
        elif action == 'populate':
            self._populate(models, options)
        elif action == 'delete':
            self._delete(models, aliases, options)
        elif action == 'rebuild':
            self._rebuild(models, aliases, options)
        else:
            raise CommandError(
                "Invalid action. Must be one of"
                " '--create','--populate', '--delete' or '--rebuild' ."
            )
