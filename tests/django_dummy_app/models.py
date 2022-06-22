from django.db import models


class Continent(models.Model):
    """"""

    name = models.CharField(max_length=255, unique=True)


class Country(models.Model):
    name = models.CharField(max_length=255, unique=True)
    area = models.BigIntegerField()
    population = models.BigIntegerField()
    continent = models.ForeignKey(Continent, models.CASCADE, related_name="countries")

    def __str__(self):
        return f"{self.name}"

    @property
    def event_count(self):
        return self.events.all().count()

    def event_count_func(self):
        return self.events.all().count()


class Event(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateTimeField()
    country = models.ForeignKey(Country, models.CASCADE, related_name="events")
    source = models.TextField()
    comment = models.TextField()
    null_field = models.IntegerField(null=True, default=None)

    def __str__(self):
        return f"{self.name} - {self.country} - {self.date.strftime('%Y-%m-%d')}"
