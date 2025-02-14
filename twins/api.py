import requests
from ninja import NinjaAPI
from django.conf import settings
from django.shortcuts import get_object_or_404
from twins.models import DigitalTwinInstanceRelationship, DigitalTwinProperty, SystemContext, DTDLModel, DigitalTwinInstance, Device, DigitalTwinDevicePropertyBinding

api = NinjaAPI()


### ============================
###  API para Importar Systems
### ============================

@api.post("/systems/import/")
def importar_systems(request):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/")
    if response.status_code == 200:
        systems = response.json()
        for system in systems:
            SystemContext.objects.update_or_create(
                middts_id=system["id"],
                defaults={"name": system["name"], "description": system.get("description", "")},
            )
        return {"message": "Importação de Systems concluída com sucesso!"}
    return {"error": "Erro ao importar Systems"}, response.status_code


### ============================
###  API para Importar Modelos DTDL
### ============================

@api.post("/dtdlmodels/import/")
def importar_dtdlmodels(request):
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
    return {"message": "Importação de Modelos DTDL concluída com sucesso!"}


### ============================
###  API para Importar Instâncias de Gêmeos Digitais
### ============================

@api.post("/instances/import/")
def importar_instances(request):
    systems = SystemContext.objects.filter(middts_id__isnull=False)
    for system in systems:
        response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system.middts_id}/instances/")
        if response.status_code == 200:
            instances = response.json()
            for instance in instances:
                # Nome baseado no modelo
                model_middts_id = instance.get('model')
                if model_middts_id:
                    dtdlmodel = DTDLModel.objects.filter(middts_id=model_middts_id).first()
                    instance_name = f"{dtdlmodel.name} - Instância {instance['id']}"
                    # Criar ou atualizar a instância
                    dt_instance, created = DigitalTwinInstance.objects.update_or_create(
                        middts_id=instance["id"],
                        defaults={
                            "model": dtdlmodel,
                            "name": instance_name,
                            "properties_json": instance.get("digitaltwininstanceproperty_set", {}),
                        },
                    )

                    # Criar os relacionamentos da instância com outros gêmeos digitais
                    for relationship in instance.get("sourcerelationships", []):
                        target_instance = DigitalTwinInstance.objects.filter(middts_id=relationship["target_instance"]).first()

                        if target_instance:
                            DigitalTwinInstanceRelationship.objects.update_or_create(
                                source_instance=dt_instance,
                                target_instance=target_instance,
                                defaults={"relationship": relationship["relationship_name"]},
                            )

                    # Criar as propriedades da instância
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

    return {"message": "Importação de Instâncias concluída com sucesso!"}

# Criar um novo sistema
@api.post("/systems/")
def create_system(request, name: str, description: str = None):
    payload = {"name": name, "description": description}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/", json=payload)
    if response.status_code == 200:
        return response.json()
    return response.text, response.status_code


# Listar sistemas
@api.get("/systems/")
def list_systems(request):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/")
    return response.json()


# Criar um modelo DTDL
@api.post("/systems/{system_id}/dtdlmodels/")
def create_dtdlmodel(request, system_id: int, name: str, specification: dict):
    payload = {"name": name, "specification": specification}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/dtdlmodels/", json=payload)
    return response.json()


# Listar modelos DTDL
@api.get("/systems/{system_id}/dtdlmodels/")
def list_dtdlmodels(request, system_id: int):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/dtdlmodels/")
    return response.json()


# Criar uma instância de Gêmeo Digital
@api.post("/systems/{system_id}/instances/")
def create_instance(request, system_id: int, dtdl_model_id: int, name: str):
    payload = {"dtdl_model_id": dtdl_model_id, "name": name}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/", json=payload)
    return response.json()


# Listar instâncias
@api.get("/systems/{system_id}/instances/")
def list_instances(request, system_id: int):
    response = requests.get(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/")
    return response.json()


# Associar Gêmeo Digital a um Dispositivo
@api.post("/systems/{system_id}/instances/{dtinstance_id}/bind/")
def bind_dtinstance_device(request, system_id: int, dtinstance_id: int, device_id: int):
    payload = {"device_property_id": device_id}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/{dtinstance_id}/bind/", json=payload)
    return response.json()



# Atualizar uma propriedade causal de um Gêmeo Digital
@api.put("/systems/{system_id}/instances/{dtinstance_id}/properties/{property_id}/")
def update_causal_property(request, system_id: int, dtinstance_id: int, property_id: int, value: str):
    payload = {"value": value}
    response = requests.put(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/{dtinstance_id}/properties/{property_id}/", json=payload)
    return response.json()


# Executar consulta Cypher no Neo4j
@api.post("/systems/{system_id}/instances/query/")
def execute_cypher_query(request, system_id: int, query: str):
    payload = {"query": query}
    response = requests.post(f"{settings.MIDDTS_API_URL}/orchestrator/systems/{system_id}/instances/query/", json=payload)
    return response.json()
