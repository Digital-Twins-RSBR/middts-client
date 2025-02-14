import json
from django.conf import settings
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from .models import SystemContext, DigitalTwinInstance, DigitalTwinInstanceRelationship, DigitalTwinProperty, ModelRelationship, DTDLModel



def index(request):
    return render(request, "index.html")


def list_systems(request):
    systems = SystemContext.objects.all()
    return render(request, "systems.html", {"systems": systems})

def build_hierarchy(models, relationships):
    """
    Organiza os Modelos DTDL em uma estrutura de árvore hierárquica.
    O modelo raiz é aquele que não aparece como `target_model` de nenhum relacionamento.
    """
    hierarchy = {}

    # Inicializa todos os modelos sem pais
    for model in models:
        hierarchy[model.id] = {
            "model": model,
            "children": []
        }

    # Associa filhos aos pais com base nos relacionamentos
    for relation in relationships:
        parent_id = relation.source_model.id
        child_id = relation.target_model.id

        if parent_id in hierarchy and child_id in hierarchy:
            hierarchy[parent_id]["children"].append(hierarchy[child_id])

    # Retorna apenas os nós raiz (que não são filhos de ninguém)
    roots = [node for node in hierarchy.values() if not any(node["model"].id == rel.target_model.id for rel in relationships)]
    return roots

def list_dtdlmodels(request):
    selected_system_id = request.GET.get("system_id")  
    systems = SystemContext.objects.all()  

    if selected_system_id:
        dtdlmodels = DTDLModel.objects.filter(system_id=selected_system_id)
    else:
        dtdlmodels = DTDLModel.objects.all()

    relationships = ModelRelationship.objects.filter(source_model__in=dtdlmodels)

    hierarchy = build_hierarchy(dtdlmodels, relationships)

    return render(request, "dtdlmodels.html", {
        "systems": systems,
        "selected_system_id": int(selected_system_id) if selected_system_id else None,
        "hierarchy": hierarchy
    })


def list_instances(request):
    selected_system_id = request.GET.get("system_id")  
    systems = SystemContext.objects.all()  

    selected_system = None
    if selected_system_id:
        selected_system = get_object_or_404(SystemContext, id=selected_system_id)

    if selected_system:
        instances = DigitalTwinInstance.objects.filter(model__system=selected_system)
    else:
        instances = DigitalTwinInstance.objects.all()

    relationships = DigitalTwinInstanceRelationship.objects.filter(source_instance__in=instances)

    instances_list = [
        {
            "id": instance.id,
            "name": instance.name,
            "model": instance.model.name,
            "properties": [
                {"id": prop.id, "name": prop.name, "value": prop.value, "type": prop.type, "can_edit": prop.causal or True if prop.type and prop.type.lower() == "property" else False }
                for prop in instance.properties.all()
            ]
        }
        for instance in instances
    ]

    relationships_list = [
        {"source": rel.source_instance.id, "target": rel.target_instance.id}
        for rel in relationships
    ]

    return render(request, "instances.html", {
        "systems": systems,
        "selected_system": selected_system,
        "instances_json": json.dumps(instances_list),  # Passamos JSON puro para o template
        "relationships_json": json.dumps(relationships_list)  # JSON puro para o template
    })

@csrf_exempt
def update_property(request, instance_id):
    """
    Atualiza todas as propriedades editáveis de um Gêmeo Digital.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        properties = data.get("properties", [])
        updated_properties = []
        for prop in properties:
            try:
                property_obj = DigitalTwinProperty.objects.get(
                    id=prop["id"], instance_id=instance_id
                )
                if property_obj.causal or property_obj.type.lower() == "property":
                    property_obj.value = prop["value"]
                    property_obj.save()
                    # property_obj.update_value(prop["value"])
                    updated_properties.append({
                        "id": property_obj.id,
                        "name": property_obj.name,
                        "value": property_obj.value
                    })
            except DigitalTwinProperty.DoesNotExist:
                continue
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)

        return JsonResponse({"message": "Propriedades atualizadas", "updated_properties": updated_properties}, status=200)

    return JsonResponse({"error": "Método não permitido"}, status=405)


def dtexplorer(request):
    selected_system_id = request.GET.get("system_id")
    systems = SystemContext.objects.all()
    selected_system = None
    query_result = None
    error_message = None
    if selected_system_id:
        selected_system = get_object_or_404(SystemContext, id=selected_system_id)

    if request.method == "POST":
        cypher_query = request.POST.get("cypher_query")
        if selected_system and cypher_query:
            try:
                response = requests.post(
                    f"{settings.MIDDTS_API_URL}/orchestrator/systems/{selected_system.middts_id}/instances/query/",
                    json={"query": cypher_query}
                )
                response.raise_for_status()
                query_result = response.json()
                # Segunda consulta para buscar relacionamentos
                node_ids = [node["identity"] for result in query_result["results"] for node in result if "identity" in node]
                if node_ids:
                    relationships_query = f"MATCH (a)-[r]->(b) WHERE id(a) IN {node_ids} OR id(b) IN {node_ids} RETURN r"
                    response = requests.post(
                        f"{settings.MIDDTS_API_URL}/orchestrator/systems/{selected_system.middts_id}/instances/query/",
                        json={"query": relationships_query}
                    )
                    response.raise_for_status()
                    relationships_result = response.json()
                    query_result["relationships"] = relationships_result["results"]
            except requests.RequestException as e:
                error_message = str(e)

    return render(request, "dtexplorer.html", {
        "systems": systems,
        "selected_system": selected_system,
        "query_result": json.dumps(query_result) if query_result else None,
        "error_message": error_message
    })