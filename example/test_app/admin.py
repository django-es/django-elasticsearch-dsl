from django.contrib import admin

from .models import Car, Manufacturer, Ad


admin.site.register(Car)
admin.site.register(Manufacturer)
admin.site.register(Ad)
