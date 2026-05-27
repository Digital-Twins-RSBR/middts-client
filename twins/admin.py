from django.contrib import admin
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path
import requests
from twins import middts_api
from .models import DigitalTwinInstanceRelationship, DigitalTwinProperty, SystemContext, DTDLModel, DigitalTwinInstance, Device, DigitalTwinDevicePropertyBinding, ModelElement, ModelRelationship, DeviceType, DeviceProperty
from .utils import upsert_instance_relationship


@admin.action(description="Import Systems from Middts")
def import_systems_from_middts(modeladmin, request, queryset):
    response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/")
    if response.status_code == 200:
        systems = response.json()
        for system in systems:
            obj, created = SystemContext.objects.update_or_create(
                middts_id=system["id"],
                defaults={"name": system["name"], "description": system.get("description", "")},
            )
            if created:
                modeladmin.message_user(request, f"Imported: {system['name']}")
            else:
                modeladmin.message_user(request, f"Updated: {system['name']}")
    else:
        modeladmin.message_user(request, "Error importing Systems", level="error")


@admin.register(SystemContext)
class SystemContextAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "middts_id")
    actions = [import_systems_from_middts]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-middts/', self.admin_site.admin_view(self.import_middts), name='import-middts'),
        ]
        return custom_urls + urls
    
    def import_middts(self, request):
        response = requests.post(f"{settings.SITE_URL}/api/systems/import/")  # Calling internal API
        if response.status_code == 200:
            messages.success(request, "Systems import from Middts completed successfully!")
        else:
            messages.error(request, "Error importing Systems from Middts.")
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_middts_url"] = "import-middts/"
        return super().changelist_view(request, extra_context=extra_context)


@admin.action(description="Import DTDL Models from Middts")
def import_dtdlmodels_from_middts(modeladmin, request, queryset):
    for dtdlmodel in queryset:
        response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{dtdlmodel.system.middts_id}/dtdlmodels/")
        if response.status_code == 200:
            models = response.json()
            for model in models:
                obj, created = DTDLModel.objects.update_or_create(
                    middts_id=model["id"],
                    defaults={"system": dtdlmodel.system, "name": model["name"], "specification": model["specification"]},
                )
                if created:
                    modeladmin.message_user(request, f"Imported: {model['name']}")
                else:
                    modeladmin.message_user(request, f"Updated: {model['name']}")
        else:
            modeladmin.message_user(request, f"Error importing models from system {dtdlmodel.system.name}", level="error")


@admin.action(description="Create and Import Digital Twin Instance from Middts")
def create_and_import_instance_from_middts(modeladmin, request, queryset):
    for dtdlmodel in queryset:
        # Create instance in Middts
        payload = {"dtdl_model_id": dtdlmodel.middts_id, "name": f"Instance of {dtdlmodel.name}"}
        response = middts_api.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{dtdlmodel.system.middts_id}/instances/", json=payload)
        if response.status_code == 200:
            instance = response.json()
            instance_id = instance["id"]

            # Import the created instance
            response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{dtdlmodel.system.middts_id}/instances/{instance_id}")
            if response.status_code == 200:
                instance = response.json()
                model_middts_id = instance.get('model')

                # Start with the original model from the queryset
                model_for_defaults = dtdlmodel

                # If Middts reports a different model id, try to resolve it locally or fetch
                if model_middts_id and model_middts_id != (dtdlmodel.middts_id if dtdlmodel else None):
                    found = DTDLModel.objects.filter(middts_id=model_middts_id).first()
                    if found:
                        model_for_defaults = found
                    else:
                        # Try to fetch the model from Middts and create locally
                        resp = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{dtdlmodel.system.middts_id}/dtdlmodels/{model_middts_id}")
                        if resp.status_code == 200:
                            model_data = resp.json()
                            model_for_defaults = DTDLModel.objects.create(
                                system=dtdlmodel.system,
                                name=model_data.get("name", f"Model {model_middts_id}"),
                                specification=model_data.get("specification", {}),
                                middts_id=model_middts_id,
                            )

                if not model_for_defaults:
                    modeladmin.message_user(request, f"Skipped importing instance {instance.get('id')} because model is missing", level=messages.ERROR)
                else:
                    instance_name = f"{model_for_defaults.name} - Instance {instance['id']}"
                    dt_instance, created = DigitalTwinInstance.objects.update_or_create(
                        middts_id=instance["id"],
                        defaults={
                            "model": model_for_defaults,
                            "name": instance_name,
                            "properties_json": instance.get("digitaltwininstanceproperty_set", {}),
                        },
                    )

                    # Create the instance relationships with other digital twins
                    for relationship in instance.get("sourcerelationships", []):
                        target_instance = DigitalTwinInstance.objects.filter(middts_id=relationship["target_instance"]).first()

                        if target_instance:
                            upsert_instance_relationship(
                                source_instance=dt_instance,
                                target_instance=target_instance,
                                relationship_name=relationship.get("relationship_name"),
                            )

                    # Create the instance properties
                    for prop in instance.get("digitaltwininstanceproperty_set", []):
                        DigitalTwinProperty.objects.update_or_create(
                            instance=dt_instance,
                            middts_id=prop["id"],
                            name=prop["name"],
                            defaults={
                                "type": prop["type"],
                                "value": prop["value"],
                                "causal": prop["causal"]
                            },
                        )
                    if created:
                        modeladmin.message_user(request, f"Imported: {instance_name}")
                    else:
                        modeladmin.message_user(request, f"Updated: {instance_name}")
            else:
                modeladmin.message_user(request, f"Error importing instance from model {dtdlmodel.name}", level="error")
        else:
            modeladmin.message_user(request, f"Error creating instance for model {dtdlmodel.name}", level="error")


@admin.register(DTDLModel)
class DTDLModelAdmin(admin.ModelAdmin):
    list_display = ("name", "system", "middts_id", "dtmi")
    list_filter = ("system",)
    actions = [import_dtdlmodels_from_middts, create_and_import_instance_from_middts]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-dtdlmodels/', self.admin_site.admin_view(self.import_dtdlmodels), name='import-dtdlmodels'),
        ]
        return custom_urls + urls

    def import_dtdlmodels(self, request):
        response = requests.post(f"{settings.SITE_URL}/api/dtdlmodels/import/")
        if response.status_code == 200:
            messages.success(request, "DTDL Models import completed successfully!")
        else:
            messages.error(request, "Error importing DTDL Models.")
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_dtdlmodels_url"] = "import-dtdlmodels/"
        return super().changelist_view(request, extra_context=extra_context)


@admin.action(description="Import Digital Twin Instances from Middts")
def import_instances_from_middts(modeladmin, request, queryset):
    for instance in queryset:
        response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{instance.model.system.middts_id}/instances/")
        if response.status_code == 200:
            instances = response.json()
            for instance in instances:
                obj, created = DigitalTwinInstance.objects.update_or_create(
                    middts_id=instance["id"],
                    defaults={"model": instance.model, "name": instance["name"], "properties_json": instance.get("properties", {})},
                )
                if created:
                    modeladmin.message_user(request, f"Imported: {instance['name']}")
                else:
                    modeladmin.message_user(request, f"Updated: {instance['name']}")

                # Import relationships
                relationships = instance.get("relationships", [])
                for relationship in relationships:
                    target_instance, _ = DigitalTwinInstance.objects.update_or_create(
                        middts_id=relationship["target_id"],
                        defaults={"model": instance.model, "name": relationship["target_name"], "properties_json": relationship.get("target_properties", {})},
                    )
                    upsert_instance_relationship(
                        source_instance=obj,
                        target_instance=target_instance,
                        relationship_name=relationship.get("name"),
                    )
        else:
            modeladmin.message_user(request, f"Error importing instances from model {instance.model.name}", level="error")

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
    list_filter = ("model__system", "model")
    actions = [import_instances_from_middts]
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
            messages.success(request, "Instances import completed successfully!")
        else:
            messages.error(request, "Error importing Instances.")
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


@admin.action(description="Import Digital Twin Instance Relationships from Middts")
def import_relationships_from_middts(modeladmin, request, queryset):
    for relationship in queryset:
        response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{relationship.source_instance.model.system.middts_id}/instances/relationships/")
        if response.status_code == 200:
            relationships = response.json()
            for rel in relationships:
                source_instance = DigitalTwinInstance.objects.get(middts_id=rel["source_instance"])
                target_instance = DigitalTwinInstance.objects.get(middts_id=rel["target_instance"])
                existed = DigitalTwinInstanceRelationship.objects.filter(
                    source_instance=source_instance,
                    target_instance=target_instance,
                    relationship=rel.get("relationship"),
                ).exists()
                upsert_instance_relationship(
                    source_instance=source_instance,
                    target_instance=target_instance,
                    relationship_name=rel.get("relationship"),
                    middts_id=rel.get("id"),
                )
                if not existed:
                    modeladmin.message_user(request, f"Imported: {rel['relationship']}")
                else:
                    modeladmin.message_user(request, f"Updated: {rel['relationship']}")
        else:
            modeladmin.message_user(request, f"Error importing relationships from system {relationship.source_instance.model.system.name}", level="error")


@admin.register(DigitalTwinInstanceRelationship)
class DigitalTwinInstanceRelationshipAdmin(admin.ModelAdmin):
    list_display = ("source_instance", "relationship", "target_instance")
    list_filter = ("source_instance__model__system",)
    actions = [import_relationships_from_middts]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-relationships/', self.admin_site.admin_view(self.import_relationships), name='import-relationships'),
        ]
        return custom_urls + urls

    def import_relationships(self, request):
        response = requests.post(f"{settings.SITE_URL}/api/relationships/import/")
        if response.status_code == 200:
            messages.success(request, "Relationships import completed successfully!")
        else:
            messages.error(request, "Error importing Relationships.")
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_relationships_url"] = "import-relationships/"
        return super().changelist_view(request, extra_context=extra_context)


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


@admin.action(description="Import Devices from Middts")
def import_devices_from_middts(modeladmin, request, queryset):
    response = middts_api.get(f"{settings.MIDDTS_API_URL}/facade/devices/")
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
                modeladmin.message_user(request, f"Imported: {device['name']}")
            else:
                modeladmin.message_user(request, f"Updated: {device['name']}")

            for prop in device["properties"]:
                DeviceProperty.objects.update_or_create(
                    device_type=device_type,
                    name=prop["name"],
                    defaults={"data_type": prop["data_type"], "middts_id": prop["id"]},
                )
    else:
        modeladmin.message_user(request, "Error importing Devices", level="error")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "middts_id", "device_type")
    readonly_fields = ("name", "middts_id")
    actions = [import_devices_from_middts]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-devices/', self.admin_site.admin_view(self.import_devices), name='import-devices'),
        ]
        return custom_urls + urls


    def import_devices(self, request):
        response = middts_api.get(f"{settings.MIDDTS_API_URL}/facade/devices/")
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
                    messages.success(request, f"Imported: {device['name']}")
                else:
                    messages.success(request, f"Updated: {device['name']}")

                for prop in device["properties"]:
                    DeviceProperty.objects.update_or_create(
                        device=device_instance,
                        name=prop["name"],
                        defaults={"data_type": prop["type"], "middts_id": prop["id"]},
                    )
        else:
            messages.error(request, "Error importing Devices", level="error")

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
        imported = 0
        skipped = 0
        for system_id in SystemContext.objects.values_list("middts_id", flat=True):
            response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/properties/connected/")
            if response.status_code == 200:
                bindings = response.json()
                for binding in bindings:
                    dt_instance = DigitalTwinInstance.objects.filter(middts_id=binding.get("dtinstance")).first()
                    if not dt_instance:
                        skipped += 1
                        continue

                    dt_property = DigitalTwinProperty.objects.filter(middts_id=binding.get("property"), instance=dt_instance).first()
                    if not dt_property and binding.get("property_name"):
                        dt_property = DigitalTwinProperty.objects.filter(
                            instance=dt_instance,
                            name=binding.get("property_name"),
                        ).first()
                    if not dt_property:
                        skipped += 1
                        continue

                    device_property = DeviceProperty.objects.filter(middts_id=binding.get("device_property")).first()
                    if not device_property:
                        skipped += 1
                        continue

                    DigitalTwinDevicePropertyBinding.objects.update_or_create(
                        dt_property=dt_property,
                        device_property=device_property,
                    )
                    imported += 1
                if imported:
                    messages.success(request, f"Bindings imported successfully: {imported}.")
                if skipped:
                    messages.warning(request, f"Bindings skipped due to missing references: {skipped}.")
            else:
                messages.error(request, "Error importing Bindings.")
        return redirect("..")
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_bindings_url"] = "import-bindings/"
        return super().changelist_view(request, extra_context=extra_context)