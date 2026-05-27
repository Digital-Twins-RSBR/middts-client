import json
from django.conf import settings
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from twins import middts_api
from .api import api, import_systems, import_dtdlmodels, import_instances, import_relationships, import_bindings
from .models import DeviceProperty, SystemContext, DigitalTwinInstance, DigitalTwinInstanceRelationship, DigitalTwinProperty, ModelRelationship, DTDLModel, Device, DigitalTwinDevicePropertyBinding
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    next_url = request.GET.get('next', '/dashboard/')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', '/dashboard/')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url or '/dashboard/')
        error = 'Usuário ou senha inválidos. Tente novamente.'

    return render(request, 'login.html', {
        'error': error,
        'next': next_url,
    })


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def index(request):
    return render(request, "index.html")


@login_required
def list_systems(request):
    systems = SystemContext.objects.all()
    return render(request, "systems.html", {"systems": systems})


@login_required
def import_all(request):
    actions = [
        ("Systems", lambda: import_systems(request)),
        ("DTDL Models", lambda: import_dtdlmodels(request)),
        ("Instances", lambda: import_instances(request)),
        ("Relationships", lambda: import_relationships(request)),
        ("Bindings", lambda: import_bindings(request)),
    ]
    for label, action in actions:
        result = action()
        if isinstance(result, tuple):
            body, status = result
        else:
            body, status = result, 200
        if status == 200:
            if isinstance(body, dict) and body.get('message'):
                messages.success(request, f"{label}: {body['message']}")
            else:
                messages.success(request, f"{label} imported successfully.")
        else:
            messages.error(request, f"{label}: {body.get('error', 'Failed to import')}")
    return redirect('dashboard')


def build_hierarchy(models, relationships):
    """
    Organizes DTDL Models into a hierarchical tree structure.
    The root model is the one that does not appear as `target_model` in any relationship.
    """
    hierarchy = {}

    # Initialize all models without parents
    for model in models:
        hierarchy[model.id] = {
            "model": model,
            "children": []
        }

    # Associate children with parents based on relationships
    for relation in relationships:
        parent_id = relation.source_model.id
        child_id = relation.target_model.id

        if parent_id in hierarchy and child_id in hierarchy:
            hierarchy[parent_id]["children"].append(hierarchy[child_id])

    # Return only the root nodes (which are not children of anyone)
    roots = [node for node in hierarchy.values() if not any(node["model"].id == rel.target_model.id for rel in relationships)]
    return roots

@login_required
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


@login_required
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
        "instances_json": json.dumps(instances_list),  # Pass raw JSON to the template
        "relationships_json": json.dumps(relationships_list)  # Raw JSON to the template
    })

@csrf_exempt
@login_required
def update_property(request, instance_id):
    """
    Updates all editable properties of a Digital Twin.
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

        return JsonResponse({"message": "Properties updated", "updated_properties": updated_properties}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def dtexplorer(request):
    selected_system_id = request.GET.get("system_id")
    systems = SystemContext.objects.all()
    selected_system = None
    query_result = None
    error_message = None
    warning_message = None
    submitted_query = False

    def _format_endpoint_error(exc):
        response = getattr(exc, "response", None)
        if not response:
            return str(exc)

        details = ""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                details = payload.get("detail") or payload.get("error") or payload.get("message") or json.dumps(payload)
            elif isinstance(payload, list):
                details = json.dumps(payload)
            else:
                details = str(payload)
        except ValueError:
            details = (response.text or "").strip()

        base = f"{response.status_code} error from {response.url}"
        return f"{base}: {details}" if details else base

    if selected_system_id:
        selected_system = get_object_or_404(SystemContext, id=selected_system_id)

    if request.method == "POST":
        cypher_query = request.POST.get("cypher_query")
        submitted_query = bool(cypher_query)
        if selected_system and cypher_query:
            try:
                response = middts_api.post(
                    f"{settings.MIDDTS_API_URL}/orchestrator/systems/{selected_system.middts_id}/instances/query/",
                    json={"query": cypher_query}
                )
                response.raise_for_status()
                query_result = response.json()
            except requests.HTTPError as e:
                error_message = _format_endpoint_error(e)
            except requests.RequestException as e:
                error_message = str(e)

            if query_result:
                # Second query to fetch relationships
                node_ids = [node["identity"] for result in query_result["results"] for node in result if "identity" in node]
                if node_ids:
                    relationships_query = f"MATCH (a)-[relationships_filter]->(b) WHERE id(a) IN {node_ids} OR id(b) IN {node_ids} RETURN relationships_filter"
                    try:
                        response = middts_api.post(
                            f"{settings.MIDDTS_API_URL}/orchestrator/systems/{selected_system.middts_id}/instances/query/",
                            json={"query": relationships_query}
                        )
                        response.raise_for_status()
                        relationships_result = response.json()
                        query_result["relationships"] = relationships_result["results"]
                    except requests.HTTPError as e:
                        warning_message = f"Partial result: { _format_endpoint_error(e) }"
                    except requests.RequestException as e:
                        warning_message = f"Partial result: {str(e)}"

    # Format the data for the GraphComponent
    formatted_data = {
        "nodes": [],
        "links": []
    }
    node_ids_set = set()
    link_ids_set = set()
    if query_result:
        for result in query_result["results"]:
            for element in result:
                if "identity" in element:
                    if element["identity"] not in node_ids_set:
                        formatted_data["nodes"].append({
                            "id": element["identity"],
                            "labels": element["labels"],
                            "properties": element["properties"]
                        })
                        node_ids_set.add(element["identity"])
                elif "start_node" in element and "end_node" in element:
                    link_id = (element["start_node"], element["end_node"], element["type"])
                    if link_id not in link_ids_set:
                        formatted_data["links"].append({
                            "source": element["start_node"],
                            "target": element["end_node"],
                            "type": element["type"],
                            "properties": element["properties"]
                        })
                        link_ids_set.add(link_id)
                elif "elementId" in element:
                    if element["elementId"] not in node_ids_set:
                        formatted_data["nodes"].append({
                            "id": element["elementId"],
                            "labels": element["labels"],
                            "properties": element["properties"]
                        })
                        node_ids_set.add(element["elementId"])
                elif "start" in element and "end" in element:
                    link_id = (element["start"], element["end"], element["type"])
                    if link_id not in link_ids_set:
                        formatted_data["links"].append({
                            "source": element["start"],
                            "target": element["end"],
                            "type": element["type"],
                            "properties": element["properties"]
                        })
                        link_ids_set.add(link_id)
        if "relationships" in query_result:
            for result in query_result["relationships"]:
                for element in result:
                    if "start_node" in element and "end_node" in element:
                        link_id = (element["start_node"], element["end_node"], element["type"])
                        if link_id not in link_ids_set:
                            formatted_data["links"].append({
                                "source": element["start_node"],
                                "target": element["end_node"],
                                "type": element["type"],
                                "properties": element["properties"]
                            })
                            link_ids_set.add(link_id)

    # Additional verification to remove relationships that reference unknown nodes
    known_node_ids = node_ids_set
    formatted_data["links"] = [link for link in formatted_data["links"] if link["source"] in known_node_ids and link["target"] in known_node_ids]

    return render(request, "dtexplorer.html", {
        "systems": systems,
        "selected_system": selected_system,
        "query_result_json": json.dumps(query_result) if query_result else None,
        "query_result": json.dumps(formatted_data) if query_result else None,
        "error_message": error_message,
        "warning_message": warning_message,
        "no_results": submitted_query and not query_result and not error_message
    })

@login_required
def manage_bindings(request):
    dt_properties = DigitalTwinProperty.objects.filter(digitaltwindevicepropertybinding__isnull=True)
    properties = DeviceProperty.objects.filter(digitaltwindevicepropertybinding__isnull=True)
    bindings = DigitalTwinDevicePropertyBinding.objects.all()

    if request.method == "POST":
        dt_property_id = request.POST.get("dt_property_id")
        property_id = request.POST.get("device_property_id")

        dt_property = get_object_or_404(DigitalTwinProperty, id=dt_property_id)
        property = get_object_or_404(DeviceProperty, id=property_id)

        binding, created = DigitalTwinDevicePropertyBinding.objects.update_or_create(
            dt_property=dt_property,
            device_property=property,
        )

        if created:
            messages.success(request, "Binding created successfully.")
        else:
            messages.success(request, "Binding updated successfully.")

    return render(request, "manage_bindings.html", {
        "dt_properties": dt_properties,
        "properties": properties,
        "bindings": bindings,
    })

@csrf_exempt
@login_required
def delete_binding(request, binding_id):
    if request.method == "POST":
        binding = get_object_or_404(DigitalTwinDevicePropertyBinding, id=binding_id)
        binding.delete()
        messages.success(request, "Binding deleted successfully.")
    return redirect("manage_bindings")