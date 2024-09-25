from django.contrib import admin
from cosmetics.models import ChemicalElement, CosmeticOrder, OrderComponent

admin.site.register(ChemicalElement)
admin.site.register(CosmeticOrder)
admin.site.register(OrderComponent)
