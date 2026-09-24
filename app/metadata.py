from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceMeta:
    name: str
    layer: str
    active: bool = False
    version: str = "2.0.0"


def tag_service(app, attr_name, name, layer, active=False):
    svc = getattr(app, attr_name, None)
    if svc is not None:
        svc._service_meta = ServiceMeta(name=name, layer=layer, active=active)
