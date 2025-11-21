"""
MSSQL Orders Database Setup Script

This script creates and populates an MSSQL database with synthetic order data
for testing the customer support agent. It generates 100,000 orders (configurable)
spanning 3 years with realistic date clustering and tracking numbers.

Usage:
    python setup_orders_database.py [options]

Examples:
    # Generate 100,000 orders (default)
    python setup_orders_database.py
    
    # Generate 50,000 orders
    python setup_orders_database.py --num-orders 50000
    
    # Preserve existing table
    python setup_orders_database.py --no-drop
    
    # Custom batch size
    python setup_orders_database.py --batch-size 2000

Requirements:
    - MSSQL_CONNECTION_STRING environment variable must be set
    - ODBC Driver 18 for SQL Server must be installed
    - pyodbc Python package must be installed
"""

import os
import sys
import time
import random
import argparse
from datetime import datetime, timedelta, date
from typing import List, Tuple, Dict

try:
    import pyodbc
except ImportError:
    print("❌ Error: pyodbc is not installed. Please run: pip install pyodbc")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Error: python-dotenv is not installed. Please run: pip install python-dotenv")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("❌ Error: tqdm is not installed. Please run: pip install tqdm")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

class DatabaseConfig:
    """Configuration for database setup."""

    def __init__(self, connection_string: str, table_name: str = "orders"):
        self.connection_string = connection_string
        self.table_name = table_name


# ============================================================================
# Database Connection Management
# ============================================================================

def connect_to_database(connection_string: str) -> pyodbc.Connection:
    """
    Establish connection to MSSQL database.
    
    Args:
        connection_string: ODBC connection string
    
    Returns:
        pyodbc.Connection: Active database connection
    
    Raises:
        Exception: If connection fails
    """
    try:
        conn = pyodbc.connect(connection_string)
        conn.autocommit = False  # Use transactions for batch inserts
        return conn
    except pyodbc.Error as e:
        print(f"❌ Failed to connect to database: {e}")
        raise


# ============================================================================
# Schema Management
# ============================================================================

def drop_table_if_exists(connection: pyodbc.Connection, table_name: str) -> None:
    """
    Drop table if it exists.
    
    Args:
        connection: Database connection
        table_name: Name of table to drop
    """
    cursor = connection.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        connection.commit()
        print(f"✓ Dropped existing table '{table_name}'")
    except pyodbc.Error as e:
        print(f"⚠️  Warning: Could not drop table: {e}")
        connection.rollback()
    finally:
        cursor.close()


def create_orders_table(connection: pyodbc.Connection, table_name: str) -> None:
    """
    Create orders table with proper schema and indexes.
    
    Args:
        connection: Database connection
        table_name: Name of table to create
    
    Raises:
        Exception: If table creation fails
    """
    cursor = connection.cursor()
    try:
        # Create table
        create_sql = f"""
        CREATE TABLE {table_name} (
            order_id VARCHAR(20) PRIMARY KEY,
            status VARCHAR(20) NOT NULL,
            tracking VARCHAR(50) NULL,
            estimated_delivery DATE NOT NULL,
            order_date DATE NOT NULL
        )
        """
        cursor.execute(create_sql)
        
        # Create indexes for better query performance
        cursor.execute(f"CREATE INDEX idx_order_date ON {table_name}(order_date)")
        cursor.execute(f"CREATE INDEX idx_status ON {table_name}(status)")
        cursor.execute(f"CREATE INDEX idx_tracking ON {table_name}(tracking)")
        
        connection.commit()
        print(f"✓ Created table '{table_name}' with indexes")
    except pyodbc.Error as e:
        connection.rollback()
        print(f"❌ Failed to create table: {e}")
        raise
    finally:
        cursor.close()


# ============================================================================
# Data Generation Functions
# ============================================================================

def generate_order_id(sequence_num: int) -> str:
    """
    Generate order ID in format: ORD-00001 to ORD-999999

    Args:
        sequence_num: Sequential number (1-999999)

    Returns:
        str: Formatted order ID (e.g., "ORD-00001")
    """
    return f"ORD-{sequence_num:05d}"


def generate_tracking_number(sequence_num: int) -> str:
    """
    Generate tracking number in UPS-style format: 1Z999AA10XXXXXXXXX

    Pattern matches the examples in customer_support_agent.py:
    - "1Z999AA10123456784"
    - "1Z999AA10123456785"

    Args:
        sequence_num: Sequential number for uniqueness

    Returns:
        str: Formatted tracking number
    """
    # Start from 123456784 (matching the example in customer_support_agent.py)
    tracking_suffix = 123456784 + sequence_num - 1
    return f"1Z999AA10{tracking_suffix:09d}"


def generate_random_status() -> str:
    """
    Randomly select order status with uniform distribution.

    Status options match those in customer_support_agent.py examples.

    Returns:
        str: Random status value
    """
    statuses = ["shipped", "processing", "canceled", "returned", "refunded", "delivered"]
    return random.choice(statuses)


def calculate_order_dates(total_orders: int) -> List[date]:
    """
    Calculate order dates with realistic clustering.

    Logic:
    - Start date: 3 years (1095 days) before today
    - Every 250-300 orders share the same date (random batch size)
    - Then advance by 1 day

    This creates realistic clustering where multiple orders share the same date,
    mimicking real-world e-commerce patterns.

    Args:
        total_orders: Total number of orders to generate

    Returns:
        list: List of order dates (one per order)
    """
    start_date = datetime.now().date() - timedelta(days=1095)
    order_dates = []
    current_date = start_date
    orders_on_current_date = 0
    orders_per_date = random.randint(250, 300)

    for i in range(total_orders):
        order_dates.append(current_date)
        orders_on_current_date += 1

        # Advance date after N orders
        if orders_on_current_date >= orders_per_date:
            current_date += timedelta(days=1)
            orders_on_current_date = 0
            orders_per_date = random.randint(250, 300)  # New random batch size

    return order_dates


def calculate_estimated_delivery(order_date: date) -> date:
    """
    Calculate estimated delivery date.

    Args:
        order_date: Order creation date

    Returns:
        date: Estimated delivery date (order_date + 1-15 days)
    """
    days_to_delivery = random.randint(1, 15)
    return order_date + timedelta(days=days_to_delivery)


def generate_order_batch(
    start_num: int,
    batch_size: int,
    order_dates: List[date]
) -> List[Tuple[str, str, str, date, date]]:
    """
    Generate a batch of orders.

    Args:
        start_num: Starting order number
        batch_size: Number of orders in batch
        order_dates: Pre-calculated list of order dates

    Returns:
        list: List of tuples (order_id, status, tracking, est_delivery, order_date)
    """
    batch = []
    for i in range(batch_size):
        order_num = start_num + i
        order_id = generate_order_id(order_num)
        status = generate_random_status()
        tracking = generate_tracking_number(order_num)
        order_date = order_dates[order_num - 1]
        estimated_delivery = calculate_estimated_delivery(order_date)

        batch.append((order_id, status, tracking, estimated_delivery, order_date))

    return batch


# ============================================================================
# Data Insertion
# ============================================================================

def insert_orders_batch(
    connection: pyodbc.Connection,
    table_name: str,
    orders_batch: List[Tuple[str, str, str, date, date]]
) -> int:
    """
    Insert a batch of orders using parameterized query.

    Args:
        connection: Database connection
        table_name: Target table name
        orders_batch: List of order tuples

    Returns:
        int: Number of rows inserted

    Raises:
        Exception: If batch insert fails
    """
    cursor = connection.cursor()
    try:
        insert_sql = f"""
        INSERT INTO {table_name}
        (order_id, status, tracking, estimated_delivery, order_date)
        VALUES (?, ?, ?, ?, ?)
        """
        cursor.executemany(insert_sql, orders_batch)
        connection.commit()
        return len(orders_batch)
    except pyodbc.Error as e:
        connection.rollback()
        print(f"❌ Batch insert failed: {e}")
        raise
    finally:
        cursor.close()


def populate_database(
    connection: pyodbc.Connection,
    table_name: str,
    total_orders: int,
    batch_size: int
) -> Dict[str, any]:
    """
    Populate database with generated orders.

    Args:
        connection: Database connection
        table_name: Target table name
        total_orders: Total number of orders to generate
        batch_size: Number of orders per batch

    Returns:
        dict: Summary statistics including:
            - total_inserted: Number of orders inserted
            - elapsed_time: Time taken in seconds
            - start_date: First order date
            - end_date: Last order date
            - date_span_days: Number of days spanned
    """
    print(f"\n📊 Generating {total_orders:,} orders...")

    # Pre-calculate all order dates for consistency
    print("📅 Calculating order dates...")
    order_dates = calculate_order_dates(total_orders)

    start_time = time.time()
    total_inserted = 0

    # Create progress bar with forced updates
    print("\n🔄 Starting batch insertion with progress tracking...\n")

    with tqdm(
        total=total_orders,
        desc="Inserting orders",
        unit=" orders",
        unit_scale=False,
        mininterval=0,
        maxinterval=0,
        miniters=1,
        dynamic_ncols=True,
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n:,}/{total:,} [{elapsed}<{remaining}, {rate_fmt}]"
    ) as pbar:
        # Process in batches
        for batch_start in range(1, total_orders + 1, batch_size):
            batch_end = min(batch_start + batch_size, total_orders + 1)
            current_batch_size = batch_end - batch_start

            # Generate batch
            batch = generate_order_batch(batch_start, current_batch_size, order_dates)

            # Insert batch
            inserted = insert_orders_batch(connection, table_name, batch)
            total_inserted += inserted

            # Update progress bar with explicit refresh
            pbar.update(inserted)
            pbar.refresh()

            # Force stdout flush to ensure display updates
            sys.stdout.flush()

    elapsed_time = time.time() - start_time

    return {
        "total_inserted": total_inserted,
        "elapsed_time": elapsed_time,
        "start_date": order_dates[0],
        "end_date": order_dates[-1],
        "date_span_days": (order_dates[-1] - order_dates[0]).days
    }


# ============================================================================
# Main Execution
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Setup and populate MSSQL orders database for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100,000 orders (default)
  python setup_orders_database.py

  # Generate 50,000 orders
  python setup_orders_database.py --num-orders 50000

  # Preserve existing table
  python setup_orders_database.py --no-drop

  # Custom batch size
  python setup_orders_database.py --batch-size 2000

  # Full custom configuration
  python setup_orders_database.py --num-orders 250000 --batch-size 5000 --table-name customer_orders
        """
    )

    parser.add_argument(
        "--num-orders",
        type=int,
        default=1000,
        help="Number of orders to generate (default: 1000)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for inserts (default: 100)"
    )
    parser.add_argument(
        "--table-name",
        type=str,
        default="orders",
        help="Table name (default: orders)"
    )
    parser.add_argument(
        "--no-drop",
        action="store_true",
        help="Do not drop existing table (default: drop and recreate)"
    )

    return parser.parse_args()


def main() -> int:
    """
    Main execution function.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Parse arguments
    args = parse_arguments()

    # Load environment variables
    load_dotenv()

    connection_string = os.getenv("MSSQL_CONNECTION_STRING")
    if not connection_string:
        print("❌ Error: MSSQL_CONNECTION_STRING not found in environment")
        print("   Please set this variable in your .env file or environment")
        return 1

    # Print configuration
    print("=" * 80)
    print("MSSQL Orders Database Setup")
    print("=" * 80)
    print(f"Configuration:")
    print(f"  - Orders to generate: {args.num_orders:,}")
    print(f"  - Batch size: {args.batch_size:,}")
    print(f"  - Table name: {args.table_name}")
    print(f"  - Drop existing table: {not args.no_drop}")
    print("=" * 80)

    try:
        # Connect to database
        print("\n🔌 Connecting to database...")
        conn = connect_to_database(connection_string)
        print("✓ Connected successfully")

        # Drop table if requested
        if not args.no_drop:
            drop_table_if_exists(conn, args.table_name)

        # Create table
        create_orders_table(conn, args.table_name)

        # Populate database
        summary = populate_database(
            conn,
            args.table_name,
            args.num_orders,
            args.batch_size
        )

        # Print summary
        print("\n" + "=" * 80)
        print("✅ DATABASE SETUP COMPLETE")
        print("=" * 80)
        print(f"Total orders inserted: {summary['total_inserted']:,}")
        print(f"Time elapsed: {summary['elapsed_time']:.2f} seconds")
        print(f"Average rate: {summary['total_inserted']/summary['elapsed_time']:.0f} orders/sec")
        print(f"Date range: {summary['start_date']} to {summary['end_date']}")
        print(f"Date span: {summary['date_span_days']} days")
        print("=" * 80)

        # Close connection
        conn.close()
        print("\n✓ Database connection closed")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

