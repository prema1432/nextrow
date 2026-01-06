import time
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app import db
from app.services.scanner import run_scan


router = APIRouter()


@router.post("/scan")
def start_scan(start_url: str, max_pages: int = 10, max_clicks_per_page: int = 5, background_tasks: BackgroundTasks = None):
    if not start_url.startswith(("http://", "https://")):
        raise HTTPException(400, "Invalid URL")
    if db.scans_col is None or db.pages_col is None or db.reports_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    scan_id = str(uuid.uuid4())
    db.scans_col.insert_one({
        "_id": scan_id,
        "start_url": start_url,
        "status": "queued",
        "pages_scanned": 0,
        "total_pages": 0,
        "max_pages": max_pages,
        "max_clicks_per_page": max_clicks_per_page,
        "created_at": time.time()
    })

    background_tasks.add_task(run_scan, scan_id, start_url, max_pages, max_clicks_per_page)
    return {"scan_id": scan_id, "message": "Scan started in background"}


@router.get("/scans")
def list_scans(limit: int = Query(50, ge=1, le=200)):
    if db.scans_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    docs = list(
        db.scans_col.find(
            {},
            {
                "_id": 1,
                "start_url": 1,
                "status": 1,
                "pages_scanned": 1,
                "total_pages": 1,
                "created_at": 1,
                "max_pages": 1,
                "max_clicks_per_page": 1,
                "started_at": 1,
                "completed_at": 1,
                "duration_seconds": 1,
            },
        ).sort("created_at", -1).limit(limit)
    )

    return {"scans": docs}


@router.delete("/scans")
def delete_all_scans():
    if db.scans_col is None or db.pages_col is None or db.reports_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    pages_deleted = db.pages_col.delete_many({}).deleted_count
    reports_deleted = db.reports_col.delete_many({}).deleted_count
    scans_deleted = db.scans_col.delete_many({}).deleted_count

    return {"deleted": True, "scans_deleted": scans_deleted, "pages_deleted": pages_deleted, "reports_deleted": reports_deleted}


@router.post("/scan/{scan_id}/retry")
def retry_scan(scan_id: str, background_tasks: BackgroundTasks = None):
    if db.scans_col is None or db.pages_col is None or db.reports_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    scan = db.scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")

    start_url = scan.get("start_url")
    if not start_url:
        raise HTTPException(400, "Original scan is missing start_url")

    max_pages = int(scan.get("max_pages") or 10)
    max_clicks_per_page = int(scan.get("max_clicks_per_page") or 5)

    new_scan_id = str(uuid.uuid4())
    db.scans_col.insert_one({
        "_id": new_scan_id,
        "start_url": start_url,
        "status": "queued",
        "pages_scanned": 0,
        "total_pages": 0,
        "max_pages": max_pages,
        "max_clicks_per_page": max_clicks_per_page,
        "created_at": time.time(),
        "retried_from": scan_id,
    })

    background_tasks.add_task(run_scan, new_scan_id, start_url, max_pages, max_clicks_per_page)
    return {"scan_id": new_scan_id, "message": "Retry scan started"}


@router.delete("/scan/{scan_id}")
def delete_scan(scan_id: str):
    if db.scans_col is None or db.pages_col is None or db.reports_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    scan = db.scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")

    pages_deleted = db.pages_col.delete_many({"scan_id": scan_id}).deleted_count
    report_deleted = db.reports_col.delete_one({"_id": scan_id}).deleted_count
    scan_deleted = db.scans_col.delete_one({"_id": scan_id}).deleted_count

    return {"scan_id": scan_id, "deleted": bool(scan_deleted), "pages_deleted": pages_deleted, "report_deleted": report_deleted}


@router.get("/scan/{scan_id}")
def get_scan_status(scan_id: str):
    if db.scans_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    scan = db.scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")

    return scan
