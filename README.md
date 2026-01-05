# Adobe Analytics Website Scanner

A FastAPI application that scans websites for Adobe Analytics implementation, detecting Adobe Launch/DTM tagging and capturing network beacons on page load and user interactions.

## Features

- **Adobe Launch Detection**: Identifies `assets.adobedtm.com` script tags
- **Beacon Capture**: Monitors network requests for Adobe Analytics beacons (`b/ss/` or `interact`)
- **Interactive Testing**: Clicks links and buttons to capture interaction-triggered beacons
- **Excel Reports**: Generates downloadable reports with all findings
- **Background Processing**: Scans run asynchronously with status tracking

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install-deps
playwright install chromium
```

2. Start the server:
```bash
uvicorn main:app --reload
```

3. Access the API at `http://localhost:8000`

### API Usage

**Start a scan:**
```bash
curl -X POST "http://localhost:8001/scan?start_url=https://www.homedepot.ca&max_pages=5&max_clicks_per_page=3"
```

**Check scan status:**
```bash
curl "http://localhost:8001/scan/{scan_id}"
```

**Get report data as JSON:**
```bash
curl "http://localhost:8001/report/{scan_id}/data"
```

**Download Excel report:**
```bash
curl "http://localhost:8001/report/{scan_id}" -o report.xlsx
```

## Deployment on Render.com (Free Tier)

1. **Create Web Service**: Connect your GitHub repository
2. **Build Command**: 
   ```
   pip install -r requirements.txt && playwright install-deps && playwright install chromium
   ```
3. **Start Command**: 
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. **Environment Variables**: 
   - `MONGO_URI`: Your MongoDB Atlas connection string

## MongoDB Atlas Setup

The application uses the provided connection string:
```
mongodb+srv://nextrowuser:nextrow@nextrow.dgppima.mongodb.net/?appName=nextrow
```

Collections created:
- `adobe_scanner.scans`: Scan metadata and status
- `adobe_scanner.pages`: Page-level scan results

## Report Structure

The Excel report includes:
- **ScanID**: Unique identifier for the scan
- **URL**: Page URL scanned
- **Page Title**: HTML title of the page
- **Has Adobe Launch Tagging**: Boolean indicating presence of Adobe Launch
- **Beacon Type**: "Page Load" or "Link/Button Click"
- **Clicked Element**: Description of clicked element (for interaction beacons)
- **Request URL**: Full beacon URL
- **Method**: HTTP method (GET/POST)
- **Payload**: Request payload or query parameters

## Configuration

- `max_pages`: Maximum pages to crawl (default: 10)
- `max_clicks_per_page`: Maximum clickable elements to test per page (default: 5)
- Timeout settings: 90s for page load, 10s for clicks, 5s for beacon capture

## Architecture

- **FastAPI**: REST API framework
- **Playwright**: Headless browser automation for accurate beacon detection
- **MongoDB Atlas**: Cloud database for scan data storage
- **Pandas + OpenPyXL**: Excel report generation
- **BeautifulSoup + Requests**: Lightweight URL collection