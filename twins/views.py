from django.shortcuts import render, get_object_or_404
from .models import DigitalTwinInstance, DigitalTwinInstanceRelationship, ModelRelationship, SystemContext, DTDLModel



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

    return render(request, "instances.html", {
        "systems": systems,
        "selected_system": selected_system,
        "instances": instances,
        "relationships": relationships
    })



