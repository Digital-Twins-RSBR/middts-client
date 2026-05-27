from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
    login_view,
    logout_view,
    index,
    import_all,
    dtexplorer,
    list_instances,
    list_systems,
    list_dtdlmodels,
    update_property,
    delete_binding,
    manage_bindings,
)
from .api import api

urlpatterns = [
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', login_required(index), name='dashboard'),
    path('import-all/', login_required(import_all), name='import_all'),
    path('api/', api.urls),
    path('systems/', login_required(list_systems), name='list_systems'),
    path('dtdlmodels/', login_required(list_dtdlmodels), name='list_dtdlmodels'),
    path('instances/', login_required(list_instances), name='list_instances'),
    path('instances/<int:instance_id>/properties/update/', login_required(update_property), name='update_property'),
    path('dtexplorer/', login_required(dtexplorer), name='dtexplorer'),
    path('manage-bindings/', login_required(manage_bindings), name='manage_bindings'),
    path('delete-binding/<int:binding_id>/', login_required(delete_binding), name='delete_binding'),
]
