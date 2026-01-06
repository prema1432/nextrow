from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app import db
from app.ui import UI_HTML


router = APIRouter()


@router.get("/")
def root():
    return HTMLResponse(UI_HTML)


@router.get("/health")
def health():
    return {
        "message": "Adobe Analytics Website Scanner",
        "db_connected": db.scans_col is not None,
        "endpoints": {
            "start_scan": "POST /scan",
            "list_scans": "GET /scans",
            "delete_scan": "DELETE /scan/{scan_id}",
            "check_status": "GET /scan/{scan_id}",
            "get_report_data": "GET /report/{scan_id}/data",
            "download_excel": "GET /report/{scan_id}",
            "download_simple_excel": "GET /report/{scan_id}/simple",
        },
    }
