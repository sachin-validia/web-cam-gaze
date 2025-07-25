#!/usr/bin/env python3
"""
Simple debug script to trace the calibration data flow
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from db.storage_service import DatabaseStorageService
from db.database import get_db

class CalibrationDebugger:
    """Debug tool for calibration data flow"""
    
    def __init__(self):
        self.storage = DatabaseStorageService()
        self.db = get_db()
        
    def print_section(self, title: str):
        """Print a formatted section header"""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
    
    def check_database_tables(self):
        """Check if all required tables exist"""
        self.print_section("DATABASE TABLES CHECK")
        
        tables = [
            'calibration_sessions',
            'screen_info',
            'calibration_frames',
            'calibration_data',
            'calibration_audit_log'
        ]
        
        for table in tables:
            try:
                query = f"SELECT COUNT(*) as count FROM {table}"
                result = self.db.execute_query(query, fetch_one=True)
                count = result['count'] if result else 0
                print(f"✓ {table}: {count} records")
            except Exception as e:
                print(f"✗ {table}: {str(e)}")
    
    def trace_session_flow(self, session_id: str = None, candidate_id: str = None):
        """Trace the complete flow for a session"""
        self.print_section("SESSION FLOW TRACE")
        
        # Get the most recent session if not specified
        if not session_id:
            query = """
            SELECT id, candidate_id, status, created_at, error_message
            FROM calibration_sessions 
            ORDER BY created_at DESC 
            LIMIT 5
            """
            sessions = self.db.execute_query(query)
            if sessions:
                print("Recent sessions:")
                for i, session in enumerate(sessions):
                    print(f"\n{i+1}. Session ID: {session['id']}")
                    print(f"   Candidate ID: {session['candidate_id']}")
                    print(f"   Status: {session['status']}")
                    print(f"   Created: {session['created_at']}")
                    if session['error_message']:
                        print(f"   Error: {session['error_message']}")
                
                # Use the most recent one
                session = sessions[0]
                session_id = session['id']
                candidate_id = session['candidate_id']
                print(f"\nUsing most recent session: {session_id}")
            else:
                print("No sessions found")
                return
        
        # Check screen info
        self.print_section("SCREEN INFO CHECK")
        screen_info = self.storage.get_screen_info(candidate_id)
        if screen_info:
            print("✓ Screen info exists")
            print(json.dumps(screen_info, indent=2))
        else:
            print("✗ No screen info found")
        
        # Check calibration frames
        self.print_section("CALIBRATION FRAMES CHECK")
        frames = self.storage.get_calibration_frames(session_id)
        print(f"Debug: Checking frames for session_id: {session_id}")
        
        if frames:
            print(f"✓ Found {len(frames)} frames")
            
            # Analyze frame distribution
            target_counts = {}
            success_count = 0
            for frame in frames:
                target_key = f"{frame['target_position']['x']},{frame['target_position']['y']}"
                target_counts[target_key] = target_counts.get(target_key, 0) + 1
                if frame['frame_data'].get('success'):
                    success_count += 1
            
            print(f"\nFrame Statistics:")
            print(f"  - Successful frames: {success_count}/{len(frames)}")
            print(f"  - Frames per target:")
            for target, count in target_counts.items():
                print(f"    - Target {target}: {count} frames")
            
            # Show a sample frame
            if frames:
                print("\nSample frame data:")
                sample = frames[0]
                print(f"  - Frame index: {sample['frame_index']}")
                print(f"  - Target position: {sample['target_position']}")
                print(f"  - Success: {sample['frame_data'].get('success', False)}")
                if 'gaze_point' in sample['frame_data']:
                    print(f"  - Gaze point: {sample['frame_data']['gaze_point']}")
        else:
            print("✗ No calibration frames found")
            
            # Debug: Check raw database
            print("\nDebug: Checking raw database for frames...")
            query = "SELECT COUNT(*) as count FROM calibration_frames WHERE session_id = %s"
            result = self.db.execute_query(query, (session_id,), fetch_one=True)
            if result:
                print(f"Raw count in DB: {result['count']}")
        
        # Check calibration data
        self.print_section("CALIBRATION DATA CHECK")
        cal_exists = self.storage.check_calibration_exists(candidate_id)
        if cal_exists:
            print("✓ Calibration data exists")
            
            # Get calibration files
            files = self.storage.get_calibration_files(candidate_id)
            if files:
                print("Files generated:")
                for filename in files.keys():
                    print(f"  - {filename}")
        else:
            print("✗ No calibration data found")
    
    def check_complete_endpoint_requirements(self):
        """Check specific requirements for the /complete endpoint"""
        self.print_section("COMPLETE ENDPOINT REQUIREMENTS")
        
        print("The /api/calibration/complete endpoint requires:")
        print("1. Valid session_id")
        print("2. Valid candidate_id")
        print("3. Calibration frames in database")
        print("4. Screen info saved for candidate")
        print("5. GazeService initialized (or mock data)")
        print("\nChecking most recent session...")
        
        # Get most recent session
        query = """
        SELECT id, candidate_id, status
        FROM calibration_sessions 
        WHERE status != 'completed'
        ORDER BY created_at DESC 
        LIMIT 1
        """
        session = self.db.execute_query(query, fetch_one=True)
        
        if session:
            session_id = session['id']
            candidate_id = session['candidate_id']
            
            print(f"\nSession: {session_id}")
            print(f"Candidate: {candidate_id}")
            
            # Check each requirement
            print("\nRequirement checks:")
            
            # 1. Session exists
            print("1. Session exists: ✓")
            
            # 2. Screen info
            screen_info = self.storage.get_screen_info(candidate_id)
            if screen_info:
                print("2. Screen info exists: ✓")
            else:
                print("2. Screen info exists: ✗ (This will cause 400 error)")
            
            # 3. Frames
            frames = self.storage.get_calibration_frames(session_id)
            if frames and len(frames) > 0:
                print(f"3. Calibration frames: ✓ ({len(frames)} frames)")
            else:
                print("3. Calibration frames: ✗ (This will cause 400 error)")
            
            # 4. Check if GazeService issue
            print("4. GazeService: Check backend logs for initialization errors")

def main():
    """Main debug function"""
    debugger = CalibrationDebugger()
    
    # Check database tables
    debugger.check_database_tables()
    
    # Trace session flow
    debugger.trace_session_flow()
    
    # Check complete endpoint requirements
    debugger.check_complete_endpoint_requirements()
    
    print("\n" + "="*60)
    print("DEBUGGING SUMMARY")
    print("="*60)
    print("\nIf you're getting a 400 error on /api/calibration/complete, check:")
    print("1. Are calibration frames being saved to the database?")
    print("2. Is screen info being saved?")
    print("3. Check backend logs for any errors during frame processing")
    print("4. Verify the session_id and candidate_id match between calls")

if __name__ == "__main__":
    main()