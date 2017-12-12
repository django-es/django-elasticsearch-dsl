# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class Car(models.Model):
    TYPE_CHOICES = (
        ('se', "Sedan"),
        ('br', "Break"),
        ('4x', "4x4"),
        ('co', "Coupé"),
    )

    name = models.CharField(max_length=255)
    launched = models.DateField()
    type = models.CharField(
        max_length=2,
        choices=TYPE_CHOICES,
        default='se',
    )
    manufacturer = models.ForeignKey(
        'Manufacturer', null=True, on_delete=models.SET_NULL
    )
    categories = models.ManyToManyField('Category')

    class Meta:
        app_label = 'tests'

    def __str__(self):
        return self.name


COUNTRIES = {
    'FR': 'France',
    'UK': 'United Kingdom',
    'ES': 'Spain',
    'IT': 'Italya',
}


@python_2_unicode_compatible
class Manufacturer(models.Model):
    name = models.CharField(max_length=255, default=_("Test lazy tanslation"))
    country_code = models.CharField(max_length=2)
    created = models.DateField()
    logo = models.ImageField(blank=True)

    class meta:
        app_label = 'tests'

    def country(self):
        return COUNTRIES.get(self.country_code, self.country_code)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Category(models.Model):
    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    icon = models.ImageField(blank=True)

    class Meta:
        app_label = 'tests'

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class Ad(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateField(auto_now_add=True)
    modified = models.DateField(auto_now=True)
    url = models.URLField()
    car = models.ForeignKey(
        'Car', related_name='ads',  null=True, on_delete=models.SET_NULL
    )

    class Meta:
        app_label = 'tests'

    def __str__(self):
        return self.title
