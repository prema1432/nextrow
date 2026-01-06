import asyncio
import json
import time
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app import db
from app.services.reporting import store_report_in_mongo


logger = logging.getLogger(__name__)


def run_scan(scan_id: str, start_url: str, max_pages: int, max_clicks_per_page: int):
    def _is_adobe_beacon_url(req_url: str) -> bool:
        if not req_url:
            return False
        return ("b/ss/" in req_url) or ("interact" in req_url)

    def _payload_from_playwright_request(request) -> Any:
        try:
            post_data = request.post_data
        except Exception:
            post_data = None

        if post_data:
            try:
                return request.post_data_json
            except Exception:
                return post_data

        parsed = urlparse(request.url)
        if not parsed.query:
            return ""
        params = parse_qs(parsed.query)
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    def _beacon_key(req_url: str, method: str, payload: Any) -> str:
        try:
            payload_s = json.dumps(payload, sort_keys=True, default=str)
        except Exception:
            payload_s = str(payload)
        return f"{method.upper()}|{req_url}|{payload_s}"

    async def _run_scan_playwright() -> None:
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc

        collector_state: Dict[str, Any] = {"active": None}

        def on_request(request) -> None:
            bucket = collector_state.get("active")
            if bucket is None:
                return

            req_url = request.url
            if not _is_adobe_beacon_url(req_url):
                return

            method = request.method or "GET"
            payload = _payload_from_playwright_request(request)
            key = _beacon_key(req_url, method, payload)
            if key in bucket["seen"]:
                return
            bucket["seen"].add(key)

            bucket["beacons"].append({
                "request_url": req_url,
                "method": method,
                "payload": payload,
                "response_payload": "",
            })
            bucket["index_by_key"][key] = len(bucket["beacons"]) - 1

        def on_response(response) -> None:
            bucket = collector_state.get("active")
            if bucket is None:
                return

            resp_url = response.url
            if not _is_adobe_beacon_url(resp_url):
                return

            try:
                req = response.request
                method = req.method or "GET"
                payload = _payload_from_playwright_request(req)
            except Exception:
                method = "GET"
                payload = ""

            key = _beacon_key(resp_url, method, payload)
            bucket["responses_by_key"][key] = response

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (compatible; AdobeAnalyticsScanner/1.0)",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(30000)

            page.on("request", on_request)
            page.on("response", on_response)

            visited: set[str] = set()
            queue: List[str] = [start_url]

            while queue and len(visited) < max_pages:
                url = queue.pop(0)
                if not url or url in visited:
                    continue
                if not url.startswith(("http://", "https://")):
                    continue
                if urlparse(url).netloc != base_domain:
                    continue

                page_start = time.time()
                visited.add(url)

                load_bucket = {
                    "beacons": [],
                    "seen": set(),
                    "index_by_key": {},
                    "responses_by_key": {},
                }
                collector_state["active"] = load_bucket

                title = ""
                content = ""
                try:
                    await page.goto(url, wait_until="networkidle")
                    await page.wait_for_timeout(1000)
                    title = await page.title()
                    content = await page.content()
                except PlaywrightTimeoutError:
                    try:
                        title = await page.title()
                        content = await page.content()
                    except Exception:
                        title = ""
                        content = ""
                except Exception:
                    collector_state["active"] = None
                    continue

                collector_state["active"] = None

                for key, resp in list(load_bucket["responses_by_key"].items()):
                    idx = load_bucket["index_by_key"].get(key)
                    if idx is None:
                        continue
                    try:
                        body = await resp.text()
                        if isinstance(body, str) and len(body) > 10000:
                            body = body[:10000]
                        load_bucket["beacons"][idx]["response_payload"] = body
                    except Exception:
                        continue

                has_tagging = "assets.adobedtm.com" in (content or "")

                internal_links: List[str] = []
                try:
                    hrefs = await page.eval_on_selector_all(
                        "a[href]",
                        "elements => elements.map(el => el.href)",
                    )
                except Exception:
                    hrefs = []

                for href in hrefs or []:
                    if not href or not isinstance(href, str):
                        continue
                    if not href.startswith(("http://", "https://")):
                        continue
                    if urlparse(href).netloc != base_domain:
                        continue
                    if href in visited or href in queue:
                        continue
                    internal_links.append(href)
                    queue.append(href)

                click_events: List[Dict[str, Any]] = []
                for link in internal_links[: max(0, int(max_clicks_per_page))]:
                    click_bucket = {
                        "beacons": [],
                        "seen": set(),
                        "index_by_key": {},
                        "responses_by_key": {},
                    }
                    collector_state["active"] = click_bucket

                    try:
                        await page.goto(link, wait_until="networkidle")
                        await page.wait_for_timeout(750)
                    except Exception:
                        pass

                    collector_state["active"] = None

                    for key, resp in list(click_bucket["responses_by_key"].items()):
                        idx = click_bucket["index_by_key"].get(key)
                        if idx is None:
                            continue
                        try:
                            body = await resp.text()
                            if isinstance(body, str) and len(body) > 10000:
                                body = body[:10000]
                            click_bucket["beacons"][idx]["response_payload"] = body
                        except Exception:
                            continue

                    click_events.append({
                        "element": link[:100],
                        "element_type": "link",
                        "beacons": click_bucket["beacons"],
                    })

                    try:
                        await page.goto(url, wait_until="domcontentloaded")
                    except Exception:
                        pass

                db.pages_col.insert_one({
                    "scan_id": scan_id,
                    "url": url,
                    "title": title,
                    "has_tagging": has_tagging,
                    "load_beacons": load_bucket["beacons"],
                    "click_events": click_events,
                    "scan_duration": time.time() - page_start,
                })

                db.scans_col.update_one({"_id": scan_id}, {"$inc": {"pages_scanned": 1}})

            await context.close()
            await browser.close()

    started_at = time.time()
    db.scans_col.update_one(
        {"_id": scan_id},
        {"$set": {"status": "running", "total_pages": int(max_pages), "started_at": started_at, "pages_scanned": 0}},
    )

    try:
        asyncio.run(_run_scan_playwright())
        store_report_in_mongo(scan_id)

        completed_at = time.time()
        db.scans_col.update_one(
            {"_id": scan_id},
            {"$set": {"status": "completed", "completed_at": completed_at, "duration_seconds": round(completed_at - started_at, 2)}},
        )
    except Exception as e:
        completed_at = time.time()
        db.scans_col.update_one(
            {"_id": scan_id},
            {"$set": {"status": "failed", "error": str(e), "completed_at": completed_at, "duration_seconds": round(completed_at - started_at, 2)}},
        )
