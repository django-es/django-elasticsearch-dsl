.. :changelog:

History
-------

0.4.0 (Unreleased)
~~~~~~~~~~~~~~~~~~
* Fix DocType inheritance. The DocType is store in the registry as a class and not anymore as an instance

0.3.0 (2017-10-01)
~~~~~~~~~~~~~~~~~~
* Add support for resynching ES documents if related models are updated (HansAdema)
* Better management for django FileField and ImageField
* Fix some errors in the doc (barseghyanartur, diwu1989)

0.2.0 (2017-07-02)
~~~~~~~~~~~~~~~~~~

* Replace simple model signals with easier to customise signal processors (barseghyanartur)
* Add options to disable automatic index refreshes (HansAdema)
* Support defining DocType indexes through Meta class (HansAdema)
* Add option to set default Index settings through Django config (HansAdema)

0.1.0 (2017-05-26)
~~~~~~~~~~~~~~~~~~

* First release on PyPI.
