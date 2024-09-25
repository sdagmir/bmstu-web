from django.contrib import admin
from django.urls import path
from lab01 import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.components, name='components'),
    path('component/<int:id>/', views.component, name='component'),
    path('request/<int:id>/', views.request, name='request')
]
