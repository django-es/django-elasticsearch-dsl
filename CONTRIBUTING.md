# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at https://github.com/qcoumes/django-opensearch-dsl/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

### Write Documentation

Django Opensearch DSL could always use more documentation, whether as part of the official Django Opensearch DSL docs,
in docstrings, or even on the web in blog posts, articles, and such.

### Submit Feedback

The best way to send feedback is to file an issue at https://github.com/qcoumes/django-opensearch-dsl/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions are welcome :)

--- 

## Setting up local environment

Ready to contribute? Here's how to set up `django-opensearch-dsl` for local development.

1. Fork the `django-opensearch-dsl` repo on GitHub.

2. Clone your fork locally:

    * `git clone git@github.com:your_name_here/django-opensearch-dsl.git`

3. Install your local copy into a virtualenv.

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip3 install -r develop_requirements.txt
   ```

4. Create a branch for local development:

    * `git checkout -b name-of-your-bugfix-or-feature`

   Now you can make your changes locally.

## Testing your changes

Tests must be written inside the `tests/` Django's project. This project contains three directory :

* `project` - "settings" directory containing the usual stuff (`settings.py`, `wsgi.py`, `urls.py`, ...)
* `django_dummy_app` - Django application you can use for testing. It already contains some models.
* `tests` - Where you should write your tests.

You can interact with this project using the root-level `manage.py`.

If you need to manually tests some of your feature, you can create a `sqlite3`
database with `python3 manage.py migrate`. You can also load some geographic data with
`python3 manage.py loaddata tests/django_dummy_app/geography_data.json`.

To run the tests, you also need an instance of Opensearch running on `localhost:9201`. You can use `docker`
to start an instance with `docker-compose` (`docker-compose up [-d]`).

---

There is mainly two ways of writing tests :

* Interacting directly with Opensearch (e.g. `tests/tests/test_search.py`)
* Mocking interaction with Opensearch (e.g. `tests/tests/test_signals.py`)

You can run all the tests for supported django versions by running `tox` (`pip install tox`).

### Submitting your changes

1. Ensure your code is correctly formatted and documented:

```sh
./bin/pre_commit.sh
```

2. Commit your changes and push your branch to GitHub:

```sh
git add .
git commit -m "Your detailed description of your changes."
git push origin name-of-your-bugfix-or-feature
```

3. Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests

2. If the pull request adds functionality, the documentation should be updated.

3. The pull request should work for and 3.6 and above. Check
   https://github.com/qcoumes/django-opensearch-dsl/actions
   and make sure that the tests pass for all supported Python versions.
