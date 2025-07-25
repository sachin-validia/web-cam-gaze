#!/usr/bin/env python3
"""
Backend Log Monitor

This script monitors the backend logs for errors and important events
during the calibration process.

Usage: python monitor_backend_logs.py
"""

import subprocess
import sys
import re
from datetime import datetime
import signal

class BackendLogMonitor:
    def __init__(self):
        self.error_patterns = [
            r'ERROR',
            r'Failed to',
            r'Database error',
            r'Exception',
            r'Traceback',
            r'MySQL',
            r'Connection',
            r'timeout',
            r'refused'
        ]
        
        self.important_patterns = [
            r'Calibration session created',
            r'Frame saved successfully',
            r'Calibration started',
            r'Calibration completed',
            r'GazeService',
            r'POST /api/calibration',
            r'POST /api/session',
            r'save_calibration_frame',
            r'calibration_frames'
        ]
        
        self.stats = {
            'errors': 0,
            'frames_saved': 0,
            'sessions_created': 0,
            'api_calls': 0
        }
        
    def parse_log_line(self, line):
        """Parse and categorize log line"""
        # Check for errors
        for pattern in self.error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                self.stats['errors'] += 1
                return ('error', line.strip())
        
        # Check for important events
        for pattern in self.important_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Count specific events
                if 'Frame saved successfully' in line:
                    self.stats['frames_saved'] += 1
                elif 'Calibration session created' in line:
                    self.stats['sessions_created'] += 1
                elif 'POST /api/' in line:
                    self.stats['api_calls'] += 1
                    
                return ('info', line.strip())
        
        # Check for HTTP requests
        if re.search(r'(GET|POST|PUT|DELETE) /api/', line):
            self.stats['api_calls'] += 1
            return ('http', line.strip())
            
        return (None, None)
    
    def format_output(self, event_type, message):
        """Format output with colors and symbols"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if event_type == 'error':
            return f"[{timestamp}] ❌ ERROR: {message}"
        elif event_type == 'info':
            if 'Frame saved' in message:
                return f"[{timestamp}] 📸 FRAME: {message}"
            elif 'session created' in message:
                return f"[{timestamp}] ✅ SESSION: {message}"
            elif 'POST /api/calibration/frame' in message:
                # Extract response time if available
                match = re.search(r'(\d+)ms', message)
                time_str = f" ({match.group(1)}ms)" if match else ""
                return f"[{timestamp}] 📡 API: Frame submission{time_str}"
            else:
                return f"[{timestamp}] ℹ️  INFO: {message}"
        elif event_type == 'http':
            return f"[{timestamp}] 🌐 HTTP: {message}"
        
        return None
    
    def display_stats(self):
        """Display current statistics"""
        print("\n" + "-"*50)
        print("📊 STATISTICS:")
        print(f"  Sessions Created: {self.stats['sessions_created']}")
        print(f"  Frames Saved: {self.stats['frames_saved']}")
        print(f"  API Calls: {self.stats['api_calls']}")
        print(f"  Errors: {self.stats['errors']}")
        print("-"*50 + "\n")
    
    def monitor_logs(self):
        """Monitor backend logs in real-time"""
        print("🔍 Backend Log Monitor Started")
        print("Monitoring for calibration events and errors...")
        print("Press Ctrl+C to stop\n")
        
        # Try to find the backend process
        try:
            # First, try to tail the log file if it exists
            log_files = [
                'calibration.log',
                'app.log',
                'backend.log'
            ]
            
            for log_file in log_files:
                try:
                    process = subprocess.Popen(
                        ['tail', '-f', log_file],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=1
                    )
                    print(f"📄 Tailing log file: {log_file}\n")
                    break
                except:
                    continue
            else:
                # If no log file found, try to capture stdout from the backend
                print("⚠️  No log files found. Waiting for backend output...")
                print("Make sure the backend is running with verbose logging.\n")
                
                # Monitor system logs for Python processes
                process = subprocess.Popen(
                    ['tail', '-f', '/dev/null'],  # Placeholder
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1
                )
            
            # Set up signal handler for stats display
            def show_stats(signum, frame):
                self.display_stats()
            
            signal.signal(signal.SIGUSR1, show_stats)
            
            line_count = 0
            while True:
                line = process.stdout.readline()
                if line:
                    event_type, message = self.parse_log_line(line)
                    if event_type:
                        output = self.format_output(event_type, message)
                        if output:
                            print(output)
                            
                            # Show stats every 20 relevant lines
                            line_count += 1
                            if line_count % 20 == 0:
                                self.display_stats()
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped.")
            self.display_stats()
            if 'process' in locals():
                process.terminate()
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    monitor = BackendLogMonitor()
    monitor.monitor_logs()

if __name__ == "__main__":
    main()