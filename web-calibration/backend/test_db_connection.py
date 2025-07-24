#!/usr/bin/env python3
"""Test database connection and setup"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test MySQL connection"""
    try:
        # Get connection parameters
        config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'validia'),
            'password': os.getenv('DB_PASSWORD', 'validia123@')
        }
        
        print(f"Testing connection to MySQL at {config['host']}:{config['port']} as user '{config['user']}'...")
        
        # Test connection without database
        connection = mysql.connector.connect(**config)
        
        if connection.is_connected():
            print("✓ Successfully connected to MySQL server")
            cursor = connection.cursor()
            
            # Check if database exists
            db_name = os.getenv('DB_NAME', 'calibration_db')
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall()]
            
            if db_name in databases:
                print(f"✓ Database '{db_name}' exists")
                
                # Connect to the database
                connection.database = db_name
                
                # Check tables
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
                
                if tables:
                    print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")
                else:
                    print(f"✗ No tables found in database '{db_name}'")
                    print("  Run: mysql -u validia -p calibration_db < db/schema.sql")
            else:
                print(f"✗ Database '{db_name}' does not exist")
                print(f"  Creating database '{db_name}'...")
                cursor.execute(f"CREATE DATABASE {db_name}")
                print(f"✓ Database '{db_name}' created")
                print("  Now run: mysql -u validia -p calibration_db < db/schema.sql")
                
            cursor.close()
        else:
            print("✗ Failed to connect to MySQL")
            
    except Error as e:
        print(f"✗ MySQL Error: {e}")
        if "Access denied" in str(e):
            print("\n  Check your credentials in .env file:")
            print("  - DB_USER (current: validia)")
            print("  - DB_PASSWORD")
        elif "Can't connect" in str(e):
            print("\n  MySQL server may not be running. Start it with:")
            print("  - macOS: brew services start mysql")
            print("  - Linux: sudo systemctl start mysql")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("\nConnection closed.")

if __name__ == "__main__":
    test_connection()