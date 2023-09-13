import os
import sys
import argparse

try:
    from django.conf import settings
    from django.test.utils import get_runner

    def get_settings():
        elasticsearch_dsl_default_settings = {
            'hosts': os.environ.get(
                'ELASTICSEARCH_URL',
                'https://127.0.0.1:9200'
            ),
            'http_auth': (
                os.environ.get('ELASTICSEARCH_USERNAME'),
                os.environ.get('ELASTICSEARCH_PASSWORD')
            )
        }

        elasticsearch_certs_path = os.environ.get(
            'ELASTICSEARCH_CERTS_PATH'
        )
        if elasticsearch_certs_path:
            elasticsearch_dsl_default_settings['ca_certs'] = (
                elasticsearch_certs_path
            )
        else:
            elasticsearch_dsl_default_settings['verify_certs'] = False

        settings.configure(
            DEBUG=True,
            USE_TZ=True,
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sites",
                "django_elasticsearch_dsl",
                "tests",
            ],
            SITE_ID=1,
            MIDDLEWARE_CLASSES=(),
            ELASTICSEARCH_DSL={
                'default': elasticsearch_dsl_default_settings
            },
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        )

        try:
            import django
            setup = django.setup
        except AttributeError:
            pass
        else:
            setup()

        return settings

except ImportError:
    import traceback
    traceback.print_exc()
    msg = "To fix this error, run: pip install -r requirements_test.txt"
    raise ImportError(msg)


def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--elasticsearch',
        nargs='?',
        metavar='localhost:9200',
        const='localhost:9200',
        help="To run integration test against an Elasticsearch server",
    )
    parser.add_argument(
        '--elasticsearch-username',
        nargs='?',
        help="Username for Elasticsearch user"
    )
    parser.add_argument(
        '--elasticsearch-password',
        nargs='?',
        help="Password for Elasticsearch user"
    )
    parser.add_argument(
        '--elasticsearch-certs-path',
        nargs='?',
        help="Path to CA certificates for Elasticsearch"
    )
    return parser


def run_tests(*test_args):
    args, test_args = make_parser().parse_known_args(test_args)
    if args.elasticsearch:
        os.environ.setdefault('ELASTICSEARCH_URL', args.elasticsearch)

    os.environ.setdefault(
        'ELASTICSEARCH_USERNAME', args.elasticsearch_username
    )
    os.environ.setdefault(
        'ELASTICSEARCH_PASSWORD', args.elasticsearch_password
    )

    if args.elasticsearch_certs_path:
        os.environ.setdefault(
            'ELASTICSEARCH_CERTS_PATH', args.elasticsearch_certs_path
        )

    if not test_args:
        test_args = ['tests']

    settings = get_settings()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    failures = test_runner.run_tests(test_args)

    if failures:
        sys.exit(bool(failures))


if __name__ == '__main__':
    run_tests(*sys.argv[1:])
