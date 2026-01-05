import uuid
import time
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from playwright.sync_api import sync_playwright
from pymongo import MongoClient

app = FastAPI(title="Adobe Analytics Website Scanner")

# === Replace with your MongoDB Atlas connection string ===
MONGO_URI = "mongodb+srv://nextrowuser:nextrow@nextrow.dgppima.mongodb.net/?appName=nextrow"
client = MongoClient(MONGO_URI)
db = client["adobe_scanner"]
scans_col = db["scans"]
pages_col = db["pages"]
reports_col = db["reports"]


def collect_urls(start_url: str, max_pages: int = 10) -> list[str]:
    """Lightweight crawler to collect up to max_pages internal URLs."""
    parsed = urlparse(start_url)
    domain = parsed.netloc
    visited = set()
    queue = [start_url]
    urls = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ScannerBot/1.0)"}

    while queue and len(urls) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        urls.append(url)

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                abs_url = urljoin(url, a["href"].split("#")[0])  # remove fragments
                if urlparse(abs_url).netloc == domain and abs_url not in visited:
                    queue.append(abs_url)
        except Exception:
            continue

    return urls[:max_pages]


def generate_report_data(scan_id: str) -> list[dict]:
    """Generate report data structure from scan results."""
    scan = scans_col.find_one({"_id": scan_id})
    if not scan:
        return []
    
    page_docs = list(pages_col.find({"scan_id": scan_id}))
    rows = []
    
    for page in page_docs:
        # Page-level row
        rows.append({
            "ScanID": scan_id,
            "URL": page["url"],
            "Page Title": page["title"],
            "Has Adobe Launch Tagging": page["has_tagging"],
            "Beacon Type": "Page Load",
            "Clicked Element": "",
            "Request URL": "",
            "Method": "",
            "Payload": ""
        })

        # Load beacons
        for b in page["load_beacons"]:
            rows.append({
                "ScanID": scan_id,
                "URL": page["url"],
                "Page Title": page["title"],
                "Has Adobe Launch Tagging": page["has_tagging"],
                "Beacon Type": "Page Load",
                "Clicked Element": "",
                "Request URL": b["request_url"],
                "Method": b["method"],
                "Payload": b["payload"]
            })

        # Click beacons
        for click in page["click_events"]:
            element = click["element"]
            for b in click["beacons"]:
                rows.append({
                    "ScanID": scan_id,
                    "URL": page["url"],
                    "Page Title": page["title"],
                    "Has Adobe Launch Tagging": page["has_tagging"],
                    "Beacon Type": "Link/Button Click",
                    "Clicked Element": element,
                    "Request URL": b["request_url"],
                    "Method": b["method"],
                    "Payload": b["payload"]
                })
            if not click["beacons"]:
                rows.append({
                    "ScanID": scan_id,
                    "URL": page["url"],
                    "Page Title": page["title"],
                    "Has Adobe Launch Tagging": page["has_tagging"],
                    "Beacon Type": "Link/Button Click",
                    "Clicked Element": element,
                    "Request URL": "",
                    "Method": "",
                    "Payload": "No beacon detected"
                })
    
    return rows


def store_report_in_mongo(scan_id: str):
    """Generate and store report data in MongoDB."""
    report_data = generate_report_data(scan_id)
    
    # Store the report data
    report_doc = {
        "_id": scan_id,
        "scan_id": scan_id,
        "generated_at": time.time(),
        "total_rows": len(report_data),
        "data": report_data
    }
    
    # Use upsert to replace existing report if it exists
    reports_col.replace_one({"_id": scan_id}, report_doc, upsert=True)
    return report_doc


def run_scan(scan_id: str, start_url: str, max_pages: int, max_clicks_per_page: int):
    urls = collect_urls(start_url, max_pages)

    scans_col.update_one({"_id": scan_id}, {"$set": {"status": "running", "total_pages": len(urls), "started_at": time.time()}})

    beacons = []  # shared list for request listener

    def handle_request(request):
        url = request.url
        if "b/ss/" in url or "interact" in url:
            payload = request.post_data()
            if not payload and request.method == "GET":
                payload = urlparse(url).query
            beacons.append({
                "request_url": url,
                "method": request.method,
                "payload": str(payload) if payload else "None"
            })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.on("request", handle_request)
        page = context.new_page()

        for idx, url in enumerate(urls):
            try:
                beacons.clear()
                page.goto(url, wait_until="networkidle", timeout=90000)
                title = page.title()
                content = page.content()
                has_tagging = "assets.adobedtm.com" in content

                load_beacons = beacons[:]

                # === Click testing ===
                click_events = []
                clickable_locators = page.locator("a[href], button").all()[:max_clicks_per_page]
                for locator in clickable_locators:
                    try:
                        element_desc = (locator.text_content(strip=True) or
                                        locator.get_attribute("href") or
                                        "unknown element")[:100]

                        pre_url = page.url
                        beacons.clear()

                        locator.click(timeout=10000, force=True)
                        page.wait_for_timeout(5000)  # wait for async beacons

                        click_beacons = beacons[:]

                        if page.url != pre_url:  # navigation happened
                            page.go_back(wait_until="networkidle")

                        click_events.append({
                            "element": element_desc,
                            "beacons": click_beacons
                        })
                    except Exception:
                        continue

                # Save page data
                pages_col.insert_one({
                    "scan_id": scan_id,
                    "url": url,
                    "title": title,
                    "has_tagging": has_tagging,
                    "load_beacons": load_beacons,
                    "click_events": click_events
                })

                scans_col.update_one({"_id": scan_id}, {"$inc": {"pages_scanned": 1}})

            except Exception as e:
                print(f"Error scanning {url}: {e}")
                continue

        browser.close()

    # Generate and store report data in MongoDB
    store_report_in_mongo(scan_id)
    
    scans_col.update_one({"_id": scan_id}, {"$set": {"status": "completed", "completed_at": time.time()}})


@app.post("/scan")
def start_scan(start_url: str, max_pages: int = 10, max_clicks_per_page: int = 5, background_tasks: BackgroundTasks = None):
    if not start_url.startswith(("http://", "https://")):
        raise HTTPException(400, "Invalid URL")
    scan_id = str(uuid.uuid4())
    scans_col.insert_one({
        "_id": scan_id,
        "start_url": start_url,
        "status": "queued",
        "pages_scanned": 0,
        "total_pages": 0
    })
    background_tasks.add_task(run_scan, scan_id, start_url, max_pages, max_clicks_per_page)
    return {"scan_id": scan_id, "message": "Scan started in background"}


@app.get("/scan/{scan_id}")
def get_scan_status(scan_id: str):
    scan = scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")
    return scan


@app.get("/report/{scan_id}/data")
def get_report_data(scan_id: str):
    """Get report data as JSON from MongoDB."""
    scan = scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan["status"] != "completed":
        raise HTTPException(400, "Scan not completed yet")
    
    report = reports_col.find_one({"_id": scan_id})
    if not report:
        raise HTTPException(404, "Report not found")
    
    return {
        "scan_id": scan_id,
        "generated_at": report["generated_at"],
        "total_rows": report["total_rows"],
        "data": report["data"]
    }


@app.get("/report/{scan_id}")
def download_report(scan_id: str):
    """Generate and download Excel report from stored MongoDB data."""
    scan = scans_col.find_one({"_id": scan_id})
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan["status"] != "completed":
        raise HTTPException(400, "Scan not completed yet")

    # Get report data from MongoDB
    report = reports_col.find_one({"_id": scan_id})
    if not report:
        raise HTTPException(404, "Report not found")

    # Generate Excel file from stored data
    df = pd.DataFrame(report["data"])
    filename = f"/tmp/report_{scan_id}.xlsx"
    df.to_excel(filename, index=False)

    return FileResponse(
        filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"adobe_analytics_report_{scan_id}.xlsx"
    )