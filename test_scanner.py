#!/usr/bin/env python3
"""
Simple test script for the Adobe Analytics Website Scanner
"""
import requests
import time
import json

BASE_URL = "http://localhost:8001"

def test_scanner():
    print("🚀 Testing Adobe Analytics Website Scanner")
    
    # Test 1: Start a scan
    print("\n1. Starting scan...")
    response = requests.post(f"{BASE_URL}/scan", params={
        "start_url": "https://www.homedepot.ca",
        "max_pages": 3,
        "max_clicks_per_page": 2
    })
    
    if response.status_code != 200:
        print(f"❌ Failed to start scan: {response.text}")
        return
    
    scan_data = response.json()
    scan_id = scan_data["scan_id"]
    print(f"✅ Scan started with ID: {scan_id}")
    
    # Test 2: Check scan status
    print("\n2. Monitoring scan progress...")
    while True:
        response = requests.get(f"{BASE_URL}/scan/{scan_id}")
        if response.status_code != 200:
            print(f"❌ Failed to get scan status: {response.text}")
            return
        
        status_data = response.json()
        status = status_data["status"]
        pages_scanned = status_data.get("pages_scanned", 0)
        total_pages = status_data.get("total_pages", 0)
        
        print(f"📊 Status: {status} | Progress: {pages_scanned}/{total_pages}")
        
        if status == "completed":
            print("✅ Scan completed!")
            break
        elif status == "failed":
            print("❌ Scan failed!")
            return
        
        time.sleep(5)
    
    # Test 3: Get report data as JSON
    print("\n3. Getting report data as JSON...")
    response = requests.get(f"{BASE_URL}/report/{scan_id}/data")
    
    if response.status_code != 200:
        print(f"❌ Failed to get report data: {response.text}")
        return
    
    report_data = response.json()
    print(f"✅ Report data retrieved: {report_data['total_rows']} rows")
    print(f"📊 Generated at: {time.ctime(report_data['generated_at'])}")
    
    # Test 4: Download Excel report
    print("\n4. Downloading Excel report...")
    response = requests.get(f"{BASE_URL}/report/{scan_id}")
    
    if response.status_code != 200:
        print(f"❌ Failed to download report: {response.text}")
        return
    
    filename = f"test_report_{scan_id}.xlsx"
    with open(filename, "wb") as f:
        f.write(response.content)
    
    print(f"✅ Excel report downloaded: {filename}")
    print(f"📄 File size: {len(response.content)} bytes")
    
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    try:
        test_scanner()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")