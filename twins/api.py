from ninja import NinjaAPI
from django.conf import settings
from django.shortcuts import get_object_or_404
from twins.models import DigitalTwinInstanceRelationship, DigitalTwinProperty, SystemContext, DTDLModel, DigitalTwinInstance, Device, DigitalTwinDevicePropertyBinding, DeviceProperty
from twins import middts_api
from .utils import upsert_instance_relationship

api = NinjaAPI()


def import_systems_from_middts():
    response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/")
    if response.status_code == 200:
        systems = response.json()
        for system in systems:
            SystemContext.objects.update_or_create(
                middts_id=system["id"],
                defaults={"name": system["name"], "description": system.get("description", "")},
            )
        return {"message": "Systems import completed successfully!"}, 200
    return {"error": "Error importing Systems"}, response.status_code


def import_dtdlmodels_from_middts():
    systems = SystemContext.objects.filter(middts_id__isnull=False)
    for system in systems:
        response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system.middts_id}/dtdlmodels/")
        if response.status_code == 200:
            models = response.json()
            for model in models:
                DTDLModel.objects.update_or_create(
                    middts_id=model["id"],
                    defaults={"system": system, "name": model["name"], "specification": model["specification"]},
                )
    return {"message": "DTDL Models import completed successfully!"}, 200


def import_instances_from_middts():
    systems = SystemContext.objects.filter(middts_id__isnull=False)
    for system in systems:
        response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system.middts_id}/instances/")
        if response.status_code == 200:
            instances = response.json()
            for instance in instances:
                model_middts_id = instance.get('model')
                if model_middts_id:
                    dtdlmodel = DTDLModel.objects.filter(middts_id=model_middts_id).first()
                    if not dtdlmodel:
                        resp = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system.middts_id}/dtdlmodels/{model_middts_id}/")
                        if resp.status_code == 200:
                            model_data = resp.json()
                            dtdlmodel = DTDLModel.objects.create(
                                system=system,
                                name=model_data.get("name", f"Model {model_middts_id}"),
                                specification=model_data.get("specification", {}),
                                middts_id=model_middts_id,
                            )
                    if not dtdlmodel:
                        continue
                    instance_name = f"{dtdlmodel.name} - Instance {instance['id']}"
                    dt_instance, created = DigitalTwinInstance.objects.update_or_create(
                        middts_id=instance["id"],
                        defaults={
                            "model": dtdlmodel,
                            "name": instance_name,
                            "properties_json": instance.get("digitaltwininstanceproperty_set", {}),
                        },
                    )
                    for relationship in instance.get("sourcerelationships", []):
                        target_instance = DigitalTwinInstance.objects.filter(middts_id=relationship["target_instance"]).first()
                        if target_instance:
                            upsert_instance_relationship(
                                source_instance=dt_instance,
                                target_instance=target_instance,
                                relationship_name=relationship.get("relationship_name"),
                                middts_id=relationship.get("id"),
                            )
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
    return {"message": "Instances import completed successfully!"}, 200


def import_relationships_from_middts():
    systems = SystemContext.objects.filter(middts_id__isnull=False)
    for system in systems:
        response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system.middts_id}/relationships/")
        if response.status_code == 200:
            relationships = response.json()
            for relationship in relationships:
                relationship_name = relationship.get('relationship_name')
                middts_id = relationship.get('id')
                if middts_id:
                    source_middts_id = relationship.get('source_instance')
                    target_middts_id = relationship.get('target_instance')
                    if source_middts_id and target_middts_id:
                        source_instance = DigitalTwinInstance.objects.filter(middts_id=source_middts_id).first()
                        target_instance = DigitalTwinInstance.objects.filter(middts_id=target_middts_id).first()
                        if source_instance and target_instance:
                            upsert_instance_relationship(
                                source_instance=source_instance,
                                target_instance=target_instance,
                                relationship_name=relationship_name,
                                middts_id=middts_id,
                            )
    return {"message": "Instances relationships completed successfully!"}, 200


def import_bindings_from_middts():
    imported = 0
    skipped = 0
    for system in SystemContext.objects.filter(middts_id__isnull=False):
        response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system.middts_id}/instances/properties/connected/")
        if response.status_code == 200:
            bindings = response.json()
            for binding in bindings:
                dt_instance = DigitalTwinInstance.objects.filter(middts_id=binding.get("dtinstance")).first()
                dt_property = None
                if dt_instance:
                    dt_property = DigitalTwinProperty.objects.filter(
                        middts_id=binding.get("property"),
                        instance=dt_instance,
                    ).first()
                    if not dt_property and binding.get("property_name"):
                        dt_property = DigitalTwinProperty.objects.filter(
                            instance=dt_instance,
                            name=binding.get("property_name"),
                        ).first()
                device_property = DeviceProperty.objects.filter(middts_id=binding.get("device_property")).first()
                if dt_instance and dt_property and device_property:
                    DigitalTwinDevicePropertyBinding.objects.update_or_create(
                        dt_property=dt_property,
                        device_property=device_property,
                    )
                    imported += 1
                else:
                    skipped += 1
        else:
            return {"error": "Error importing Bindings"}, response.status_code
    return {"message": "Bindings import completed successfully!", "imported": imported, "skipped": skipped}, 200

### ============================
###  API to Import Systems
### ============================

@api.post("/systems/import/")
def import_systems(request):
    result, status = import_systems_from_middts()
    if status == 200:
        return result
    return result, status


### ============================
###  API to Import DTDL Models
### ============================

@api.post("/dtdlmodels/import/")
def import_dtdlmodels(request):
    result, status = import_dtdlmodels_from_middts()
    if status == 200:
        return result
    return result, status


### ============================
###  API to Import Digital Twin Instances
### ============================

@api.post("/instances/import/")
def import_instances(request):
    result, status = import_instances_from_middts()
    if status == 200:
        return result
    return result, status


@api.post("/bindings/import/")
def import_bindings(request):
    result, status = import_bindings_from_middts()
    if status == 200:
        return result
    return result, status

# Create a new system
@api.post("/systems/")
def create_system(request, name: str, description: str = None):
    payload = {"name": name, "description": description}
    response = middts_api.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/", json=payload)
    if response.status_code == 200:
        return response.json()
    return response.text, response.status_code


# List systems
@api.get("/systems/")
def list_systems(request):
    response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/")
    return response.json()


# Create a DTDL model
@api.post("/systems/{system_id}/dtdlmodels/")
def create_dtdlmodel(request, system_id: int, name: str, specification: dict):
    payload = {"name": name, "specification": specification}
    response = middts_api.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/dtdlmodels/", json=payload)
    return response.json()


# List DTDL models
@api.get("/systems/{system_id}/dtdlmodels/")
def list_dtdlmodels(request, system_id: int):
    response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/dtdlmodels/")
    return response.json()


# Create a Digital Twin instance
@api.post("/systems/{system_id}/instances/")
def create_instance(request, system_id: int, dtdl_model_id: int, name: str):
    payload = {"dtdl_model_id": dtdl_model_id, "name": name}
    response = middts_api.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/", json=payload)
    return response.json()

# Digital Twin Relationship imports
@api.post("/relationships/import/")
def import_relationships(request):
    return import_relationships_from_middts()

# List instances
@api.get("/systems/{system_id}/instances/")
def list_instances(request, system_id: int):
    response = middts_api.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/")
    return response.json()


# Bind Digital Twin instance to a Device
@api.post("/systems/{system_id}/instances/{dtinstance_id}/bind/")
def bind_dtinstance_device(request, system_id: int, dtinstance_id: int, device_id: int):
    payload = {"device_property_id": device_id}
    response = middts_api.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/{dtinstance_id}/bind/", json=payload)
    return response.json()


# Update a causal property of a Digital Twin
@api.put("/systems/{system_id}/instances/{dtinstance_id}/properties/{property_id}/")
def update_causal_property(request, system_id: int, dtinstance_id: int, property_id: int, value: str):
    payload = {"value": value}
    response = middts_api.put(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/{dtinstance_id}/properties/{property_id}/", json=payload)
    return response.json()


# Execute Cypher query in Neo4j
@api.post("/systems/{system_id}/instances/query/")
def execute_cypher_query(request, system_id: int, query: str):
    payload = {"query": query}
    response = middts_api.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/query/", json=payload)
    return response.json()
