"""
Setup Knowledge Base Table

This script creates and populates a knowledge_base table in the MSSQL database
with customer support articles for the customer support agent.

Usage:
    python setup_knowledge_base.py
"""

import os
import pyodbc
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_to_database(connection_string: str) -> pyodbc.Connection:
    """Connect to the MSSQL database."""
    try:
        connection = pyodbc.connect(connection_string)
        print("✓ Connected to database successfully")
        return connection
    except pyodbc.Error as e:
        print(f"❌ Failed to connect to database: {e}")
        raise


def drop_table_if_exists(connection: pyodbc.Connection, table_name: str) -> None:
    """Drop the table if it exists."""
    cursor = connection.cursor()
    try:
        cursor.execute(f"IF OBJECT_ID('{table_name}', 'U') IS NOT NULL DROP TABLE {table_name}")
        connection.commit()
        print(f"✓ Dropped existing table '{table_name}' (if it existed)")
    except pyodbc.Error as e:
        connection.rollback()
        print(f"❌ Failed to drop table: {e}")
        raise
    finally:
        cursor.close()


def create_knowledge_base_table(connection: pyodbc.Connection, table_name: str) -> None:
    """Create the knowledge_base table."""
    cursor = connection.cursor()
    try:
        create_sql = f"""
        CREATE TABLE {table_name} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            keyword VARCHAR(50) NOT NULL,
            article NVARCHAR(MAX) NOT NULL
        )
        """
        cursor.execute(create_sql)
        
        # Create index for better search performance
        cursor.execute(f"CREATE INDEX idx_keyword ON {table_name}(keyword)")
        
        connection.commit()
        print(f"✓ Created table '{table_name}' with index")
    except pyodbc.Error as e:
        connection.rollback()
        print(f"❌ Failed to create table: {e}")
        raise
    finally:
        cursor.close()


def populate_knowledge_base(connection: pyodbc.Connection, table_name: str) -> None:
    """Populate the knowledge_base table with articles."""
    cursor = connection.cursor()
    
    articles = [
        ("return", "Return Policy: Items can be returned within 30 days of delivery. Visit our returns portal or contact support to initiate a return."),
        ("shipping", "Shipping Information: Standard shipping takes 5-7 business days. Express shipping takes 2-3 business days. Free shipping on orders over $50."),
        ("refund", "Refund Process: Refunds are processed within 5-10 business days after we receive your return. The refund will be issued to your original payment method."),
        ("tracking", "Tracking Your Order: You can track your order using the tracking number provided in your shipping confirmation email."),
    ]
    
    try:
        insert_sql = f"INSERT INTO {table_name} (keyword, article) VALUES (?, ?)"
        cursor.executemany(insert_sql, articles)
        connection.commit()
        print(f"✓ Inserted {len(articles)} articles into '{table_name}'")
    except pyodbc.Error as e:
        connection.rollback()
        print(f"❌ Failed to insert articles: {e}")
        raise
    finally:
        cursor.close()


def main() -> int:
    """Main execution function."""
    print("=" * 80)
    print("Knowledge Base Table Setup")
    print("=" * 80)
    
    connection_string = os.getenv("MSSQL_CONNECTION_STRING")
    if not connection_string:
        print("❌ Error: MSSQL_CONNECTION_STRING not found in environment")
        print("   Please set this variable in your .env file")
        return 1
    
    table_name = "knowledge_base"
    
    try:
        # Connect to database
        print("\n🔌 Connecting to database...")
        conn = connect_to_database(connection_string)
        
        # Drop existing table
        drop_table_if_exists(conn, table_name)
        
        # Create table
        create_knowledge_base_table(conn, table_name)
        
        # Populate table
        populate_knowledge_base(conn, table_name)
        
        print("\n" + "=" * 80)
        print("✅ Knowledge base setup completed successfully!")
        print("=" * 80)
        
        conn.close()
        return 0
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

