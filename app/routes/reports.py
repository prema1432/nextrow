import io

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app import db


router = APIRouter()


@router.get("/report/{scan_id}/data")
def get_report_data(scan_id: str):
    if db.scans_col is None or db.reports_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    scan = db.scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan["status"] != "completed":
        raise HTTPException(400, "Scan not completed yet")

    report = db.reports_col.find_one({"_id": scan_id})
    if not report:
        raise HTTPException(404, "Report not found")

    return {
        "scan_id": scan_id,
        "generated_at": report["generated_at"],
        "total_rows": report["total_rows"],
        "data": report["data"],
    }


@router.get("/report/{scan_id}")
def download_report(scan_id: str):
    if db.scans_col is None or db.reports_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    scan = db.scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan["status"] != "completed":
        raise HTTPException(400, "Scan not completed yet")

    report = db.reports_col.find_one({"_id": scan_id})
    if not report:
        raise HTTPException(404, "Report not found")

    df = pd.DataFrame(report["data"])
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    headers = {"Content-Disposition": f"attachment; filename=adobe_analytics_report_{scan_id}.xlsx"}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/report/{scan_id}/simple")
def download_simple_report(scan_id: str):
    if db.scans_col is None or db.reports_col is None:
        raise HTTPException(status_code=503, detail="Database not connected. Set MONGO_URI and restart the server.")

    scan = db.scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan["status"] != "completed":
        raise HTTPException(400, "Scan not completed yet")

    report = db.reports_col.find_one({"_id": scan_id})
    if not report:
        raise HTTPException(404, "Report not found")

    df = pd.DataFrame(report["data"])
    keep_cols = [
        "Scan ID",
        "Page URL",
        "Page Title",
        "Beacon URL",
        "Request Method",
        "Request Payload",
    ]
    if "Response Payload" in df.columns:
        keep_cols.append("Response Payload")

    existing = [c for c in keep_cols if c in df.columns]
    df = df[existing]
    if "Beacon URL" in df.columns:
        df = df[df["Beacon URL"].astype(str).str.len() > 0]

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    headers = {"Content-Disposition": f"attachment; filename=adobe_analytics_simple_report_{scan_id}.xlsx"}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
