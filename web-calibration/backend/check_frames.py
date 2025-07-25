#!/usr/bin/env python3
"""Check calibration frames in database"""

import mysql.connector
import json
from utils.config import settings

def check_frames():
    conn = mysql.connector.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME
    )
    
    cursor = conn.cursor()
    
    # Get latest session
    cursor.execute("""
        SELECT id FROM calibration_sessions 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    latest_session = cursor.fetchone()
    if not latest_session:
        print("No sessions found")
        return
        
    session_id = latest_session[0]
    print(f"Latest session: {session_id}")
    
    # Check frame distribution
    cursor.execute("""
        SELECT 
            COUNT(*) as total_frames,
            COUNT(DISTINCT target_position) as unique_targets,
            MIN(frame_index) as min_index,
            MAX(frame_index) as max_index
        FROM calibration_frames 
        WHERE session_id = %s
    """, (session_id,))
    
    stats = cursor.fetchone()
    print(f"\nFrame statistics:")
    print(f"  Total frames: {stats[0]}")
    print(f"  Unique targets: {stats[1]}")
    print(f"  Frame index range: {stats[2]} - {stats[3]}")
    
    # Show target distribution
    cursor.execute("""
        SELECT target_position, COUNT(*) as frame_count
        FROM calibration_frames 
        WHERE session_id = %s
        GROUP BY target_position
    """, (session_id,))
    
    print(f"\nTarget distribution:")
    for row in cursor.fetchall():
        target = json.loads(row[0])
        print(f"  Position ({target['x']}, {target['y']}): {row[1]} frames")
    
    # Check frame indices
    cursor.execute("""
        SELECT frame_index, COUNT(*) as count
        FROM calibration_frames 
        WHERE session_id = %s
        GROUP BY frame_index
        HAVING count > 1
        LIMIT 5
    """, (session_id,))
    
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"\nWARNING: Found duplicate frame indices:")
        for dup in duplicates:
            print(f"  Frame index {dup[0]}: {dup[1]} times")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_frames()