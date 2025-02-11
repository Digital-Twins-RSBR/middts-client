import requests
from django.db import models
from django.conf import settings

MIDDTS_API_URL = settings.MIDDTS_API_URL  # Garante que a URL do Middts esteja configurada

class SystemContext(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # Relacionamento com o System do Middts

    def save(self, *args, **kwargs):
        """
        Sempre que um SystemContext for criado ou editado, ele será sincronizado com o Middts.
        Se já existir um `middts_id`, ele será atualizado no Middts.
        Se ainda não existir um `middts_id`, ele será criado no Middts.
        """
        super().save(*args, **kwargs)  # Salva primeiro no banco local
        # Payload para envio ao Middts
        payload = {
            "name": self.name,
            "description": self.description
        }

        headers = {
            "Content-Type": "application/json"
        }

        if self.middts_id:
            # Atualiza no Middts
            response = requests.put(f"{MIDDTS_API_URL}/orchestrator/systems/{self.middts_id}/", json=payload, headers=headers)
        else:
            # Cria no Middts
            response = requests.post(f"{MIDDTS_API_URL}/orchestrator/systems/", json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.middts_id = data.get("id")
                super().save(update_fields=["middts_id"])  # Atualiza o middts_id localmente após a criação

    def __str__(self):
        return self.name


class DTDLModel(models.Model):
    system = models.ForeignKey(SystemContext, on_delete=models.CASCADE, related_name="dtdl_models")
    name = models.CharField(max_length=255)
    specification = models.JSONField()
    dtmi = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Identificador único do modelo
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # ID do Middts



    def save(self, *args, **kwargs):
        """
        Sempre que um DTDLModel for criado ou editado, ele será sincronizado com o Middts.
        Se já existir um `middts_id`, ele será atualizado no Middts.
        Se ainda não existir um `middts_id`, ele será criado no Middts.
        """
        # Extração do DTMI da specification
        if not self.dtmi and "@id" in self.specification:
            self.dtmi = self.specification["@id"]
        super().save(*args, **kwargs)  # Salva primeiro no banco local

        # Payload para envio ao Middts
        payload = {
            "name": self.name,
            "specification": self.specification
        }

        headers = {
            "Content-Type": "application/json"
        }

        if self.middts_id:
            # Atualiza no Middts
            response = requests.put(
                f"{MIDDTS_API_URL}/orchestrator/systems/{self.system.middts_id}/dtdlmodels/{self.middts_id}/",
                json=payload,
                headers=headers
            )
        else:
            # Cria no Middts
            response = requests.post(
                f"{MIDDTS_API_URL}/orchestrator/systems/{self.system.middts_id}/dtdlmodels/",
                json=payload,
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                self.middts_id = data.get("id")
                super().save(update_fields=["middts_id"])  # Atualiza o middts_id localmente após a criação

        # Extração automática de elementos e relacionamentos
        ModelElement.extract_elements_from_specification(self)
        self.extract_relationships()
        ModelRelationship.update_relationships()

    def extract_relationships(self):
        """
        Extrai relacionamentos do JSON da `specification` e armazena no banco.
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
                        defaults={"target_dtmi": target_dtmi}  # Agora salvamos a relação com o DTMI alvo
                    )

    def __str__(self):
        return f"{self.name} - {self.system.name}"


class ModelElement(models.Model):
    """
    Representa os elementos dentro de um Modelo DTDL.
    Podem ser Propriedades, Comandos ou Relacionamentos.
    """
    model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, related_name="elements")
    name = models.CharField(max_length=255)
    element_type = models.CharField(max_length=50)  # Ex: Property, Command, Relationship
    data_type = models.CharField(max_length=255, blank=True, null=True)  # Tipo de dado (caso seja propriedade)
    target_model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, null=True, blank=True, related_name="target_elements")

    class Meta:
        unique_together = ("model", "name", "element_type")  # Garante unicidade dos elementos dentro de um modelo

    def __str__(self):
        return f"{self.name} ({self.element_type}) - {self.model.name}"

    @staticmethod
    def extract_elements_from_specification(dtdl_model):
        """
        Extrai elementos (propriedades, comandos, relacionamentos) da `specification` e os salva no banco.
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
    Representa as relações entre os Modelos DTDL.
    """
    source_model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, related_name="outgoing_relationships")
    target_model = models.ForeignKey(DTDLModel, on_delete=models.CASCADE, related_name="incoming_relationships", null=True, blank=True)
    name = models.CharField(max_length=255)
    target_dtmi = models.CharField(max_length=255)  # Armazena o DTMI do modelo alvo antes de vinculá-lo corretamente
    element = models.ForeignKey("ModelElement", on_delete=models.CASCADE, null=True, blank=True, related_name="relationships")

    class Meta:
        unique_together = ("source_model", "target_model", "name")  # Garante unicidade do relacionamento

    def __str__(self):
        return f"{self.source_model.name} -[{self.name}]-> {self.target_model.name if self.target_model else self.target_model_id}"

    @staticmethod
    def update_relationships():
        """
        Atualiza os relacionamentos após os modelos DTDL serem carregados,
        garantindo que os ModelElements sejam vinculados corretamente.
        """
        for relationship in ModelRelationship.objects.filter(target_model__isnull=True):
            target_model = DTDLModel.objects.filter(dtmi=relationship.target_dtmi).first()

            if target_model:
                relationship.target_model = target_model
                # Vincular ao elemento correto
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
    properties = models.JSONField(default=dict)
    middts_id = models.IntegerField(null=True, blank=True, unique=True)  # ID do Middts

    def __str__(self):
        return f"{self.name} ({self.model.name})"


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
    relationship = models.CharField(max_length=255)  # Nome do relacionamento, ex: "conectado a"

    class Meta:
        unique_together = ("source_instance", "target_instance", "relationship")

    def __str__(self):
        return f"{self.source_instance} -> ({self.relationship}) -> {self.target_instance}"


class Device(models.Model):
    identifier = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=[("active", "Ativo"), ("inactive", "Inativo")])
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class DigitalTwinDeviceBinding(models.Model):
    dt_instance = models.ForeignKey(DigitalTwinInstance, on_delete=models.CASCADE)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    property_mapping = models.JSONField()  # Mapeia propriedades do DT para do dispositivo

    def __str__(self):
        return f"{self.dt_instance.name} -> {self.device.name}"
