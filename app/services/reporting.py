import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs

from app import db


logger = logging.getLogger(__name__)


def extract_adobe_analytics_info(beacon_url: str) -> Dict[str, Any]:
    result = {
        'beacon_type': 'unknown',
        'report_suite': None,
        'tracking_server': None,
        'version': None,
        'parameters': {}
    }

    try:
        parsed = urlparse(beacon_url)

        if '/b/ss/' in beacon_url:
            result['beacon_type'] = 'legacy'
            parts = parsed.path.split('/')
            if len(parts) > 3:
                result['report_suite'] = parts[3].split(',')[0]
        elif 'interact' in beacon_url:
            result['beacon_type'] = 'aam'
            params = parse_qs(parsed.query)
            if 'configId' in params:
                result['config_id'] = params['configId'][0]
            if 'requestId' in params:
                result['request_id'] = params['requestId'][0]

        result['tracking_server'] = parsed.netloc

        params = parse_qs(parsed.query)
        result['parameters'] = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

        if '/b/ss/' in beacon_url:
            path_parts = parsed.path.split('/')
            if len(path_parts) > 5 and path_parts[5].isdigit():
                result['version'] = path_parts[5]

    except Exception as e:
        logger.warning(f"Error extracting Adobe Analytics info from {beacon_url}: {str(e)}")

    return result


def generate_report_data(scan_id: str) -> List[Dict[str, Any]]:
    logger.info(f"Generating report data for scan: {scan_id}")

    scan = db.scans_col.find_one({"_id": scan_id})
    if not scan:
        logger.error(f"Scan not found: {scan_id}")
        return []

    page_docs = list(db.pages_col.find({"scan_id": scan_id}))
    if not page_docs:
        logger.warning(f"No pages found for scan: {scan_id}")
        return []

    rows = []
    scan_start_time = scan.get('started_at', time.time())
    scan_end_time = scan.get('completed_at')
    scan_duration_seconds = scan.get('duration_seconds')

    for page in page_docs:
        page_url = page.get('url', 'N/A')
        page_title = page.get('title', 'Untitled')
        has_tagging = page.get('has_tagging', False)

        rows.append({
            "Scan ID": scan_id,
            "Page URL": page_url,
            "Page Title": page_title,
            "Scan Start Time": datetime.fromtimestamp(scan_start_time).strftime('%Y-%m-%d %H:%M:%S'),
            "Scan End Time": datetime.fromtimestamp(scan_end_time).strftime('%Y-%m-%d %H:%M:%S') if scan_end_time else "",
            "Scan Duration (s)": scan_duration_seconds if scan_duration_seconds is not None else "",
            "Has Adobe Launch Tagging": "Yes" if has_tagging else "No",
            "Beacon Type": "Page Summary",
            "Beacon URL": "",
            "Request Method": "",
            "Request Payload": "",
            "Adobe Analytics Detected": "Yes" if has_tagging else "No",
            "Beacon Count": len(page.get('load_beacons', [])),
            "Click Events Scanned": len(page.get('click_events', [])),
            "Page Scan Duration (s)": round(page.get('scan_duration', 0), 2)
        })

        for beacon in page.get('load_beacons', []):
            beacon_url = beacon.get('request_url', '')
            method = beacon.get('method', 'GET')
            payload = beacon.get('payload', '')
            response_payload = beacon.get('response_payload', '')

            aa_info = extract_adobe_analytics_info(beacon_url)

            rows.append({
                "Scan ID": scan_id,
                "Page URL": page_url,
                "Page Title": page_title,
                "Scan Start Time": datetime.fromtimestamp(scan_start_time).strftime('%Y-%m-%d %H:%M:%S'),
                "Scan End Time": datetime.fromtimestamp(scan_end_time).strftime('%Y-%m-%d %H:%M:%S') if scan_end_time else "",
                "Scan Duration (s)": scan_duration_seconds if scan_duration_seconds is not None else "",
                "Has Adobe Launch Tagging": "Yes" if has_tagging else "No",
                "Beacon Type": f"Page Load - {aa_info['beacon_type'].upper()}",
                "Beacon URL": beacon_url,
                "Request Method": method,
                "Request Payload": json.dumps(payload, indent=2) if isinstance(payload, dict) else str(payload),
                "Response Payload": json.dumps(response_payload, indent=2) if isinstance(response_payload, (dict, list)) else str(response_payload),
                "Adobe Analytics Detected": "Yes" if aa_info['beacon_type'] in ['legacy', 'aam'] else "No",
                "Report Suite ID": aa_info.get('report_suite', 'N/A'),
                "Tracking Server": aa_info.get('tracking_server', 'N/A'),
                "Config ID": aa_info.get('config_id', 'N/A'),
                "Request ID": aa_info.get('request_id', 'N/A'),
                "Version": aa_info.get('version', 'N/A')
            })

        for click in page.get('click_events', []):
            element = click.get('element', 'Unknown')
            element_type = click.get('element_type', 'link')

            if not click.get('beacons'):
                rows.append({
                    "Scan ID": scan_id,
                    "Page URL": page_url,
                    "Page Title": page_title,
                    "Scan Start Time": datetime.fromtimestamp(scan_start_time).strftime('%Y-%m-%d %H:%M:%S'),
                    "Scan End Time": datetime.fromtimestamp(scan_end_time).strftime('%Y-%m-%d %H:%M:%S') if scan_end_time else "",
                    "Scan Duration (s)": scan_duration_seconds if scan_duration_seconds is not None else "",
                    "Has Adobe Launch Tagging": "Yes" if has_tagging else "No",
                    "Beacon Type": f"{element_type.capitalize()} Click - No Beacon",
                    "Clicked Element": element,
                    "Beacon URL": "",
                    "Request Method": "",
                    "Request Payload": "No Adobe Analytics beacon detected for this interaction",
                    "Adobe Analytics Detected": "No"
                })
                continue

            for beacon in click.get('beacons', []):
                beacon_url = beacon.get('request_url', '')
                method = beacon.get('method', 'GET')
                payload = beacon.get('payload', '')
                response_payload = beacon.get('response_payload', '')

                aa_info = extract_adobe_analytics_info(beacon_url)

                rows.append({
                    "Scan ID": scan_id,
                    "Page URL": page_url,
                    "Page Title": page_title,
                    "Scan Start Time": datetime.fromtimestamp(scan_start_time).strftime('%Y-%m-%d %H:%M:%S'),
                    "Scan End Time": datetime.fromtimestamp(scan_end_time).strftime('%Y-%m-%d %H:%M:%S') if scan_end_time else "",
                    "Scan Duration (s)": scan_duration_seconds if scan_duration_seconds is not None else "",
                    "Has Adobe Launch Tagging": "Yes" if has_tagging else "No",
                    "Beacon Type": f"{element_type.capitalize()} Click - {aa_info['beacon_type'].upper()}",
                    "Clicked Element": element,
                    "Beacon URL": beacon_url,
                    "Request Method": method,
                    "Request Payload": json.dumps(payload, indent=2) if isinstance(payload, dict) else str(payload),
                    "Response Payload": json.dumps(response_payload, indent=2) if isinstance(response_payload, (dict, list)) else str(response_payload),
                    "Adobe Analytics Detected": "Yes" if aa_info['beacon_type'] in ['legacy', 'aam'] else "No",
                    "Report Suite ID": aa_info.get('report_suite', 'N/A'),
                    "Tracking Server": aa_info.get('tracking_server', 'N/A'),
                    "Config ID": aa_info.get('config_id', 'N/A'),
                    "Request ID": aa_info.get('request_id', 'N/A'),
                    "Version": aa_info.get('version', 'N/A'),
                })

    logger.info(f"Generated {len(rows)} rows of report data for scan: {scan_id}")
    return rows


def store_report_in_mongo(scan_id: str):
    report_data = generate_report_data(scan_id)

    report_doc = {
        "_id": scan_id,
        "scan_id": scan_id,
        "generated_at": time.time(),
        "total_rows": len(report_data),
        "data": report_data
    }

    db.reports_col.replace_one({"_id": scan_id}, report_doc, upsert=True)
    return report_doc
