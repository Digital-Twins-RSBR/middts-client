from django.urls import path
from .views import dtexplorer, index, list_instances, list_systems, list_dtdlmodels, update_property, delete_binding, manage_bindings
from .api import api

urlpatterns = [
    path("", index, name="index"),  # Página inicial
    path("api/", api.urls),
    path("systems/", list_systems, name="list_systems"),
    path("dtdlmodels/", list_dtdlmodels, name="list_dtdlmodels"),
    path("instances/", list_instances, name="list_instances"),
    path("instances/<int:instance_id>/properties/update/", update_property, name="update_property"),
    path("dtexplorer/", dtexplorer, name="dtexplorer"),
    path("manage-bindings/", manage_bindings, name="manage_bindings"),
    path("delete-binding/<int:binding_id>/", delete_binding, name="delete_binding"),
]