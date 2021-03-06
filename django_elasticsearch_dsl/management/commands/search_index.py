from __future__ import unicode_literals, absolute_import

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
            '--index_names',
            type=str,
            nargs='*',
            help="Specify the index names to be updated in elasticsearch"
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
        parser.set_defaults(parallel=getattr(settings, 'ELASTICSEARCH_DSL_PARALLEL', False))
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

    def _get_indices(self, index_names):
        indices = registry.get_indices()

        invalid_index_names = set(index_names) - set(index._name for index in indices)
        if invalid_index_names:
            raise CommandError("No index named {}".format(invalid_index_names))

        return set(index for index in indices if index._name in index_names)

    def _create(self, indices, options):
        for index in indices:
            self.stdout.write("Creating index '{}'".format(index._name))
            index.create()

    def _populate(self, indices, options):
        parallel = options['parallel']
        models = registry.get_models(indices)
        for doc in registry.get_documents(models):
            self.stdout.write("Indexing {} '{}' objects {}".format(
                doc().get_queryset().count() if options['count'] else "all",
                doc.django.model.__name__,
                "(parallel)" if parallel else "")
            )
            qs = doc().get_indexing_queryset()
            doc().update(qs, parallel=parallel)

    def _delete(self, indices, options):
        index_names = [index._name for index in indices]

        if not options['force']:
            response = input(
                "Are you sure you want to delete "
                "the '{}' indexes? [y/N]: ".format(", ".join(index_names)))
            if response.lower() != 'y':
                self.stdout.write('Aborted')
                return False

        for index in indices:
            self.stdout.write("Deleting index '{}'".format(index._name))
            index.delete(ignore=404)
        return True

    def _rebuild(self, models, options):
        if not self._delete(models, options):
            return

        self._create(models, options)
        self._populate(models, options)

    def handle(self, *args, **options):
        if not options['action']:
            raise CommandError(
                "No action specified. Must be one of"
                " '--create','--populate', '--delete' or '--rebuild' ."
            )

        if options['models'] and options['index_names']:
            raise CommandError("Only one of '--models' or '--index_names' are allowed.")

        action = options['action']
        if options['index_names']:
            indices = self._get_indices(options['index_names'])
        else:
            models = self._get_models(options['models'])
            indices = registry.get_indices(models)

        if action == 'create':
            self._create(indices, options)
        elif action == 'populate':
            self._populate(indices, options)
        elif action == 'delete':
            self._delete(indices, options)
        elif action == 'rebuild':
            self._rebuild(indices, options)
        else:
            raise CommandError(
                "Invalid action. Must be one of"
                " '--create','--populate', '--delete' or '--rebuild' ."
            )
