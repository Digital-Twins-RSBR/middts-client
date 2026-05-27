from django.db import IntegrityError
from .models import DigitalTwinInstanceRelationship


def upsert_instance_relationship(source_instance, target_instance, relationship_name, middts_id=None):
    """Create or return an existing DigitalTwinInstanceRelationship using the
    unique key (source_instance, target_instance, relationship).

    This helper avoids IntegrityError when the same relationship already
    exists and centralizes the logic for all import paths.
    """
    if not source_instance or not target_instance or not relationship_name:
        return None

    defaults = {"relationship": relationship_name}
    if middts_id is not None:
        defaults["middts_id"] = middts_id

    try:
        obj, created = DigitalTwinInstanceRelationship.objects.update_or_create(
            source_instance=source_instance,
            target_instance=target_instance,
            relationship=relationship_name,
            defaults=defaults,
        )
        return obj
    except IntegrityError:
        return DigitalTwinInstanceRelationship.objects.filter(
            source_instance=source_instance,
            target_instance=target_instance,
            relationship=relationship_name,
        ).first()
