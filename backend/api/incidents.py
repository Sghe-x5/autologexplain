from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.services.incidents import IncidentNotFoundError, InvalidStatusTransitionError, create_manual_incident, update_incident_status

router = APIRouter()


class ManualIncidentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    service: str = Field(min_length=1, max_length=128)
    environment: str = Field(min_length=1, max_length=64)
    category: str = Field(default="unknown", min_length=1, max_length=64)
    severity: str = Field(default="error", min_length=1, max_length=32)
    message: str = Field(default="", max_length=2000)
    actor: str = Field(default="incident-api", min_length=1, max_length=100)


class UpdateIncidentStatusRequest(BaseModel):
    status: Literal["acknowledged", "mitigated", "resolved", "reopened"]
    actor: str = Field(default="incident-api", min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=1000)






@router.post("", status_code=status.HTTP_201_CREATED)
def create_incident(payload: ManualIncidentCreateRequest):
    try:
        return create_manual_incident(
            title=payload.title,
            service=payload.service,
            environment=payload.environment,
            category=payload.category,
            severity=payload.severity,
            message=payload.message,
            actor=payload.actor,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed_to_create_incident") from exc


@router.patch("/{incident_id}/status")
def patch_incident_status(incident_id: str, payload: UpdateIncidentStatusRequest):
    try:
        return update_incident_status(
            incident_id=incident_id,
            next_status=payload.status,
            actor=payload.actor,
            note=payload.note,
        )
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident_not_found") from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed_to_update_status") from exc










