#!/usr/bin/env python3
"""Script to clear all calibration tables"""

import mysql.connector
from utils.config import settings

def clear_all_tables():
    """Clear all calibration tables"""
    conn = mysql.connector.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME
    )
    
    cursor = conn.cursor()
    
    # Clear tables in correct order due to foreign key constraints
    tables = [
        'calibration_frames',
        'calibration_data', 
        'screen_info',
        'calibration_sessions',
        'calibration_audit_log'
    ]
    
    for table in tables:
        cursor.execute(f'DELETE FROM {table}')
        count = cursor.rowcount
        print(f'Cleared {count} rows from {table} table')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print('\nAll tables cleared successfully!')

if __name__ == "__main__":
    clear_all_tables()