from django.contrib import admin
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path
import requests
from .models import DigitalTwinInstanceRelationship, DigitalTwinProperty, SystemContext, DTDLModel, DigitalTwinInstance, Device, DigitalTwinDevicePropertyBinding, ModelElement, ModelRelationship, DeviceType, DeviceProperty


@admin.action(description="Importar Systems do Middts")
def importar_systems_do_middts(modeladmin, request, queryset):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/")
    if response.status_code == 200:
        systems = response.json()
        for system in systems:
            obj, created = SystemContext.objects.update_or_create(
                middts_id=system["id"],
                defaults={"name": system["name"], "description": system.get("description", "")},
            )
            if created:
                modeladmin.message_user(request, f"Importado: {system['name']}")
            else:
                modeladmin.message_user(request, f"Atualizado: {system['name']}")
    else:
        modeladmin.message_user(request, "Erro ao importar Systems", level="error")


@admin.register(SystemContext)
class SystemContextAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "middts_id")
    actions = [importar_systems_do_middts]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-middts/', self.admin_site.admin_view(self.import_middts), name='import-middts'),
        ]
        return custom_urls + urls
    
    def import_middts(self, request):
        response = requests.post(f"{settings.SITE_URL}/api/systems/import/")  # Chamando API interna
        if response.status_code == 200:
            messages.success(request, "Importação de Systems do Middts concluída com sucesso!")
        else:
            messages.error(request, "Erro ao importar Systems do Middts.")
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_middts_url"] = "import-middts/"
        return super().changelist_view(request, extra_context=extra_context)


@admin.action(description="Importar Modelos DTDL do Middts")
def importar_modelos_dtdl_do_middts(modeladmin, request, queryset):
    for dtdlmodel in queryset:
        response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{dtdlmodel.system.middts_id}/dtdlmodels/")
        if response.status_code == 200:
            models = response.json()
            for model in models:
                obj, created = DTDLModel.objects.update_or_create(
                    middts_id=model["id"],
                    defaults={"system": dtdlmodel.system, "name": model["name"], "specification": model["specification"]},
                )
                if created:
                    modeladmin.message_user(request, f"Importado: {model['name']}")
                else:
                    modeladmin.message_user(request, f"Atualizado: {model['name']}")
        else:
            modeladmin.message_user(request, f"Erro ao importar modelos do system {dtdlmodel.system.name}", level="error")


@admin.register(DTDLModel)
class DTDLModelAdmin(admin.ModelAdmin):
    list_display = ("name", "system", "middts_id", "dtmi")
    actions = [importar_modelos_dtdl_do_middts]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-dtdlmodels/', self.admin_site.admin_view(self.import_dtdlmodels), name='import-dtdlmodels'),
        ]
        return custom_urls + urls

    def import_dtdlmodels(self, request):
        response = requests.post(f"{settings.SITE_URL}/api/dtdlmodels/import/")
        if response.status_code == 200:
            messages.success(request, "Importação de Modelos DTDL concluída com sucesso!")
        else:
            messages.error(request, "Erro ao importar Modelos DTDL.")
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_dtdlmodels_url"] = "import-dtdlmodels/"
        return super().changelist_view(request, extra_context=extra_context)


@admin.action(description="Importar Instâncias de Gêmeos Digitais do Middts")
def importar_instances_do_middts(modeladmin, request, queryset):
    for instance in queryset:
        response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{instance.model.system.middts_id}/instances/")
        if response.status_code == 200:
            instances = response.json()
            for instance in instances:
                obj, created = DigitalTwinInstance.objects.update_or_create(
                    middts_id=instance["id"],
                    defaults={"model": instance.model, "name": instance["name"], "properties": instance.get("properties", {})},
                )
                if created:
                    modeladmin.message_user(request, f"Importado: {instance['name']}")
                else:
                    modeladmin.message_user(request, f"Atualizado: {instance['name']}")

                # Importar relacionamentos
                relationships = instance.get("relationships", [])
                for relationship in relationships:
                    target_instance, _ = DigitalTwinInstance.objects.update_or_create(
                        middts_id=relationship["target_id"],
                        defaults={"model": instance.model, "name": relationship["target_name"], "properties": relationship.get("target_properties", {})},
                    )
                    DigitalTwinInstanceRelationship.objects.update_or_create(
                        source_instance=obj,
                        relationship=relationship["name"],
                        defaults={"target_instance": target_instance},
                    )
        else:
            modeladmin.message_user(request, f"Erro ao importar instâncias do modelo {instance.model.name}", level="error")

class DigitalTwinPropertyInline(admin.TabularInline):
            model = DigitalTwinProperty
            extra = 1

class DigitalTwinInstanceRelationshipInline(admin.TabularInline):
    model = DigitalTwinInstanceRelationship
    fk_name = "source_instance"
    extra = 1

@admin.register(DigitalTwinInstance)
class DigitalTwinInstanceAdmin(admin.ModelAdmin):
    list_display = ("name", "model", "middts_id")
    actions = [importar_instances_do_middts]
    inlines = [DigitalTwinPropertyInline, DigitalTwinInstanceRelationshipInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-instances/', self.admin_site.admin_view(self.import_instances), name='import-instances'),
        ]
        return custom_urls + urls

    def import_instances(self, request):
        response = requests.post(f"{settings.SITE_URL}/api/instances/import/")
        if response.status_code == 200:
            messages.success(request, "Importação de Instâncias concluída com sucesso!")
        else:
            messages.error(request, "Erro ao importar Instâncias.")
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_instances_url"] = "import-instances/"
        return super().changelist_view(request, extra_context=extra_context)
        


@admin.register(DigitalTwinProperty)
class DigitalTwinPropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "value", "instance")
    list_filter = ("instance",)
    search_fields = ("name", "instance__name")


@admin.register(DigitalTwinInstanceRelationship)
class DigitalTwinInstanceRelationshipAdmin(admin.ModelAdmin):
    list_display = ("source_instance", "relationship", "target_instance")


@admin.register(ModelElement)
class ModelElementAdmin(admin.ModelAdmin):
    list_display = ("name", "element_type", "model", "data_type", "target_model")
    list_filter = ("element_type", "model")
    search_fields = ("name", "model__name")

@admin.register(ModelRelationship)
class ModelRelationshipAdmin(admin.ModelAdmin):
    list_display = ("source_model", "name", "target_model")
    list_filter = ("source_model", "target_model")
    search_fields = ("source_model__name", "target_model__name", "name")


@admin.action(description="Importar Devices do Middts")
def importar_devices_do_middts(modeladmin, request, queryset):
    response = requests.get(f"{settings.MIDDTS_API_URL}/facade/devices/")
    if response.status_code == 200:
        devices = response.json()
        for device in devices:
            device_type, _ = DeviceType.objects.update_or_create(
                middts_id=device["device_type"]["id"],
                defaults={"name": device["device_type"]["name"], "description": device["device_type"].get("description", "")},
            )
            device_instance, created = Device.objects.update_or_create(
                middts_id=device["id"],
                defaults={"device_type": device_type, "identifier": device["identifier"], "name": device["name"], "status": device["status"], "user": request.user},
            )
            if created:
                modeladmin.message_user(request, f"Importado: {device['name']}")
            else:
                modeladmin.message_user(request, f"Atualizado: {device['name']}")

            for prop in device["properties"]:
                DeviceProperty.objects.update_or_create(
                    device_type=device_type,
                    name=prop["name"],
                    defaults={"data_type": prop["data_type"], "middts_id": prop["id"]},
                )
    else:
        modeladmin.message_user(request, "Erro ao importar Devices", level="error")




@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "middts_id", "device_type")
    readonly_fields = ("name", "middts_id")
    actions = [importar_devices_do_middts]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-devices/', self.admin_site.admin_view(self.import_devices), name='import-devices'),
        ]
        return custom_urls + urls


    def import_devices(self, request):
        response = requests.get(f"{settings.MIDDTS_API_URL}/facade/devices/")
        if response.status_code == 200:
            devices = response.json()
            for device in devices:
                device_type = None
                device_type_id = device["type_id"]
                if device_type_id:
                    device_type, _ = DeviceType.objects.update_or_create(
                        middts_id=device_type_id,
                        defaults={"name": device["type_name"],},
                    )
                device_instance, created = Device.objects.update_or_create(
                    middts_id=device["id"],
                    defaults={"device_type": device_type, "identifier": device["identifier"], "name": device["name"], "status": device["status"]},
                )
                if created:
                    messages.success(request, f"Importado: {device['name']}")
                else:
                    messages.success(request, f"Atualizado: {device['name']}")

                for prop in device["properties"]:
                    DeviceProperty.objects.update_or_create(
                        device=device_instance,
                        name=prop["name"],
                        defaults={"data_type": prop["type"], "middts_id": prop["id"]},
                    )
        else:
            messages.error(request, "Erro ao importar Devices", level="error")

        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_devices_url"] = "import-devices/"
        return super().changelist_view(request, extra_context=extra_context)
    
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DeviceType)
class DeviceTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "middts_id")
    readonly_fields = ("name", "middts_id")
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DeviceProperty)
class DevicePropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "data_type", "middts_id", 'device')
    readonly_fields = ("name", "data_type", "middts_id")
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DigitalTwinDevicePropertyBinding)
class DigitalTwinDevicePropertyBindingAdmin(admin.ModelAdmin):
    list_display = ("dt_property", "device_property")
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-bindings/', self.admin_site.admin_view(self.import_bindings), name='import-bindings'),
        ]
        return custom_urls + urls
    
    def import_bindings(self, request):
        for system_id in SystemContext.objects.values_list("middts_id", flat=True):
            response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/properties/connected/")
            if response.status_code == 200:
                bindings = response.json()
                for binding in bindings:
                    import ipdb; ipdb.set_trace()
                    dt_instance = DigitalTwinInstance.objects.get(middts_id=binding["dtinstance"])
                    dt_property = DigitalTwinProperty.objects.get(middts_id=binding["property"], instance=dt_instance)
                    device_property = DeviceProperty.objects.get(middts_id=binding["device_property"])
                    DigitalTwinDevicePropertyBinding.objects.update_or_create(
                        dt_property=dt_property,
                        device_property=device_property,
                    )
                messages.success(request, "Bindings importados com sucesso.")
            else:
                messages.error(request, "Erro ao importar Bindings.")
        return redirect("..")
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_bindings_url"] = "import-bindings/"
        return super().changelist_view(request, extra_context=extra_context)