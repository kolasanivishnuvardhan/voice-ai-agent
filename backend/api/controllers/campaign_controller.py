"""Controller for outbound campaign trigger endpoints."""

from __future__ import annotations

from typing import Any

from scheduler.campaign_worker import run_campaign


class CampaignController:
    """Dispatches campaign jobs to Celery worker."""

    async def trigger(self, campaign_type: str, patient_ids: list[str]) -> dict[str, Any]:
        """Queue campaign task for each patient."""
        task_ids: list[str] = []
        for patient_id in patient_ids:
            task = run_campaign.delay(patient_id, campaign_type)
            task_ids.append(task.id)
        return {"queued": len(task_ids), "task_ids": task_ids}
