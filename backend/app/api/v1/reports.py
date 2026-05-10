"""Scheduled Reports API endpoints.

Endpoints:
  POST   /reports/                  Create a scheduled report
  GET    /reports/                  List all scheduled reports
  GET    /reports/{id}              Get report detail
  PATCH  /reports/{id}              Update report config
  DELETE /reports/{id}              Delete a report
  POST   /reports/{id}/run          Manually trigger a report generation
  GET    /reports/{id}/history      Get report execution history
  GET    /reports/runs/{run_id}/download  Download a generated report
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_analyst
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate, ReportOut, ReportRunOut
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Scheduled Reports"])


@router.post("/", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a recurring report from any dashboard."""
    report = await ReportService.create(db, current_user.org_id, current_user.id, data)
    return ReportOut.model_validate(report)


@router.get("/", response_model=list[ReportOut])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all scheduled reports for the organization."""
    reports = await ReportService.list_all(db, current_user.org_id)
    return [ReportOut.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a scheduled report by ID."""
    report = await ReportService.get_by_id(db, report_id, current_user.org_id)
    if not report:
        raise NotFoundError(resource="Report", resource_id=report_id)
    return ReportOut.model_validate(report)


@router.patch("/{report_id}", response_model=ReportOut)
async def update_report(
    report_id: str,
    data: ReportUpdate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Update report schedule, format, or recipients."""
    report = await ReportService.update(db, report_id, current_user.org_id, data)
    if not report:
        raise NotFoundError(resource="Report", resource_id=report_id)
    return ReportOut.model_validate(report)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Delete a scheduled report and all its history."""
    success = await ReportService.delete(db, report_id, current_user.org_id)
    if not success:
        raise NotFoundError(resource="Report", resource_id=report_id)


@router.post("/{report_id}/run", response_model=ReportRunOut, status_code=status.HTTP_201_CREATED)
async def trigger_report(
    report_id: str,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a one-off report generation."""
    report = await ReportService.get_by_id(db, report_id, current_user.org_id)
    if not report:
        raise NotFoundError(resource="Report", resource_id=report_id)
    run = await ReportService.generate_report(db, report)
    return ReportRunOut.model_validate(run)


@router.get("/{report_id}/history", response_model=list[ReportRunOut])
async def report_history(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get execution history for a scheduled report."""
    # Verify org ownership
    report = await ReportService.get_by_id(db, report_id, current_user.org_id)
    if not report:
        raise NotFoundError(resource="Report", resource_id=report_id)
    runs = await ReportService.get_history(db, report_id)
    return [ReportRunOut.model_validate(r) for r in runs]


@router.get("/runs/{run_id}/download")
async def download_report(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a generated report file."""
    from sqlalchemy import select
    from app.models.report import ReportRun
    result = await db.execute(select(ReportRun).where(ReportRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run or not run.file_path:
        raise NotFoundError(resource="ReportRun", resource_id=run_id)

    import os
    if not os.path.exists(run.file_path):
        raise NotFoundError(resource="ReportFile", resource_id=run_id)

    return FileResponse(
        path=run.file_path,
        media_type="text/html",
        filename=os.path.basename(run.file_path),
    )
