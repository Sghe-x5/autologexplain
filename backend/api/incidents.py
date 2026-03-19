from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.services.incidents import (
    IncidentNotFoundError,
    InvalidStatusTransitionError,
    create_manual_incident,
    get_evidence,
    get_incident,
    get_incidents,
    get_timeline,
    update_incident_status,
)
from backend.services.incidents.constants import INCIDENT_STATUSES

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


@router.get("")
def list_incidents(
    *,
    incident_status: str | None = Query(
        None,
        alias="status",
        description=f"Allowed: {', '.join(INCIDENT_STATUSES)}",
    ),
    service: str | None = None,
    environment: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if incident_status and incident_status not in INCIDENT_STATUSES:
        raise HTTPException(status_code=422, detail=f"unknown_status:{incident_status}")

    items = get_incidents(
        status=incident_status,
        service=service,
        environment=environment,
        category=category,
        severity=severity,
        q=q,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "count": len(items)}


@router.get("/{incident_id}")
def get_incident_card(incident_id: str):
    card = get_incident(incident_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident_not_found")
    return card


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


@router.get("/{incident_id}/timeline")
def incident_timeline(incident_id: str, limit: int = Query(100, ge=1, le=500)):
    try:
        timeline = get_timeline(incident_id, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed_to_fetch_timeline") from exc

    if not timeline:
        card = get_incident(incident_id)
        if card is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident_not_found")
    return {"incident_id": incident_id, "events": timeline}


@router.get("/{incident_id}/evidence")
def incident_evidence(incident_id: str, limit: int = Query(200, ge=1, le=500)):
    try:
        return get_evidence(incident_id, limit=limit)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident_not_found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed_to_fetch_evidence") from exc


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: str):
    card = get_incident(incident_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident_not_found")

    if card.get("status") != "resolved":
        try:
            update_incident_status(
                incident_id=incident_id,
                next_status="resolved",
                actor="incident-api",
                note="deleted_via_api",
            )
        except InvalidStatusTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
