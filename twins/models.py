import requests
from django.db import models
from django.conf import settings

MIDDTS_API_URL = settings.MIDDTS_API_URL  # Ensure the Middts URL is configured

class SystemContext(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Relationship with the Middts System

    def save(self, *args, **kwargs):
        """
        Whenever a SystemContext is created or edited, it will be synchronized with Middts.
        If there is already a `middts_id`, it will be updated in Middts.
        If there is no `middts_id`, it will be created in Middts.
        """
        super().save(*args, **kwargs)  # Save locally first
        # Payload to send to Middts
        payload = {
            "name": self.name,
            "description": self.description
        }

        headers = {
            "Content-Type": "application/json"
        }

        if self.middts_id:
            # Update in Middts
            response = requests.put(f"{MIDDTS_API_URL}/orchestrator/systems/{self.middts_id}/", json=payload, headers=headers)
        else:
            # Create in Middts
            response = requests.post(f"{MIDDTS_API_URL}/orchestrator/systems/", json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.middts_id = data.get("id")
                super().save(update_fields=["middts_id"])  # Update the local middts_id after creation

    def __str__(self):
        return self.name


class DTDLModel(models.Model):
    system = models.ForeignKey(SystemContext, on_delete=models.CASCADE, related_name="dtdl_models")
    name = models.CharField(max_length=255)
    specification = models.JSONField()
    dtmi = models.CharField(max_length=255, null=True, blank=True)  # Unique model identifier
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Middts ID

    class Meta:
        unique_together = ("system", "middts_id", 'dtmi')

    def save(self, *args, **kwargs):
        """
        Whenever a DTDLModel is created or edited, it will be synchronized with Middts.
        If there is already a `middts_id`, it will be updated in Middts.
        If there is no `middts_id`, it will be created in Middts.
        """
        # Extract DTMI from the specification
        if not self.dtmi and "@id" in self.specification:
            self.dtmi = self.specification["@id"]
        super().save(*args, **kwargs)  # Save locally first

        # Payload to send to Middts
        payload = {
            "name": self.name,
            "specification": self.specification
        }

        headers = {
            "Content-Type": "application/json"
        }

        if self.middts_id:
            # Update in Middts
            response = requests.put(
                f"{MIDDTS_API_URL}/orchestrator/systems/{self.system.middts_id}/dtdlmodels/{self.middts_id}/",
                json=payload,
                headers=headers
            )
        else:
            # Create in Middts
            response = requests.post(
                f"{MIDDTS_API_URL}/orchestrator/systems/{self.system.middts_id}/dtdlmodels/",
                json=payload,
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                self.middts_id = data.get("id")
                super().save(update_fields=["middts_id"])  # Update the local middts_id after creation

        # Automatic extraction of elements and relationships
        ModelElement.extract_elements_from_specification(self)
        self.extract_relationships()
        ModelRelationship.update_relationships()

    def extract_relationships(self):
        """
        Extract relationships from the `specification` JSON and store them in the database.
        """
        data = self.specification
        if "contents" in data:
            for item in data["contents"]:
                if item.get("@type") == "Relationship":
                    target_dtmi = item["target"]
                    target_model = DTDLModel.objects.filter(dtmi__icontains=target_dtmi, system=self.system).first()
                    if target_model:
                        ModelRelationship.objects.update_or_create(
                            source_model=self,
                            target_model=target_model,
                            name=item["name"],
                            defaults={"target_dtmi": target_dtmi}  # Now we save the relationship with the target DTMI
                        )

    def __str__(self):
        return f"{self.name} - {self.system.name}"


class ModelElement(models.Model):
    """
    Represents elements within a DTDL Model.
    They can be Properties, Commands, or Relationships.
    """
    model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, related_name="elements")
    name = models.CharField(max_length=255)
    element_type = models.CharField(max_length=50)  # Ex: Property, Command, Relationship
    data_type = models.CharField(max_length=255, blank=True, null=True)  # Data type (if it's a property)
    target_model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, null=True, blank=True, related_name="target_elements")

    class Meta:
        unique_together = ("model", "name", "element_type")  # Ensure uniqueness of elements within a model

    def __str__(self):
        return f"{self.name} ({self.element_type}) - {self.model.name}"

    @staticmethod
    def extract_elements_from_specification(dtdl_model):
        """
        Extract elements (properties, commands, relationships) from the `specification` and save them in the database.
        """
        data = dtdl_model.specification
        if "contents" in data:
            for item in data["contents"]:
                element_type = item.get("@type")
                if element_type in ["Property", "Command", "Relationship"]:
                    target_model = None
                    if element_type == "Relationship":
                        target_model = DTDLModel.objects.filter(name=item["target"], system=dtdl_model.system).first()
                    
                    ModelElement.objects.update_or_create(
                        model=dtdl_model,
                        name=item["name"],
                        element_type=element_type,
                        defaults={
                            "data_type": item.get("schema", None) if element_type == "Property" else None,
                            "target_model": target_model,
                        }
                    )


class ModelRelationship(models.Model):
    """
    Represents relationships between DTDL Models.
    """
    source_model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, related_name="outgoing_relationships")
    target_model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, related_name="incoming_relationships", null=True, blank=True)
    name = models.CharField(max_length=255)
    target_dtmi = models.CharField(max_length=255)  # Stores the target model's DTMI before linking it correctly
    element = models.ForeignKey("ModelElement", on_delete=models.CASCADE, null=True, blank=True, related_name="relationships")
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Middts ID

    class Meta:
        unique_together = ("source_model", "target_model", "name")  # Ensure uniqueness of the relationship

    def __str__(self):
        return f"{self.source_model.name} -[{self.name}]-> {self.target_model.name if self.target_model else self.target_model_id}"

    @staticmethod
    def update_relationships():
        """
        Update relationships after DTDL models are loaded,
        ensuring that ModelElements are linked correctly.
        """
        for relationship in ModelRelationship.objects.filter(target_model__isnull=True):
            target_model = DTDLModel.objects.filter(dtmi=relationship.target_dtmi).first()

            if target_model:
                relationship.target_model = target_model
                # Link to the correct element
                element = ModelElement.objects.filter(
                    model=relationship.source_model,
                    name=relationship.name,
                    element_type="Relationship"
                ).first()

                if element:
                    relationship.element = element
                relationship.save()


class DigitalTwinInstance(models.Model):
    model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, related_name="instances")
    name = models.CharField(max_length=255)
    properties_json = models.JSONField(default=dict)
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Middts ID

    def __str__(self):
        return f"{self.name} ({self.model.name})"
    

class DigitalTwinProperty(models.Model):
    """
    Represents the properties of Digital Twins.
    """
    instance = models.ForeignKey(DigitalTwinInstance, on_delete=models.CASCADE, related_name="properties")
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Middts ID

    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    causal = models.BooleanField(default=False)  # Only causal properties can be edited

    def __str__(self):
        return f"{self.instance.name} - {self.name}"

    def save(self, *args, **kwargs):
        """
        Save the property and synchronize with Middts if it is a causal property.
        """
        old = DigitalTwinProperty.objects.filter(pk=self.pk).first()
        super().save(*args, **kwargs)
        if self.type == "Property" or self.causal:
            if old and old.value != self.value:
                result = self.update_value(self.value)
                if "error" in result:
                    raise Exception(result["error"])

    def update_value(self, new_value):
        """
        Update the property value in Middts.
        """
        url = f"{MIDDTS_API_URL}/orchestrator/systems/{self.instance.model.system.middts_id}/instances/{self.instance.middts_id}/properties/{self.middts_id}/"
        response = requests.put(url, json={"value": new_value})
        if response.status_code == 200:
            self.value = new_value
            self.save(update_fields=["value"])
            return response.json()
        else:
            return {"error": "Failed to update the property in Middts"}


class DigitalTwinInstanceRelationship(models.Model):
    source_instance = models.ForeignKey(
        "DigitalTwinInstance",
        on_delete=models.CASCADE,
        related_name="source_relationships"
    )
    target_instance = models.ForeignKey(
        "DigitalTwinInstance",
        on_delete=models.CASCADE,
        related_name="target_relationships"
    )
    relationship = models.CharField(max_length=255)  # Relationship name, e.g., "connected to"
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Middts ID

    class Meta:
        unique_together = ("source_instance", "target_instance", "relationship")

    def __str__(self):
        return f"{self.source_instance} -> ({self.relationship}) -> {self.target_instance}"

    def save(self, *args, **kwargs):
        """
        Save the relationship and synchronize with Middts.
        """
        super().save(*args, **kwargs)  # Save locally first

        # Payload to send to Middts
        payload = {
            "source_instance": self.source_instance.middts_id,
            "target_instance": self.target_instance.middts_id,
            "relationship": self.relationship
        }

        headers = {
            "Content-Type": "application/json"
        }

        if self.middts_id:
            # Update in Middts
            response = requests.put(
                f"{MIDDTS_API_URL}/orchestrator/systems/{self.source_instance.model.system.middts_id}/instances/relationships/{self.middts_id}/",
                json=payload,
                headers=headers
            )
        else:
            # Create in Middts
            response = requests.post(
                f"{MIDDTS_API_URL}/orchestrator/systems/{self.source_instance.model.system.middts_id}/instances/relationships/",
                json=payload,
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                self.middts_id = data.get("id")
                super().save(update_fields=["middts_id"])  # Update the local middts_id after creation


class Device(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=[("active", "Active"), ("inactive", "Inactive")])
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Adding the middts_id field
    device_type = models.ForeignKey("DeviceType", null=True, on_delete=models.CASCADE, related_name="devices")

    def __str__(self):
        return self.name


class DeviceType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Middts ID

    def __str__(self):
        return self.name


class DeviceProperty(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="properties")
    name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=255)
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Middts ID

    class Meta:
        unique_together = ("device", "name")

    def __str__(self):
        return f"{self.device.name} - {self.name}"
    

class DigitalTwinDevicePropertyBinding(models.Model):
    dt_property = models.ForeignKey(DigitalTwinProperty, on_delete=models.CASCADE)
    device_property = models.ForeignKey(DeviceProperty, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.dt_property.instance.name} -> {self.device_property.device.name}"
    
    class Meta:
        unique_together = ("dt_property", "device_property")

