"""
Database connection and session management
"""

import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
import structlog
from typing import Optional, Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.config import settings

logger = structlog.get_logger()

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.pool: Optional[pooling.MySQLConnectionPool] = None
        self.config = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'database': settings.DB_NAME,
            'pool_name': 'calibration_pool',
            'pool_size': 10,
            'pool_reset_session': True,
            'autocommit': False,
            'use_unicode': True,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
    
    def init_pool(self):
        """Initialize connection pool"""
        try:
            self.pool = pooling.MySQLConnectionPool(**self.config)
            logger.info("Database connection pool initialized", 
                       pool_size=self.config['pool_size'])
        except mysql.connector.Error as e:
            logger.error("Failed to initialize database pool", error=str(e))
            raise
    
    def close_pool(self):
        """Close all connections in the pool"""
        if self.pool:
            # MySQL connector doesn't have a direct close_pool method
            # Connections will be closed when they're returned to the pool
            logger.info("Database connections will be closed on return to pool")
            self.pool = None
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        connection = None
        try:
            connection = self.pool.get_connection()
            yield connection
            connection.commit()
        except mysql.connector.Error as e:
            if connection:
                connection.rollback()
            logger.error("Database error", error=str(e))
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    @contextmanager
    def get_cursor(self, dictionary=True):
        """Get a database cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=dictionary)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False) -> Any:
        """Execute a query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            if cursor.with_rows:
                return cursor.fetchone() if fetch_one else cursor.fetchall()
            return None
    
    def execute_insert(self, query: str, params: tuple) -> int:
        """Execute an insert query and return the last insert id"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple) -> int:
        """Execute an update query and return affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: list) -> int:
        """Execute a query with multiple parameter sets"""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount

# Global database manager instance
db_manager = DatabaseManager()

def init_db():
    """Initialize the database connection pool"""
    db_manager.init_pool()

def close_db():
    """Close the database connection pool"""
    db_manager.close_pool()

def get_db() -> DatabaseManager:
    """Get the database manager instance"""
    return db_manager