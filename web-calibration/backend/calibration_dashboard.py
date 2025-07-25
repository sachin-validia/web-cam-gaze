#!/usr/bin/env python3
"""
Calibration Process Dashboard

A comprehensive monitoring tool that tracks:
1. Database activity (sessions, frames)
2. Backend logs and errors
3. Real-time statistics
4. Performance metrics

Usage: python calibration_dashboard.py test_candidate_002
"""

import sys
import time
import json
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from collections import deque

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
        structlog.dev.ConsoleRenderer(colors=False)
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

class CalibrationDashboard:
    def __init__(self, candidate_id):
        self.candidate_id = candidate_id
        self.db = get_simple_db()
        self.session_id = None
        self.start_time = datetime.now()
        
        # Metrics
        self.metrics = {
            'total_frames': 0,
            'successful_frames': 0,
            'failed_frames': 0,
            'avg_confidence': 0.0,
            'frames_per_second': 0.0,
            'database_errors': 0,
            'api_errors': 0,
            'last_frame_time': None
        }
        
        # Recent events queue (for log display)
        self.recent_events = deque(maxlen=10)
        
        # Frame timing
        self.frame_times = deque(maxlen=30)  # Track last 30 frames for FPS
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def find_or_wait_for_session(self):
        """Find active session or wait for one to be created"""
        while True:
            query = """
            SELECT id, status, created_at, updated_at, error_message
            FROM calibration_sessions 
            WHERE candidate_id = %s 
            AND created_at >= %s
            ORDER BY created_at DESC 
            LIMIT 1
            """
            result = self.db.execute_query(
                query, 
                (self.candidate_id, self.start_time - timedelta(minutes=5)),
                fetch_one=True
            )
            
            if result:
                self.session_id = result['id']
                self.add_event("✅", f"Session found: {self.session_id[:8]}...")
                return result
            
            self.add_event("⏳", "Waiting for session creation...")
            time.sleep(1)
    
    def add_event(self, icon, message):
        """Add event to recent events"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.recent_events.append(f"[{timestamp}] {icon} {message}")
    
    def update_metrics(self):
        """Update all metrics"""
        if not self.session_id:
            return
        
        # Get frame statistics
        query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN JSON_EXTRACT(frame_data, '$.success') = true THEN 1 ELSE 0 END) as successful,
            AVG(JSON_EXTRACT(frame_data, '$.confidence')) as avg_confidence,
            MAX(created_at) as last_frame_time
        FROM calibration_frames 
        WHERE session_id = %s
        """
        result = self.db.execute_query(query, (self.session_id,), fetch_one=True)
        
        if result:
            old_total = self.metrics['total_frames']
            self.metrics['total_frames'] = result['total'] or 0
            self.metrics['successful_frames'] = result['successful'] or 0
            self.metrics['failed_frames'] = self.metrics['total_frames'] - self.metrics['successful_frames']
            self.metrics['avg_confidence'] = float(result['avg_confidence'] or 0)
            
            # Calculate FPS
            if result['last_frame_time'] and old_total < self.metrics['total_frames']:
                self.frame_times.append(datetime.now())
                if len(self.frame_times) > 1:
                    time_span = (self.frame_times[-1] - self.frame_times[0]).total_seconds()
                    if time_span > 0:
                        self.metrics['frames_per_second'] = len(self.frame_times) / time_span
                
                # Add new frame event
                new_frames = self.metrics['total_frames'] - old_total
                if new_frames > 0:
                    self.add_event("📸", f"+{new_frames} new frame(s)")
        
        # Check for database errors
        error_query = """
        SELECT COUNT(*) as error_count
        FROM calibration_audit_log
        WHERE candidate_id = %s 
        AND created_at >= %s
        AND (action LIKE '%error%' OR action LIKE '%fail%')
        """
        error_result = self.db.execute_query(
            error_query,
            (self.candidate_id, self.start_time),
            fetch_one=True
        )
        
        if error_result:
            old_errors = self.metrics['database_errors']
            self.metrics['database_errors'] = error_result['error_count'] or 0
            if self.metrics['database_errors'] > old_errors:
                self.add_event("❌", f"Database error detected!")
    
    def get_target_coverage(self):
        """Get target coverage information"""
        if not self.session_id:
            return {}
        
        query = """
        SELECT 
            JSON_EXTRACT(target_position, '$.x') as x,
            JSON_EXTRACT(target_position, '$.y') as y,
            COUNT(*) as frame_count,
            AVG(JSON_EXTRACT(frame_data, '$.confidence')) as avg_confidence
        FROM calibration_frames 
        WHERE session_id = %s
        GROUP BY x, y
        """
        results = self.db.execute_query(query, (self.session_id,))
        
        coverage = {}
        for row in results:
            x, y = float(row['x']), float(row['y'])
            position = self.get_target_name(x, y)
            coverage[position] = {
                'frames': row['frame_count'],
                'confidence': float(row['avg_confidence'] or 0)
            }
        
        return coverage
    
    def get_target_name(self, x, y):
        """Get friendly name for target position"""
        if (x, y) == (0.1, 0.1): return "Top-left"
        elif (x, y) == (0.9, 0.1): return "Top-right"
        elif (x, y) == (0.1, 0.9): return "Bottom-left"
        elif (x, y) == (0.9, 0.9): return "Bottom-right"
        else: return f"({x:.1f}, {y:.1f})"
    
    def display_dashboard(self):
        """Display the dashboard"""
        self.clear_screen()
        
        # Header
        print("╔" + "═"*58 + "╗")
        print(f"║  CALIBRATION DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ║")
        print("╠" + "═"*58 + "╣")
        print(f"║  Candidate: {self.candidate_id:<43} ║")
        if self.session_id:
            print(f"║  Session: {self.session_id[:12]}...{' '*28} ║")
        print("╚" + "═"*58 + "╝")
        
        # Metrics section
        print("\n📊 METRICS")
        print("┌" + "─"*28 + "┬" + "─"*29 + "┐")
        print(f"│ Total Frames: {self.metrics['total_frames']:>12} │ Success Rate: {self.get_success_rate():>12.1f}% │")
        print(f"│ Successful: {self.metrics['successful_frames']:>14} │ Avg Confidence: {self.metrics['avg_confidence']:>10.2f} │")
        print(f"│ Failed: {self.metrics['failed_frames']:>18} │ Frames/Second: {self.metrics['frames_per_second']:>11.1f} │")
        print(f"│ Database Errors: {self.metrics['database_errors']:>9} │ Runtime: {self.get_runtime():>17} │")
        print("└" + "─"*28 + "┴" + "─"*29 + "┘")
        
        # Target coverage
        coverage = self.get_target_coverage()
        print("\n🎯 TARGET COVERAGE")
        print("┌" + "─"*20 + "┬" + "─"*10 + "┬" + "─"*12 + "┬" + "─"*12 + "┐")
        print("│ Target             │ Frames   │ Confidence │ Status     │")
        print("├" + "─"*20 + "┼" + "─"*10 + "┼" + "─"*12 + "┼" + "─"*12 + "┤")
        
        targets = ["Top-left", "Top-right", "Bottom-left", "Bottom-right"]
        for target in targets:
            if target in coverage:
                frames = coverage[target]['frames']
                conf = coverage[target]['confidence']
                status = "✅ Good" if frames >= 10 else "⚠️  Low"
                print(f"│ {target:<18} │ {frames:>8} │ {conf:>10.2f} │ {status:<10} │")
            else:
                print(f"│ {target:<18} │ {0:>8} │ {0.0:>10.2f} │ ❌ Missing │")
        print("└" + "─"*20 + "┴" + "─"*10 + "┴" + "─"*12 + "┴" + "─"*12 + "┘")
        
        # Progress bar
        self.display_progress_bar()
        
        # Recent events
        print("\n📜 RECENT EVENTS")
        print("┌" + "─"*58 + "┐")
        if self.recent_events:
            for event in self.recent_events:
                # Truncate event to fit
                if len(event) > 56:
                    event = event[:53] + "..."
                print(f"│ {event:<56} │")
        else:
            print(f"│ {'No events yet...':^56} │")
        print("└" + "─"*58 + "┘")
        
        # Instructions
        print("\n💡 Press Ctrl+C to stop monitoring")
    
    def display_progress_bar(self):
        """Display calibration progress bar"""
        expected_frames_per_target = 15
        total_expected = expected_frames_per_target * 4  # 4 targets
        progress = min(self.metrics['total_frames'] / total_expected, 1.0)
        
        bar_width = 50
        filled = int(bar_width * progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        print(f"\n📈 PROGRESS [{bar}] {progress*100:.1f}%")
        print(f"   {self.metrics['total_frames']}/{total_expected} frames captured")
    
    def get_success_rate(self):
        """Calculate success rate"""
        if self.metrics['total_frames'] == 0:
            return 0.0
        return (self.metrics['successful_frames'] / self.metrics['total_frames']) * 100
    
    def get_runtime(self):
        """Get formatted runtime"""
        runtime = datetime.now() - self.start_time
        minutes, seconds = divmod(runtime.seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def monitor_loop(self, refresh_interval=1):
        """Main monitoring loop"""
        print("🚀 Starting Calibration Dashboard...")
        print(f"🔍 Monitoring candidate: {self.candidate_id}")
        
        # Wait for session
        self.find_or_wait_for_session()
        
        try:
            while True:
                self.update_metrics()
                self.display_dashboard()
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            self.display_dashboard()  # Show final state
            print("\n\n✅ Monitoring completed!")
            
            # Final summary
            print("\n📋 FINAL SUMMARY")
            print("="*60)
            print(f"  Candidate ID: {self.candidate_id}")
            print(f"  Session ID: {self.session_id}")
            print(f"  Total Frames: {self.metrics['total_frames']}")
            print(f"  Success Rate: {self.get_success_rate():.1f}%")
            print(f"  Average Confidence: {self.metrics['avg_confidence']:.2f}")
            print(f"  Database Errors: {self.metrics['database_errors']}")
            print(f"  Total Runtime: {self.get_runtime()}")
            print("="*60)

def main():
    parser = argparse.ArgumentParser(description='Calibration Process Dashboard')
    parser.add_argument('candidate_id', nargs='?', default='test_candidate_002',
                       help='Candidate ID to monitor (default: test_candidate_002)')
    parser.add_argument('--interval', type=int, default=1,
                       help='Refresh interval in seconds (default: 1)')
    
    args = parser.parse_args()
    
    dashboard = CalibrationDashboard(args.candidate_id)
    dashboard.monitor_loop(args.interval)

if __name__ == "__main__":
    main()