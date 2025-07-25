#!/usr/bin/env python3
"""Check if calibration frames are being saved to the database"""

import mysql.connector
import os
from dotenv import load_dotenv
import json

load_dotenv()

def check_calibration_frames():
    """Check calibration_frames table and data"""
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
        
        # Show table structure
        cursor.execute("DESCRIBE calibration_frames")
        print("\nTable structure for calibration_frames:")
        print("-" * 80)
        print(f"{'Field':<20} {'Type':<30} {'Null':<5} {'Key':<5} {'Default':<15}")
        print("-" * 80)
        
        for row in cursor.fetchall():
            print(f"{row['Field']:<20} {row['Type']:<30} {row['Null']:<5} {row['Key']:<5} {str(row['Default']):<15}")
        
        # Count total frames
        cursor.execute("SELECT COUNT(*) as total FROM calibration_frames")
        total_frames = cursor.fetchone()['total']
        print(f"\n\nTotal calibration frames in database: {total_frames}")
        
        # Get recent frames
        cursor.execute("""
            SELECT cf.*, cs.candidate_id, cs.status as session_status
            FROM calibration_frames cf
            JOIN calibration_sessions cs ON cf.session_id = cs.id
            ORDER BY cf.created_at DESC
            LIMIT 5
        """)
        
        recent_frames = cursor.fetchall()
        if recent_frames:
            print("\n\nMost recent calibration frames:")
            print("-" * 80)
            for frame in recent_frames:
                print(f"Session: {frame['session_id']}")
                print(f"Candidate: {frame['candidate_id']}")
                print(f"Frame Index: {frame['frame_index']}")
                print(f"Target Position: {frame['target_position']}")
                print(f"Created At: {frame['created_at']}")
                print(f"Session Status: {frame['session_status']}")
                
                # Parse and show frame data summary
                try:
                    frame_data = json.loads(frame['frame_data'])
                    print(f"Frame Data Keys: {list(frame_data.keys())}")
                    print(f"Success: {frame_data.get('success', 'N/A')}")
                except:
                    print("Frame Data: Could not parse JSON")
                print("-" * 40)
        else:
            print("\nNo calibration frames found in database!")
        
        # Check for any failed inserts in error logs
        cursor.execute("""
            SELECT COUNT(*) as error_count 
            FROM calibration_audit_log 
            WHERE action LIKE '%error%' OR action LIKE '%fail%'
        """)
        error_count = cursor.fetchone()['error_count']
        print(f"\nErrors logged in audit table: {error_count}")
        
        # Check session statuses
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM calibration_sessions
            GROUP BY status
        """)
        print("\n\nCalibration session statuses:")
        for row in cursor.fetchall():
            print(f"  {row['status']}: {row['count']}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_calibration_frames()