#!/usr/bin/env python3
"""
Test script to verify frame saving functionality
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Initialize database before importing storage service
from db.database import init_db, close_db, get_db
init_db()

from db.storage_service import DatabaseStorageService

def test_frame_saving():
    """Test if frames are being saved correctly"""
    
    storage = DatabaseStorageService()
    db = get_db()
    
    # Test session ID
    session_id = "909e6b8e-70f5-4f06-9210-8a4d07cd5fc2"
    
    print(f"\n1. Checking session {session_id}...")
    
    # Check if session exists
    query = "SELECT * FROM calibration_sessions WHERE id = %s"
    session = db.execute_query(query, (session_id,), fetch_one=True)
    
    if session:
        print(f"   ✓ Session found: candidate_id={session['candidate_id']}, status={session['status']}")
    else:
        print(f"   ✗ Session not found!")
        return
    
    # Check current frame count
    count_query = "SELECT COUNT(*) as count FROM calibration_frames WHERE session_id = %s"
    result = db.execute_query(count_query, (session_id,), fetch_one=True)
    initial_count = result['count'] if result else 0
    print(f"\n2. Current frame count: {initial_count}")
    
    # Try to save a test frame
    print("\n3. Attempting to save a test frame...")
    
    test_frame_data = {
        'success': True,
        'gaze_point': {'x': 0.5, 'y': 0.5},
        'confidence': 0.8,
        'eye_centers': {
            'left': {'x': 0.3, 'y': 0.4},
            'right': {'x': 0.7, 'y': 0.4}
        }
    }
    
    test_target_position = {'x': 0.1, 'y': 0.1}
    test_frame_index = 999  # Use a high number to avoid conflicts
    
    success = storage.save_calibration_frame(
        session_id=session_id,
        frame_index=test_frame_index,
        frame_data=test_frame_data,
        target_position=test_target_position
    )
    
    print(f"   Save result: {'✓ Success' if success else '✗ Failed'}")
    
    # Check new frame count
    result = db.execute_query(count_query, (session_id,), fetch_one=True)
    new_count = result['count'] if result else 0
    print(f"\n4. New frame count: {new_count}")
    print(f"   Frames added: {new_count - initial_count}")
    
    # Try to retrieve the saved frame
    if new_count > initial_count:
        print("\n5. Retrieving saved frame...")
        frame_query = """
        SELECT * FROM calibration_frames 
        WHERE session_id = %s AND frame_index = %s
        """
        saved_frame = db.execute_query(frame_query, (session_id, test_frame_index), fetch_one=True)
        
        if saved_frame:
            print(f"   ✓ Frame retrieved successfully")
            print(f"   Frame ID: {saved_frame['id']}")
            print(f"   Created at: {saved_frame['created_at']}")
            print(f"   Frame data: {json.loads(saved_frame['frame_data'])}")
        else:
            print(f"   ✗ Could not retrieve frame")
    
    # Clean up test frame
    print("\n6. Cleaning up test frame...")
    cleanup_query = "DELETE FROM calibration_frames WHERE session_id = %s AND frame_index = %s"
    rows_deleted = db.execute_update(cleanup_query, (session_id, test_frame_index))
    print(f"   Deleted {rows_deleted} test frames")

if __name__ == "__main__":
    try:
        test_frame_saving()
    finally:
        close_db()