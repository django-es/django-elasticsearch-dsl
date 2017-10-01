from django.contrib import admin

from .models import Ad, Category, Car, Manufacturer


admin.site.register(Ad)
admin.site.register(Category)
admin.site.register(Car)
admin.site.register(Manufacturer)
