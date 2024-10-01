from django.contrib import admin
from django.urls import path
from cosmetics import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.components, name='components'),
    path('component/<int:id>/', views.component, name='component'),
    path('add_component/', views.add_component, name='add_component'),
    path('create_cosmetic/<int:request_id>/',
         views.cosmetic_composition, name='cosmetic_composition'),
    path('delete_cosmetic/<int:id>/', views.delete_cosmetic,
         name='delete_cosmetic'),
]
