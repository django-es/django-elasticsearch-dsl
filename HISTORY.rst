.. :changelog:

History
-------

0.4.2 (XXX-XX-XX)
~~~~~~~~~~~~~~~~~~
* Add signals for manage m2m related objects auto synching

0.4.1 (2017-10-17)
~~~~~~~~~~~~~~~~~~
* Update example app with get_instances_from_related
* Typo/grammar fixes

0.4.0 (2017-10-07)
~~~~~~~~~~~~~~~~~~
* Add a method on the Search class to return a django queryset from an es result
* Add a queryset_pagination option to DocType.Meta for allow the pagination of
  big django querysets during the index populating
* Remove the call to iterator method for the django queryset
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
