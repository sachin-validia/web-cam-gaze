#!/usr/bin/env python3
"""
Live monitoring of calibration process
"""
import time
from simple_db_monitor import get_simple_db
from datetime import datetime, timedelta

def monitor_calibration(candidate_id='test_candidate_002', interval=2):
    db = get_simple_db()
    print(f"🔍 Monitoring calibration for: {candidate_id}")
    print("Press Ctrl+C to stop\n")
    
    last_frame_count = {}
    
    try:
        while True:
            # Get all recent sessions
            sessions = db.execute_query(
                """SELECT id, status, created_at 
                   FROM calibration_sessions 
                   WHERE candidate_id = %s 
                   AND created_at >= %s
                   ORDER BY created_at DESC""",
                (candidate_id, datetime.now() - timedelta(hours=1))
            )
            
            print(f"\n{'='*60}")
            print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"Sessions found: {len(sessions)}")
            
            for session in sessions[:2]:  # Show latest 2 sessions
                session_id = session['id']
                
                # Get frame count
                frame_count = db.execute_query(
                    "SELECT COUNT(*) as count FROM calibration_frames WHERE session_id = %s",
                    (session_id,),
                    fetch_one=True
                )['count']
                
                # Check if frames increased
                prev_count = last_frame_count.get(session_id, 0)
                diff = frame_count - prev_count
                last_frame_count[session_id] = frame_count
                
                status_icon = '🟢' if session['status'] == 'in_progress' else '🔴'
                print(f"\n{status_icon} Session: {session_id[:12]}...")
                print(f"   Status: {session['status']}")
                print(f"   Created: {session['created_at'].strftime('%H:%M:%S')}")
                print(f"   Frames: {frame_count}", end='')
                
                if diff > 0:
                    print(f" (+{diff} NEW!)")
                    
                    # Show latest frames
                    latest = db.execute_query(
                        """SELECT frame_index, created_at,
                           JSON_EXTRACT(target_position, '$.x') as x,
                           JSON_EXTRACT(target_position, '$.y') as y
                           FROM calibration_frames 
                           WHERE session_id = %s 
                           ORDER BY created_at DESC 
                           LIMIT 3""",
                        (session_id,)
                    )
                    for frame in latest:
                        print(f"      Frame {frame['frame_index']} at ({frame['x']}, {frame['y']})")
                else:
                    print()
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    finally:
        db.close()

if __name__ == "__main__":
    monitor_calibration()