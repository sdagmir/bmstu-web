from django.contrib import admin
from django.urls import path

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from cosmetics import views

schema_view = get_schema_view(
    openapi.Info(
        title="Create cosmetics API",
        default_version='v1',
        description="API for creating cosmetics",
        contact=openapi.Contact(email="galimabitov@mail.ru"),
        license=openapi.License(name="RIP License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny,],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger',
         cache_timeout=0), name='schema-swagger-ui'),

    #################################################

    path('component', views.get_components_list, name='components_list'),
    path('component/', views.ChemicalComponent.as_view(),
         name='component_post'),
    path('component/<int:pk>', views.ChemicalComponent.as_view(),
         name='chemical_component_detail'),
    path('component/<int:pk>/add', views.post_component_to_formulation,
         name='post_component_to_formulation'),
    path('component/<int:pk>/add_image',
         views.update_element_image, name='update_element_image'),

    #################################################

    path('cosmetic_formulations', views.get_created_formulations,
         name='cosmetic_formulations'),
    path('cosmetic_formulations/<int:pk>', views.get_cosmetic_formulation,
         name='cosmetic_formulation'),
    path('cosmetic_formulations/<int:pk>/put', views.put_cosmetic_formulation,
         name='cosmetic_formulation_put'),
    path('cosmetic_formulations/<int:pk>/form', views.form_cosmetic_formulation,
         name='cosmetic_formulation_form'),
    path('cosmetic_formulations/<int:pk>/resolve', views.resolve_cosmetic_formulation,
         name='cosmetic_formulation_resolve'),
    path('cosmetic_formulations/<int:pk>/delete', views.delete_cosmetic_formulation,
         name='cosmetic_formulation_delete'),

    #################################################

    path('component_in_formulation/<int:formulation_pk>/<int:component_pk>/put', views.put_chemical_element_in_formulation,
         name='component_in_formulation_put'),
    path('component_in_formulation/<int:formulation_pk>/<int:component_pk>/delete', views.delete_chemical_element_in_formulation,
         name='component_in_formulation_delete'),

    #################################################

    path('user/create', views.create_user, name='user_create'),
    path('user/login', views.login_user, name='user_login'),
    path('user/logout', views.logout_user, name='user_logout'),
    path('user/update', views.update_user, name='user_update'),
]
