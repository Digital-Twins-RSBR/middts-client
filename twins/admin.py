from django.contrib import admin
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path
import requests
from .models import DigitalTwinInstanceRelationship, SystemContext, DTDLModel, DigitalTwinInstance, Device, DigitalTwinDeviceBinding, ModelElement, ModelRelationship


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
    for model in queryset:
        response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{model.system.middts_id}/instances/")
        if response.status_code == 200:
            instances = response.json()
            for instance in instances:
                obj, created = DigitalTwinInstance.objects.update_or_create(
                    middts_id=instance["id"],
                    defaults={"model": model, "name": instance["name"], "properties": instance.get("properties", {})},
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
                        defaults={"model": model, "name": relationship["target_name"], "properties": relationship.get("target_properties", {})},
                    )
                    DigitalTwinInstanceRelationship.objects.update_or_create(
                        source_instance=obj,
                        relationship=relationship["name"],
                        defaults={"target_instance": target_instance},
                    )
        else:
            modeladmin.message_user(request, f"Erro ao importar instâncias do modelo {model.name}", level="error")


@admin.register(DigitalTwinInstance)
class DigitalTwinInstanceAdmin(admin.ModelAdmin):
    list_display = ("name", "model", "middts_id")
    actions = [importar_instances_do_middts]

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


admin.site.register(Device)
admin.site.register(DigitalTwinDeviceBinding)