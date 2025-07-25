#!/usr/bin/env python3
"""
Test the complete calibration flow with proper data
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_calibration_flow():
    candidate_id = "test_clean_007"
    
    print("1. Creating session...")
    resp = requests.post(f"{BASE_URL}/api/calibration/session/create", 
                        json={"candidate_id": candidate_id})
    if resp.status_code != 200:
        print(f"Failed to create session: {resp.text}")
        return
    
    session_data = resp.json()
    session_id = session_data['session_id']
    print(f"   Session created: {session_id}")
    
    print("\n2. Saving screen info...")
    resp = requests.post(f"{BASE_URL}/api/screen/info",
                        json={
                            "candidate_id": candidate_id,
                            "screen_width_px": 1920,
                            "screen_height_px": 1080,
                            "dpi": 96
                        })
    if resp.status_code != 200:
        print(f"Failed to save screen info: {resp.text}")
        return
    print("   Screen info saved")
    
    print("\n3. Starting calibration...")
    resp = requests.post(f"{BASE_URL}/api/calibration/start",
                        json={
                            "session_id": session_id,
                            "candidate_id": candidate_id
                        })
    if resp.status_code != 200:
        print(f"Failed to start calibration: {resp.text}")
        return
    print("   Calibration started")
    
    print("\n4. Sending calibration frames...")
    # 4 targets, 30 frames each
    targets = [
        {"x": 0.1, "y": 0.1},  # Top-left
        {"x": 0.9, "y": 0.1},  # Top-right
        {"x": 0.1, "y": 0.9},  # Bottom-left
        {"x": 0.9, "y": 0.9}   # Bottom-right
    ]
    
    frame_index = 0
    for target_index, target in enumerate(targets):
        print(f"   Target {target_index + 1}/4 at ({target['x']}, {target['y']})")
        for i in range(30):
            resp = requests.post(f"{BASE_URL}/api/calibration/frame",
                               json={
                                   "session_id": session_id,
                                   "candidate_id": candidate_id,
                                   "frame_data": "mock_image_data",
                                   "frame_index": frame_index,
                                   "target_position": target,
                                   "target_index": target_index
                               })
            if resp.status_code != 200:
                print(f"     Failed to send frame {frame_index}: {resp.text}")
                return
            frame_index += 1
        print(f"     Sent 30 frames for target {target_index + 1}")
    
    print(f"\n   Total frames sent: {frame_index}")
    
    print("\n5. Completing calibration...")
    resp = requests.post(f"{BASE_URL}/api/calibration/complete",
                        json={
                            "session_id": session_id,
                            "candidate_id": candidate_id
                        })
    
    if resp.status_code != 200:
        print(f"   Failed to complete calibration: {resp.status_code}")
        print(f"   Error: {resp.text}")
        
        # Get debug info
        print("\n6. Getting debug info...")
        debug_resp = requests.get(f"{BASE_URL}/api/debug/session/{session_id}")
        if debug_resp.status_code == 200:
            debug_data = debug_resp.json()
            print(f"   Frames in DB: {debug_data['frames']['total_count']}")
            print(f"   Frame distribution: {debug_data['frames']['distribution']}")
    else:
        print("   ✓ Calibration completed successfully!")
        print(f"   Response: {json.dumps(resp.json(), indent=2)}")

if __name__ == "__main__":
    test_calibration_flow()