from django.contrib import admin
from django.urls import path
from cosmetics import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.components, name='components'),
    path('component/<int:id>/', views.component, name='component'),
    path('request/<int:request_id>/', views.cosmetic_composition,
         name='cosmetic_composition'),
    path('add/<int:id>/', views.add_component, name='add_component'),
]
