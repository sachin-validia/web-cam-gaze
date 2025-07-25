#!/usr/bin/env python3
"""
Debug script to trace the complete calibration data flow
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style
import structlog

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from db.storage_service import DatabaseStorageService
from db.database import get_db

# Initialize colorama for colored output
init(autoreset=True)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class CalibrationDebugger:
    """Debug tool for calibration data flow"""
    
    def __init__(self):
        self.storage = DatabaseStorageService()
        self.db = get_db()
        
    def print_section(self, title: str):
        """Print a formatted section header"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{title}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
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
                print(f"{Fore.GREEN}✓ {table}: {count} records{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ {table}: {str(e)}{Style.RESET_ALL}")
    
    def trace_session_flow(self, session_id: str = None, candidate_id: str = None):
        """Trace the complete flow for a session"""
        self.print_section("SESSION FLOW TRACE")
        
        # Get the most recent session if not specified
        if not session_id:
            query = """
            SELECT id, candidate_id, status, created_at 
            FROM calibration_sessions 
            ORDER BY created_at DESC 
            LIMIT 1
            """
            session = self.db.execute_query(query, fetch_one=True)
            if session:
                session_id = session['id']
                candidate_id = session['candidate_id']
                print(f"Using most recent session: {session_id}")
                print(f"Candidate ID: {candidate_id}")
                print(f"Status: {session['status']}")
                print(f"Created: {session['created_at']}")
            else:
                print(f"{Fore.RED}No sessions found{Style.RESET_ALL}")
                return
        
        # Check screen info
        self.print_section("SCREEN INFO CHECK")
        screen_info = self.storage.get_screen_info(candidate_id)
        if screen_info:
            print(f"{Fore.GREEN}✓ Screen info exists{Style.RESET_ALL}")
            print(json.dumps(screen_info, indent=2))
        else:
            print(f"{Fore.RED}✗ No screen info found{Style.RESET_ALL}")
        
        # Check calibration frames
        self.print_section("CALIBRATION FRAMES CHECK")
        frames = self.storage.get_calibration_frames(session_id)
        if frames:
            print(f"{Fore.GREEN}✓ Found {len(frames)} frames{Style.RESET_ALL}")
            
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
        else:
            print(f"{Fore.RED}✗ No calibration frames found{Style.RESET_ALL}")
        
        # Check calibration data
        self.print_section("CALIBRATION DATA CHECK")
        cal_exists = self.storage.check_calibration_exists(candidate_id)
        if cal_exists:
            print(f"{Fore.GREEN}✓ Calibration data exists{Style.RESET_ALL}")
            
            # Get calibration files
            files = self.storage.get_calibration_files(candidate_id)
            if files:
                print("Files generated:")
                for filename in files.keys():
                    print(f"  - {filename}")
        else:
            print(f"{Fore.RED}✗ No calibration data found{Style.RESET_ALL}")
        
        # Check audit log
        self.print_section("AUDIT LOG CHECK")
        query = """
        SELECT action, created_at, details
        FROM calibration_audit_log
        WHERE candidate_id = %s
        ORDER BY created_at DESC
        LIMIT 10
        """
        audit_logs = self.db.execute_query(query, (candidate_id,))
        if audit_logs:
            print(f"Found {len(audit_logs)} audit entries:")
            for log in audit_logs:
                print(f"\n  - Action: {log['action']}")
                print(f"    Time: {log['created_at']}")
                if log['details']:
                    details = json.loads(log['details'])
                    print(f"    Details: {json.dumps(details, indent=6)}")
        else:
            print(f"{Fore.YELLOW}No audit logs found{Style.RESET_ALL}")
    
    def analyze_error_patterns(self):
        """Analyze common error patterns"""
        self.print_section("ERROR PATTERN ANALYSIS")
        
        # Check for failed sessions
        query = """
        SELECT candidate_id, error_message, created_at
        FROM calibration_sessions
        WHERE status = 'failed'
        ORDER BY created_at DESC
        LIMIT 10
        """
        failed_sessions = self.db.execute_query(query)
        
        if failed_sessions:
            print(f"{Fore.YELLOW}Failed sessions found:{Style.RESET_ALL}")
            for session in failed_sessions:
                print(f"\n  - Candidate: {session['candidate_id']}")
                print(f"    Error: {session['error_message']}")
                print(f"    Time: {session['created_at']}")
        else:
            print(f"{Fore.GREEN}No failed sessions found{Style.RESET_ALL}")
    
    def test_api_flow(self, candidate_id: str = "test_debug"):
        """Test the complete API flow with debug output"""
        self.print_section("API FLOW TEST")
        
        # This would simulate the API calls
        print("To test the API flow, run the following curl commands:")
        print(f"\n1. Create session:")
        print(f"   curl -X POST http://localhost:8000/api/calibration/session/create \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"candidate_id\": \"{candidate_id}\"}}'")
        
        print(f"\n2. Save screen info:")
        print(f"   curl -X POST http://localhost:8000/api/screen/info \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"candidate_id\": \"{candidate_id}\", \"screen_width_px\": 1920, \"screen_height_px\": 1080}}'")
        
        print(f"\n3. Start calibration:")
        print(f"   curl -X POST http://localhost:8000/api/calibration/start \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"session_id\": \"<SESSION_ID>\", \"candidate_id\": \"{candidate_id}\"}}'")
        
        print(f"\n4. Complete calibration:")
        print(f"   curl -X POST http://localhost:8000/api/calibration/complete \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"session_id\": \"<SESSION_ID>\", \"candidate_id\": \"{candidate_id}\"}}'")

def main():
    """Main debug function"""
    debugger = CalibrationDebugger()
    
    # Check database tables
    debugger.check_database_tables()
    
    # Trace session flow
    debugger.trace_session_flow()
    
    # Analyze errors
    debugger.analyze_error_patterns()
    
    # Show API test commands
    debugger.test_api_flow()
    
    # Summary
    debugger.print_section("DEBUGGING SUMMARY")
    print("Review the output above to identify where the calibration flow is failing.")
    print("\nCommon issues to check:")
    print("1. Missing calibration frames in database")
    print("2. GazeService not initialized (check logs)")
    print("3. Transform matrix computation failing")
    print("4. File validation errors")
    print("5. Database connection issues")

if __name__ == "__main__":
    main()