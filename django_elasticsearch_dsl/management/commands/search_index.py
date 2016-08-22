from __future__ import unicode_literals, absolute_import
from django.core.management.base import BaseCommand, CommandError
from django.utils.six.moves import input
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
                    elif '{}.{}'.format(model._meta.app_label.lower(),
                                        model._meta.model_name.lower()) == arg:

                        models.append(model)
                        match_found = True

                if not match_found:
                    raise CommandError("No model or app named {}".format(arg))
        else:
            models = registry.get_models()

        return set(models)

    def _execute_index_action(self, action, index, options):
        if action == 'delete':
            if not options['force']:
                response = input(
                    "Are you sure you want to delete "
                    "the '{}' index ? [n/Y]: ".format(index))
            else:
                response = 'y'
            if response.lower() == 'y':
                self.stdout.write("Deleting index '{}'".format(index))
                index.delete(ignore=404)

        elif action == 'create':
            self.stdout.write(
                "Creating index '{}'".format(index))
            index.create()

    def _execute_doc_action(self, action, doc, options):
        if action == 'populate':
            qs = doc.get_queryset()
            self.stdout.write("Indexing {} '{}' objects".format(
                qs.count(), doc._doc_type.model.__name__))
            doc.update(qs.iterator())

    def handle(self, *args, **options):
        if not options['action']:
            raise CommandError(
                "No action specified. Must be one of"
                " '--create','--populate', '--delete' or '--rebuild' ."
            )

        action = options['action']
        if action == 'rebuild':
            options.update({'action': 'delete'})
            self.handle(*args, **options)
            options.update({'action': 'create'})
            self.handle(*args, **options)
            options.update({'action': 'populate'})
            self.handle(*args, **options)
            return

        models = self._get_models(options['models'])

        if action in ['populate']:
            for doc in registry.get_documents(models):
                self._execute_doc_action(action, doc, options)
        elif action in ['create', 'delete']:
            for index in registry.get_indices(models):
                self._execute_index_action(action, index, options)
