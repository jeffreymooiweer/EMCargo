"""Untrusted delivery archives can only produce new, unapproved concepts."""
import io
import json
import zipfile
from uuid import uuid4

from app.core.messages import error
from app.schemas.deliveries import DeliveryIn, LegIn, AllocationIn
from app.services import deliveries as d


def read(content):
    if len(content) > d.MAX_RECORD:
        raise error(413, "delivery.too_large")
    try:
        if content.startswith(b"PK"):
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                matches = [entry for entry in archive.infolist() if entry.filename == "delivery.json"]
                if len(matches) != 1 or matches[0].file_size > d.MAX_RECORD or matches[0].flag_bits & 1:
                    raise ValueError()
                # Read only the manifest; never extract paths or attachments.
                with archive.open(matches[0]) as stream:
                    content = stream.read(d.MAX_RECORD + 1)
        if len(content) > d.MAX_RECORD:
            raise ValueError()
        envelope = json.loads(content)
        if envelope["format"] != "emcargo.delivery" or envelope["format_version"] not in {"1.0", "2.0"}:
            raise ValueError()
        value = envelope["delivery"]
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, KeyError, TypeError, UnicodeError, zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise error(422, "delivery.import") from exc


def restore(db, user, content):
    d.planner(db, user)
    value = read(content)
    try:
        ids = {part["id"]: str(uuid4()) for part in value["legs"]}
        if len(ids) != len(value["legs"]):
            raise ValueError()
        legs = [LegIn.model_validate({**{k: v for k, v in part.items() if k in LegIn.model_fields}, "id": ids[part["id"]]}) for part in value["legs"]]
        allocations = [AllocationIn.model_validate({**{k: v for k, v in allocation.items() if k in AllocationIn.model_fields},
            "id": str(uuid4()), "leg_ids": [ids[lid] for lid in allocation["leg_ids"]], "leg_quantities": {}}) for allocation in value["allocations"]]
        from app.schemas.routing import Stop
        stops = [Stop.model_validate({k: v for k, v in stop.items() if k in Stop.model_fields}) for stop in value.get("stops", [])]
        payload = DeliveryIn(name=value["name"], stops=stops, legs=legs, allocations=allocations)
        sources, _ = d.load_sources(db, user, payload)
        for sid, source in sources.items():
            # A local integer id alone cannot identify a shipment from another installation.
            if d.source_fingerprint(value["sources"][sid]["export"]) != source["fingerprint"]:
                raise error(409, "delivery.source_changed")
        # Never trust imported status, review, access, lineage, files or events.
        # Onward reductions require local receipt evidence, so reset those too.
        return d.create(db, user, payload)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise error(422, "delivery.import") from exc
