#!/usr/bin/env python3
"""Analyze calibration frames to identify storage issues"""

import mysql.connector
import os
from dotenv import load_dotenv
import json
from collections import defaultdict

load_dotenv()

def analyze_calibration_frames():
    """Analyze calibration frames for patterns and issues"""
    try:
        config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'validia'),
            'password': os.getenv('DB_PASSWORD', 'validia123@'),
            'database': os.getenv('DB_NAME', 'calibration_db')
        }
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor(dictionary=True)
        
        # Get all sessions and their frame counts
        cursor.execute("""
            SELECT 
                cs.id as session_id,
                cs.candidate_id,
                cs.status,
                cs.created_at as session_created,
                COUNT(cf.id) as frame_count,
                MIN(cf.frame_index) as min_frame_index,
                MAX(cf.frame_index) as max_frame_index,
                COUNT(DISTINCT cf.target_position) as unique_targets
            FROM calibration_sessions cs
            LEFT JOIN calibration_frames cf ON cs.id = cf.session_id
            GROUP BY cs.id
            ORDER BY cs.created_at DESC
        """)
        
        sessions = cursor.fetchall()
        print("Session Analysis:")
        print("-" * 100)
        print(f"{'Session ID':<40} {'Candidate':<20} {'Status':<12} {'Frames':<8} {'Targets':<8}")
        print("-" * 100)
        
        for session in sessions:
            print(f"{session['session_id']:<40} {session['candidate_id']:<20} {session['status']:<12} "
                  f"{session['frame_count']:<8} {session['unique_targets']:<8}")
        
        # Analyze frame distribution for the most recent session with frames
        if sessions and sessions[0]['frame_count'] > 0:
            recent_session_id = sessions[0]['session_id']
            print(f"\n\nDetailed analysis for session: {recent_session_id}")
            
            # Get frame distribution by target
            cursor.execute("""
                SELECT 
                    target_position,
                    COUNT(*) as frame_count,
                    MIN(frame_index) as min_index,
                    MAX(frame_index) as max_index
                FROM calibration_frames
                WHERE session_id = %s
                GROUP BY target_position
            """, (recent_session_id,))
            
            target_distribution = cursor.fetchall()
            print("\nFrames per target position:")
            print("-" * 60)
            for target in target_distribution:
                print(f"Target: {target['target_position']}")
                print(f"  Frames: {target['frame_count']}")
                print(f"  Index range: {target['min_index']} - {target['max_index']}")
            
            # Check for duplicate frame indices
            cursor.execute("""
                SELECT frame_index, COUNT(*) as count
                FROM calibration_frames
                WHERE session_id = %s
                GROUP BY frame_index
                HAVING COUNT(*) > 1
            """, (recent_session_id,))
            
            duplicates = cursor.fetchall()
            if duplicates:
                print("\n⚠️  WARNING: Duplicate frame indices found!")
                for dup in duplicates:
                    print(f"  Frame index {dup['frame_index']}: {dup['count']} occurrences")
            else:
                print("\n✓ No duplicate frame indices found")
            
            # Check frame sequence continuity
            cursor.execute("""
                SELECT DISTINCT frame_index
                FROM calibration_frames
                WHERE session_id = %s
                ORDER BY frame_index
            """, (recent_session_id,))
            
            frame_indices = [row['frame_index'] for row in cursor.fetchall()]
            if frame_indices:
                expected_indices = list(range(frame_indices[0], frame_indices[-1] + 1))
                missing_indices = set(expected_indices) - set(frame_indices)
                if missing_indices:
                    print(f"\n⚠️  WARNING: Missing frame indices: {sorted(missing_indices)}")
                else:
                    print("\n✓ Frame sequence is continuous")
            
            # Check timing between frames
            cursor.execute("""
                SELECT 
                    frame_index,
                    created_at,
                    JSON_EXTRACT(frame_data, '$.timestamp') as frame_timestamp
                FROM calibration_frames
                WHERE session_id = %s
                ORDER BY created_at
                LIMIT 10
            """, (recent_session_id,))
            
            print("\n\nFirst 10 frames timing:")
            print("-" * 60)
            frames = cursor.fetchall()
            for i, frame in enumerate(frames):
                print(f"Frame {frame['frame_index']}: {frame['created_at']} (internal: {frame['frame_timestamp']})")
                if i > 0:
                    time_diff = (frame['created_at'] - frames[i-1]['created_at']).total_seconds()
                    print(f"  Time since previous: {time_diff:.3f}s")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_calibration_frames()