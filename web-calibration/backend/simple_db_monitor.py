#!/usr/bin/env python3
"""
Simple Database Connection for Monitoring Tools

This provides a simplified database connection that doesn't require
the full FastAPI application context.
"""

import mysql.connector
from mysql.connector import Error
import structlog
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = structlog.get_logger()

class SimpleDatabase:
    """Simple database connection for monitoring scripts"""
    
    def __init__(self):
        self.connection = None
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'rootpassword'),
            'database': os.getenv('DB_NAME', 'calibration_db'),
            'autocommit': True,
            'use_unicode': True,
            'charset': 'utf8mb4'
        }
    
    def connect(self):
        """Create database connection"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            logger.info("Database connected successfully")
            return True
        except Error as e:
            logger.error("Failed to connect to database", error=str(e))
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False) -> Any:
        """Execute a query and return results"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if cursor.with_rows:
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                cursor.close()
                return result
            
            cursor.close()
            return None
            
        except Error as e:
            logger.error("Query execution failed", error=str(e), query=query)
            return None
    
    def execute_insert(self, query: str, params: tuple) -> Optional[int]:
        """Execute an insert query and return the last insert id"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            last_id = cursor.lastrowid
            cursor.close()
            return last_id
            
        except Error as e:
            logger.error("Insert failed", error=str(e), query=query)
            return None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

def get_simple_db() -> SimpleDatabase:
    """Get a simple database connection"""
    db = SimpleDatabase()
    db.connect()
    return db