"""
URL configuration for client project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from twins.views import index, list_instances, list_systems, list_dtdlmodels, update_property
from twins.api import api

urlpatterns = [
    path("", index, name="index"),  # Página inicial
    path('admin/', admin.site.urls),
    path("api/", api.urls),
    path("systems/", list_systems, name="list_systems"),
    path("dtdlmodels/", list_dtdlmodels, name="list_dtdlmodels"),
    path("instances/", list_instances, name="list_instances"),
    # path("instances/<int:instance_id>/properties/<int:property_id>/update/", update_property, name="update_property"),
    path("instances/<int:instance_id>/properties/update/", update_property, name="update_property"),
]
