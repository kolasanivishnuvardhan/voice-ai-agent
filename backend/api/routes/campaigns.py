"""Campaign API routes for outbound reminders and follow-ups."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from backend.api.controllers.campaign_controller import CampaignController

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignTriggerRequest(BaseModel):
    """Payload to trigger campaign tasks."""

    campaign_type: Literal["reminder", "followup", "vaccination"]
    patient_ids: list[str]


@router.post("/trigger")
async def trigger_campaign(request: CampaignTriggerRequest) -> dict[str, Any]:
    """Trigger campaign tasks for given patients."""
    controller = CampaignController()
    return await controller.trigger(request.campaign_type, request.patient_ids)
