"""Reports router — monthly Best-of report endpoints."""
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/")
async def list_reports(year: int | None = Query(None, description="Filter by year")):
    """List available monthly reports."""
    return {"reports": [], "year": year}


@router.get("/{year}/{month}")
async def get_report(year: int, month: int):
    """Get a specific monthly report."""
    return {"year": year, "month": month, "report": None}


@router.post("/generate")
async def generate_report(year: int = Query(...), month: int = Query(...)):
    """Trigger generation of a monthly report."""
    return {"year": year, "month": month, "status": "generated"}


@router.get("/{year}/{month}/html", response_class=HTMLResponse)
async def get_report_html(year: int, month: int):
    """Get the HTML version of a monthly report."""
    html = f"<html><body><h1>Report {year}/{month:02d}</h1><p>No data yet.</p></body></html>"
    return HTMLResponse(content=html)
