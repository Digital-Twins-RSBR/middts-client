import requests
from ninja import NinjaAPI
from django.conf import settings
from django.shortcuts import get_object_or_404
from twins.models import DigitalTwinInstanceRelationship, DigitalTwinProperty, SystemContext, DTDLModel, DigitalTwinInstance, Device, DigitalTwinDevicePropertyBinding

api = NinjaAPI()

### ============================
###  API to Import Systems
### ============================

@api.post("/systems/import/")
def import_systems(request):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/")
    if response.status_code == 200:
        systems = response.json()
        for system in systems:
            SystemContext.objects.update_or_create(
                middts_id=system["id"],
                defaults={"name": system["name"], "description": system.get("description", "")},
            )
        return {"message": "Systems import completed successfully!"}
    return {"error": "Error importing Systems"}, response.status_code


### ============================
###  API to Import DTDL Models
### ============================

@api.post("/dtdlmodels/import/")
def import_dtdlmodels(request):
    systems = SystemContext.objects.filter(middts_id__isnull=False)
    for system in systems:
        response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system.middts_id}/dtdlmodels/")
        if response.status_code == 200:
            models = response.json()
            for model in models:
                DTDLModel.objects.update_or_create(
                    middts_id=model["id"],
                    defaults={"system": system, "name": model["name"], "specification": model["specification"]},
                )
    return {"message": "DTDL Models import completed successfully!"}


### ============================
###  API to Import Digital Twin Instances
### ============================

@api.post("/instances/import/")
def import_instances(request):
    systems = SystemContext.objects.filter(middts_id__isnull=False)
    for system in systems:
        response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system.middts_id}/instances/")
        if response.status_code == 200:
            instances = response.json()
            for instance in instances:
                # Name based on the model
                model_middts_id = instance.get('model')
                if model_middts_id:
                    dtdlmodel = DTDLModel.objects.filter(middts_id=model_middts_id).first()
                    instance_name = f"{dtdlmodel.name} - Instance {instance['id']}"
                    # Create or update the instance
                    dt_instance, created = DigitalTwinInstance.objects.update_or_create(
                        middts_id=instance["id"],
                        defaults={
                            "model": dtdlmodel,
                            "name": instance_name,
                            "properties_json": instance.get("digitaltwininstanceproperty_set", {}),
                        },
                    )

                    # Create the instance relationships with other digital twins
                    for relationship in instance.get("sourcerelationships", []):
                        target_instance = DigitalTwinInstance.objects.filter(middts_id=relationship["target_instance"]).first()

                        if target_instance:
                            DigitalTwinInstanceRelationship.objects.update_or_create(
                                source_instance=dt_instance,
                                target_instance=target_instance,
                                defaults={"relationship": relationship["relationship_name"]},
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

    return {"message": "Instances import completed successfully!"}

# Create a new system
@api.post("/systems/")
def create_system(request, name: str, description: str = None):
    payload = {"name": name, "description": description}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/", json=payload)
    if response.status_code == 200:
        return response.json()
    return response.text, response.status_code


# List systems
@api.get("/systems/")
def list_systems(request):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/")
    return response.json()


# Create a DTDL model
@api.post("/systems/{system_id}/dtdlmodels/")
def create_dtdlmodel(request, system_id: int, name: str, specification: dict):
    payload = {"name": name, "specification": specification}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/dtdlmodels/", json=payload)
    return response.json()


# List DTDL models
@api.get("/systems/{system_id}/dtdlmodels/")
def list_dtdlmodels(request, system_id: int):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/dtdlmodels/")
    return response.json()


# Create a Digital Twin instance
@api.post("/systems/{system_id}/instances/")
def create_instance(request, system_id: int, dtdl_model_id: int, name: str):
    payload = {"dtdl_model_id": dtdl_model_id, "name": name}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/", json=payload)
    return response.json()


# List instances
@api.get("/systems/{system_id}/instances/")
def list_instances(request, system_id: int):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/")
    return response.json()


# Bind Digital Twin instance to a Device
@api.post("/systems/{system_id}/instances/{dtinstance_id}/bind/")
def bind_dtinstance_device(request, system_id: int, dtinstance_id: int, device_id: int):
    payload = {"device_property_id": device_id}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/{dtinstance_id}/bind/", json=payload)
    return response.json()


# Update a causal property of a Digital Twin
@api.put("/systems/{system_id}/instances/{dtinstance_id}/properties/{property_id}/")
def update_causal_property(request, system_id: int, dtinstance_id: int, property_id: int, value: str):
    payload = {"value": value}
    response = requests.put(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/{dtinstance_id}/properties/{property_id}/", json=payload)
    return response.json()


# Execute Cypher query in Neo4j
@api.post("/systems/{system_id}/instances/query/")
def execute_cypher_query(request, system_id: int, query: str):
    payload = {"query": query}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/query/", json=payload)
    return response.json()
