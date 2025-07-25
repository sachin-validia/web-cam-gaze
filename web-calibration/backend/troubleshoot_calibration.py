#!/usr/bin/env python3
"""
Calibration Troubleshooting Tool

This script checks for common issues that might prevent calibration from working:
1. Database connectivity
2. Table structure
3. Foreign key constraints
4. Recent errors
5. Session state issues

Usage: python troubleshoot_calibration.py test_candidate_002
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from simple_db_monitor import get_simple_db
from db.storage_service import DatabaseStorageService

class CalibrationTroubleshooter:
    def __init__(self, candidate_id):
        self.candidate_id = candidate_id
        self.db = get_simple_db()
        self.storage = DatabaseStorageService()
        self.issues_found = []
        
    def check_database_connection(self):
        """Check if database is accessible"""
        print("\n🔍 Checking database connection...")
        try:
            # Test basic query
            result = self.db.execute_query("SELECT 1", fetch_one=True)
            if result:
                print("  ✅ Database connection successful")
                return True
            else:
                print("  ❌ Database query returned no results")
                self.issues_found.append("Database query failed")
                return False
        except Exception as e:
            print(f"  ❌ Database connection failed: {e}")
            self.issues_found.append(f"Database connection error: {e}")
            return False
    
    def check_table_structure(self):
        """Verify all required tables exist"""
        print("\n🔍 Checking table structure...")
        required_tables = [
            'calibration_sessions',
            'calibration_frames',
            'screen_info',
            'calibration_data',
            'calibration_audit_log'
        ]
        
        all_good = True
        for table in required_tables:
            try:
                query = f"SELECT COUNT(*) as count FROM {table} LIMIT 1"
                self.db.execute_query(query)
                print(f"  ✅ Table '{table}' exists")
            except Exception as e:
                print(f"  ❌ Table '{table}' missing or inaccessible: {e}")
                self.issues_found.append(f"Table '{table}' issue")
                all_good = False
        
        return all_good
    
    def check_recent_sessions(self):
        """Check for recent sessions and their status"""
        print(f"\n🔍 Checking sessions for candidate: {self.candidate_id}")
        
        try:
            # Get recent sessions
            query = """
            SELECT id, status, created_at, updated_at, error_message
            FROM calibration_sessions
            WHERE candidate_id = %s
            AND created_at >= %s
            ORDER BY created_at DESC
            LIMIT 5
            """
            
            cutoff_time = datetime.now() - timedelta(hours=24)
            sessions = self.db.execute_query(query, (self.candidate_id, cutoff_time))
            
            if not sessions:
                print("  ⚠️  No sessions found in the last 24 hours")
                return True
            
            print(f"  Found {len(sessions)} recent session(s):")
            
            for session in sessions:
                status_icon = {
                    'in_progress': '🔄',
                    'completed': '✅',
                    'failed': '❌'
                }.get(session['status'], '❓')
                
                print(f"\n  {status_icon} Session: {session['id']}")
                print(f"     Status: {session['status']}")
                print(f"     Created: {session['created_at']}")
                
                if session['error_message']:
                    print(f"     ❌ Error: {session['error_message']}")
                    self.issues_found.append(f"Session {session['id'][:8]} failed")
                
                # Check frames for this session
                frame_count = self.check_session_frames(session['id'])
                print(f"     Frames: {frame_count}")
                
            return True
            
        except Exception as e:
            print(f"  ❌ Error checking sessions: {e}")
            self.issues_found.append(f"Session check error: {e}")
            return False
    
    def check_session_frames(self, session_id):
        """Check frames for a specific session"""
        try:
            query = """
            SELECT COUNT(*) as count
            FROM calibration_frames
            WHERE session_id = %s
            """
            result = self.db.execute_query(query, (session_id,), fetch_one=True)
            return result['count'] if result else 0
        except:
            return 0
    
    def check_foreign_key_issues(self):
        """Check for foreign key constraint issues"""
        print("\n🔍 Checking foreign key constraints...")
        
        try:
            # Check orphaned frames
            query = """
            SELECT COUNT(*) as count
            FROM calibration_frames f
            LEFT JOIN calibration_sessions s ON f.session_id = s.id
            WHERE s.id IS NULL
            """
            result = self.db.execute_query(query, fetch_one=True)
            orphaned = result['count'] if result else 0
            
            if orphaned > 0:
                print(f"  ⚠️  Found {orphaned} orphaned frame(s)")
                self.issues_found.append(f"{orphaned} orphaned frames")
            else:
                print("  ✅ No orphaned frames found")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error checking constraints: {e}")
            return False
    
    def check_recent_errors(self):
        """Check audit log for recent errors"""
        print("\n🔍 Checking recent errors in audit log...")
        
        try:
            query = """
            SELECT action, details, created_at
            FROM calibration_audit_log
            WHERE candidate_id = %s
            AND created_at >= %s
            AND (action LIKE '%error%' OR action LIKE '%fail%')
            ORDER BY created_at DESC
            LIMIT 10
            """
            
            cutoff_time = datetime.now() - timedelta(hours=1)
            errors = self.db.execute_query(query, (self.candidate_id, cutoff_time))
            
            if not errors:
                print("  ✅ No errors found in the last hour")
                return True
            
            print(f"  ⚠️  Found {len(errors)} error(s):")
            for error in errors[:5]:  # Show max 5
                print(f"\n  ❌ {error['action']}")
                print(f"     Time: {error['created_at']}")
                if error['details']:
                    try:
                        import json
                        details = json.loads(error['details'])
                        if 'error' in details:
                            print(f"     Details: {details['error']}")
                    except:
                        pass
            
            self.issues_found.extend([f"Audit error: {e['action']}" for e in errors])
            return False
            
        except Exception as e:
            print(f"  ❌ Error checking audit log: {e}")
            return False
    
    def check_screen_info(self):
        """Check if screen info exists"""
        print(f"\n🔍 Checking screen info for candidate: {self.candidate_id}")
        
        try:
            screen_info = self.storage.get_screen_info(self.candidate_id)
            
            if screen_info:
                print("  ✅ Screen info exists")
                print(f"     Resolution: {screen_info.get('width', 'N/A')}x{screen_info.get('height', 'N/A')}")
                return True
            else:
                print("  ⚠️  No screen info found")
                print("     Screen info must be saved before calibration")
                self.issues_found.append("Missing screen info")
                return False
                
        except Exception as e:
            print(f"  ❌ Error checking screen info: {e}")
            self.issues_found.append(f"Screen info error: {e}")
            return False
    
    def suggest_fixes(self):
        """Suggest fixes based on issues found"""
        print("\n💡 RECOMMENDATIONS:")
        
        if not self.issues_found:
            print("  ✅ No issues found! The system appears to be working correctly.")
            return
        
        # Provide specific recommendations
        for issue in self.issues_found:
            if "Database connection" in issue:
                print("\n  🔧 Database Connection Issue:")
                print("     - Check if MySQL is running")
                print("     - Verify database credentials in config")
                print("     - Ensure 'calibration_db' database exists")
                
            elif "Table" in issue and "missing" in issue:
                print("\n  🔧 Missing Tables:")
                print("     - Run: mysql -u root -p calibration_db < db/schema.sql")
                print("     - This will create all required tables")
                
            elif "Missing screen info" in issue:
                print("\n  🔧 Missing Screen Info:")
                print("     - Ensure the frontend calls /api/screen/save first")
                print("     - Screen info must be saved before calibration starts")
                
            elif "orphaned frames" in issue:
                print("\n  🔧 Orphaned Frames:")
                print("     - Run: python clear_tables.py --orphaned")
                print("     - This will clean up orphaned records")
                
            elif "Session" in issue and "failed" in issue:
                print("\n  🔧 Failed Session:")
                print("     - Check backend logs for detailed error messages")
                print("     - Ensure GazeService is properly initialized")
                print("     - Verify camera permissions are granted")
    
    def run_diagnostics(self):
        """Run all diagnostic checks"""
        print("="*60)
        print("🔧 CALIBRATION TROUBLESHOOTING TOOL")
        print("="*60)
        print(f"Candidate ID: {self.candidate_id}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run checks
        checks = [
            self.check_database_connection,
            self.check_table_structure,
            self.check_screen_info,
            self.check_recent_sessions,
            self.check_foreign_key_issues,
            self.check_recent_errors
        ]
        
        all_passed = True
        for check in checks:
            if not check():
                all_passed = False
        
        # Summary
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        
        if all_passed and not self.issues_found:
            print("✅ All checks passed! System is ready for calibration.")
        else:
            print(f"❌ Found {len(self.issues_found)} issue(s):")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"   {i}. {issue}")
        
        # Provide recommendations
        self.suggest_fixes()
        
        print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description='Troubleshoot calibration issues')
    parser.add_argument('candidate_id', nargs='?', default='test_candidate_002',
                       help='Candidate ID to check (default: test_candidate_002)')
    
    args = parser.parse_args()
    
    troubleshooter = CalibrationTroubleshooter(args.candidate_id)
    troubleshooter.run_diagnostics()

if __name__ == "__main__":
    main()