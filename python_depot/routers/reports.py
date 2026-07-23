"""Reports router — backed by python_depot.pydepot.reports.ReportGenerator."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from python_depot.database import get_db
from python_depot.pydepot.reports import ReportGenerator

router = APIRouter()


def _get_report_generator(db: Session = Depends(get_db)) -> ReportGenerator:
    return ReportGenerator(db)


@router.get("/")
async def list_reports(
    year: int | None = Query(None, description="Filter by year"),
    generator: ReportGenerator = Depends(_get_report_generator),
):
    """List available monthly reports."""
    reports = generator.list_reports(year)
    return {"reports": reports, "year": year}


@router.get("/{year}/{month}")
async def get_report(
    year: int,
    month: int,
    generator: ReportGenerator = Depends(_get_report_generator),
):
    """Get a specific monthly report."""
    report = generator.get_report(year, month)
    if report is None:
        return {"year": year, "month": month, "report": None}
    return report


@router.post("/generate")
async def generate_report(
    year: int = Query(...),
    month: int = Query(...),
    generator: ReportGenerator = Depends(_get_report_generator),
):
    """Trigger generation of a monthly report via ReportGenerator."""
    result = generator.generate_report(year, month)
    # Merge real data with status field for backward compat with tests
    return {**result, "status": "generated"}


@router.get("/{year}/{month}/html", response_class=HTMLResponse)
async def get_report_html(
    year: int,
    month: int,
    generator: ReportGenerator = Depends(_get_report_generator),
):
    """Get the HTML version of a monthly report."""
    result = generator.generate_report(year, month)
    html = result.get("report_html", "")
    if not html:
        html = f"<html><body><h1>Report {year}/{month:02d}</h1><p>No data yet.</p></body></html>"
    return HTMLResponse(content=html)
