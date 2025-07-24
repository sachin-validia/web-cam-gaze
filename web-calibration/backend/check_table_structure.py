#!/usr/bin/env python3
"""Check the actual table structure in the database"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def check_table_structure():
    """Check the calibration_sessions table structure"""
    try:
        config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'validia'),
            'password': os.getenv('DB_PASSWORD', 'validia123@'),
            'database': os.getenv('DB_NAME', 'calibration_db')
        }
        
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Show table structure
        cursor.execute("DESCRIBE calibration_sessions")
        print("\nTable structure for calibration_sessions:")
        print("-" * 80)
        print(f"{'Field':<20} {'Type':<30} {'Null':<5} {'Key':<5} {'Default':<15}")
        print("-" * 80)
        
        for row in cursor.fetchall():
            field, type_info, null, key, default, extra = row
            print(f"{field:<20} {type_info:<30} {null:<5} {key:<5} {str(default):<15}")
        
        # Check a specific row to see what's in the status column
        cursor.execute("SHOW CREATE TABLE calibration_sessions")
        create_statement = cursor.fetchone()[1]
        print("\n\nCREATE TABLE statement:")
        print("-" * 80)
        print(create_statement)
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_table_structure()