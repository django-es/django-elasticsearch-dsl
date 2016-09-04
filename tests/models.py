# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
from django.db import models


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
    manufacturer = models.ForeignKey('Manufacturer', null=True)

    def __str__(self):
        return self.name

    def ads(self):
        return self.ad_set.all()


COUNTRIES = {
    'FR': 'France',
    'UK': 'United Kingdom',
    'ES': 'Spain',
    'IT': 'Italya',
}


@python_2_unicode_compatible
class Manufacturer(models.Model):
    name = models.CharField(max_length=255)
    country_code = models.CharField(max_length=2)
    created = models.DateField()

    def country(self):
        return COUNTRIES.get(self.country_code, self.country_code)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Ad(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateField(auto_now_add=True)
    modified = models.DateField(auto_now=True)
    url = models.URLField()
    car = models.ForeignKey('Car', null=True)

    def __str__(self):
        return self.title
