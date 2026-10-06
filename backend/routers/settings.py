from fastapi import APIRouter

from ..db import get_settings, update_settings
from ..models import SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings() -> dict:
    return get_settings()


@router.put("")
def write_settings(body: SettingsUpdate) -> dict:
    changes = body.model_dump(exclude_unset=True)
    return update_settings(changes)
