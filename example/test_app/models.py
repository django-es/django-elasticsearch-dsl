from django.db import models


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

    def __str__(self):
        return self.name


COUNTRIES = {
    'FR': 'France',
    'UK': 'United Kingdom',
    'ES': 'Spain',
    'IT': 'Italya',
}


class Manufacturer(models.Model):
    name = models.CharField(max_length=255)
    country_code = models.CharField(max_length=2)
    logo = models.ImageField(blank=True)
    created = models.DateField()

    def country(self):
        return COUNTRIES.get(self.country_code, self.country_code)

    def __str__(self):
        return self.name


class Category(models.Model):
    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class Ad(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateField(auto_now_add=True)
    modified = models.DateField(auto_now=True)
    url = models.URLField()
    car = models.ForeignKey(
        'Car', related_name='ads', null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.title
