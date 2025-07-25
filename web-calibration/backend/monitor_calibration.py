#!/usr/bin/env python3
"""
Calibration Process Monitor

This script monitors the calibration process for a specific candidate ID.
It tracks:
1. Session creation
2. Frame insertions into calibration_frames table
3. Any database errors during the process
4. Real-time statistics

Usage: python monitor_calibration.py test_candidate_002
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from simple_db_monitor import get_simple_db
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True)
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

class CalibrationMonitor:
    def __init__(self, candidate_id):
        self.candidate_id = candidate_id
        self.db = get_simple_db()
        self.session_id = None
        self.start_time = datetime.now()
        self.last_frame_count = 0
        
    def find_active_session(self):
        """Find the most recent active session for the candidate"""
        query = """
        SELECT id, status, created_at, updated_at, error_message
        FROM calibration_sessions 
        WHERE candidate_id = %s 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        result = self.db.execute_query(query, (self.candidate_id,), fetch_one=True)
        
        if result:
            self.session_id = result['id']
            logger.info("Found session", 
                       session_id=self.session_id,
                       status=result['status'],
                       created_at=result['created_at'].isoformat())
            return result
        return None
    
    def get_frame_count(self):
        """Get current frame count for the session"""
        if not self.session_id:
            return 0
            
        query = """
        SELECT COUNT(*) as count 
        FROM calibration_frames 
        WHERE session_id = %s
        """
        result = self.db.execute_query(query, (self.session_id,), fetch_one=True)
        return result['count'] if result else 0
    
    def get_latest_frames(self, limit=5):
        """Get the most recent frames"""
        if not self.session_id:
            return []
            
        query = """
        SELECT frame_index, created_at, 
               JSON_EXTRACT(frame_data, '$.success') as success,
               JSON_EXTRACT(frame_data, '$.confidence') as confidence,
               JSON_EXTRACT(target_position, '$.x') as target_x,
               JSON_EXTRACT(target_position, '$.y') as target_y
        FROM calibration_frames 
        WHERE session_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        return self.db.execute_query(query, (self.session_id, limit))
    
    def check_database_errors(self):
        """Check for any recent database errors in audit log"""
        query = """
        SELECT action, details, created_at
        FROM calibration_audit_log
        WHERE candidate_id = %s 
        AND created_at >= %s
        AND (action LIKE '%error%' OR action LIKE '%fail%')
        ORDER BY created_at DESC
        """
        errors = self.db.execute_query(query, 
                                     (self.candidate_id, self.start_time))
        return errors
    
    def display_status(self):
        """Display current calibration status"""
        print("\n" + "="*60)
        print(f"CALIBRATION MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Candidate ID: {self.candidate_id}")
        print("="*60)
        
        # Session info
        session_info = self.find_active_session()
        if not session_info:
            print("⚠️  No active session found yet...")
            return
            
        print(f"\n📍 Session ID: {self.session_id}")
        print(f"   Status: {session_info['status']}")
        print(f"   Started: {session_info['created_at']}")
        
        if session_info['error_message']:
            print(f"   ❌ Error: {session_info['error_message']}")
        
        # Frame statistics
        frame_count = self.get_frame_count()
        new_frames = frame_count - self.last_frame_count
        self.last_frame_count = frame_count
        
        print(f"\n📊 Frame Statistics:")
        print(f"   Total frames: {frame_count}")
        if new_frames > 0:
            print(f"   ✅ New frames: +{new_frames}")
        
        # Latest frames
        latest_frames = self.get_latest_frames()
        if latest_frames:
            print(f"\n📸 Latest Frames:")
            for frame in latest_frames:
                success = "✅" if frame['success'] == 1 else "❌"
                confidence = frame['confidence'] if frame['confidence'] else 0
                print(f"   Frame {frame['frame_index']}: {success} " +
                      f"Target({frame['target_x']:.2f}, {frame['target_y']:.2f}) " +
                      f"Confidence: {confidence:.2f}")
        
        # Check for errors
        errors = self.check_database_errors()
        if errors:
            print(f"\n⚠️  Database Errors Detected:")
            for error in errors[:3]:  # Show last 3 errors
                details = json.loads(error['details']) if error['details'] else {}
                print(f"   - {error['action']}: {details.get('error', 'Unknown error')}")
                print(f"     Time: {error['created_at']}")
        
        # Target coverage
        if frame_count > 0:
            target_query = """
            SELECT DISTINCT 
                JSON_EXTRACT(target_position, '$.x') as x,
                JSON_EXTRACT(target_position, '$.y') as y,
                COUNT(*) as frame_count
            FROM calibration_frames 
            WHERE session_id = %s
            GROUP BY x, y
            """
            targets = self.db.execute_query(target_query, (self.session_id,))
            
            print(f"\n🎯 Target Coverage:")
            expected_targets = [(0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)]
            for target in targets:
                x, y = float(target['x']), float(target['y'])
                position = "Unknown"
                if (x, y) == (0.1, 0.1): position = "Top-left"
                elif (x, y) == (0.9, 0.1): position = "Top-right"
                elif (x, y) == (0.1, 0.9): position = "Bottom-left"
                elif (x, y) == (0.9, 0.9): position = "Bottom-right"
                
                print(f"   {position}: {target['frame_count']} frames")
            
            # Check missing targets
            covered_positions = [(float(t['x']), float(t['y'])) for t in targets]
            missing = [t for t in expected_targets if t not in covered_positions]
            if missing:
                print(f"   ⚠️  Missing targets: {len(missing)}")
    
    def monitor_loop(self, refresh_interval=2):
        """Main monitoring loop"""
        print(f"Starting calibration monitor for candidate: {self.candidate_id}")
        print(f"Refresh interval: {refresh_interval} seconds")
        print("Press Ctrl+C to stop monitoring\n")
        
        try:
            while True:
                self.display_status()
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped.")
            
            # Final summary
            if self.session_id:
                print(f"\n📋 Final Summary:")
                print(f"   Session ID: {self.session_id}")
                print(f"   Total frames captured: {self.last_frame_count}")
                print(f"   Duration: {datetime.now() - self.start_time}")

def main():
    parser = argparse.ArgumentParser(description='Monitor calibration process')
    parser.add_argument('candidate_id', nargs='?', default='test_candidate_002',
                       help='Candidate ID to monitor (default: test_candidate_002)')
    parser.add_argument('--interval', type=int, default=2,
                       help='Refresh interval in seconds (default: 2)')
    
    args = parser.parse_args()
    
    monitor = CalibrationMonitor(args.candidate_id)
    monitor.monitor_loop(args.interval)

if __name__ == "__main__":
    main()