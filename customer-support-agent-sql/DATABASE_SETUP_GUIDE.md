# MSSQL Orders Database Setup Guide

This guide provides instructions for setting up and populating the MSSQL orders database for testing the customer support agent.

## Prerequisites

### 1. Install Required Software

**ODBC Driver 18 for SQL Server:**
- **Windows:** Download from [Microsoft Download Center](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- **macOS:** `brew install msodbcsql18`
- **Linux:** Follow [Microsoft's installation guide](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)

### 2. Install Python Dependencies

```bash
cd customer-support-agent-sql
pip install -r requirements.txt
```

**Note:** The script uses `tqdm` for a visual progress bar that shows real-time insertion progress with percentage complete, rate, and estimated time remaining.

### 3. Configure Environment Variables

Create a `.env` file in the `customer-support-agent-sql` directory:

```bash
cp .env.template .env
```

Edit `.env` and set your MSSQL connection string:

```env
MSSQL_CONNECTION_STRING='Driver={ODBC Driver 18 for SQL Server};Server=<server>;Database=<database-name>;Connection Timeout=30;TrustServerCertificate=yes;LongAsMax=yes;UID=<username>;PWD=<password>;'
```

## Database Schema

The script creates an `orders` table with the following schema:

```sql
CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,      -- Format: ORD-00001 to ORD-99999
    status VARCHAR(20) NOT NULL,           -- shipped, processing, canceled, returned, refunded, delivered
    tracking VARCHAR(50) NULL,             -- Format: 1Z999AA10XXXXXXXXX (UPS-style)
    estimated_delivery DATE NOT NULL,      -- order_date + 1-15 days
    order_date DATE NOT NULL               -- Starting 3 years ago, clustered realistically
);

-- Indexes for performance
CREATE INDEX idx_order_date ON orders(order_date);
CREATE INDEX idx_status ON orders(status);
CREATE INDEX idx_tracking ON orders(tracking);
```

## Usage

### Basic Usage (100,000 orders)

```bash
python setup_orders_database.py
```

### Custom Number of Orders

```bash
# Generate 50,000 orders
python setup_orders_database.py --num-orders 50000

# Generate 250,000 orders
python setup_orders_database.py --num-orders 250000
```

### Preserve Existing Table

By default, the script drops and recreates the table. To preserve existing data:

```bash
python setup_orders_database.py --no-drop
```

### Custom Batch Size

Adjust the batch size for inserts (default: 1,000):

```bash
python setup_orders_database.py --batch-size 2000
```

### Custom Table Name

```bash
python setup_orders_database.py --table-name customer_orders
```

### Full Custom Configuration

```bash
python setup_orders_database.py \
    --num-orders 250000 \
    --batch-size 5000 \
    --table-name customer_orders \
    --no-drop
```

## Expected Output

```
================================================================================
MSSQL Orders Database Setup
================================================================================
Configuration:
  - Orders to generate: 100,000
  - Batch size: 1,000
  - Table name: orders
  - Drop existing table: True
================================================================================

🔌 Connecting to database...
✓ Connected successfully
✓ Dropped existing table 'orders'
✓ Created table 'orders' with indexes

📊 Generating 100,000 orders...
📅 Calculating order dates...
Inserting orders:  45%|████████████▌             | 45.0k/100k [00:05<00:06, 8.65korders/s]

================================================================================
✅ DATABASE SETUP COMPLETE
================================================================================
Total orders inserted: 100,000
Time elapsed: 11.28 seconds
Average rate: 8,869 orders/sec
Date range: 2022-11-16 to 2025-11-10
Date span: 1090 days
================================================================================

✓ Database connection closed
```

**Note:** The progress bar updates in real-time, showing:
- Percentage complete (0-100%)
- Visual progress bar
- Current/total orders with thousands separator (e.g., 45.0k/100k)
- Elapsed time and estimated time remaining
- Insertion rate (orders per second)

## Data Validation Queries

After running the setup script, validate the data using these SQL queries:

### 1. Verify Row Count

```sql
SELECT COUNT(*) as total_orders FROM orders;
```

Expected: 100,000 (or your specified number)

### 2. Check Date Range

```sql
SELECT 
    MIN(order_date) as earliest_order,
    MAX(order_date) as latest_order,
    DATEDIFF(day, MIN(order_date), MAX(order_date)) as days_span
FROM orders;
```

Expected: ~3 years (1095 days) of data

### 3. Verify Status Distribution

```sql
SELECT 
    status, 
    COUNT(*) as count,
    CAST(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders) AS DECIMAL(5,2)) as percentage
FROM orders 
GROUP BY status 
ORDER BY count DESC;
```

Expected: Roughly equal distribution across all 6 statuses (~16.67% each)

### 4. Sample Records

```sql
SELECT TOP 10 * FROM orders ORDER BY order_id;
```

### 5. Check for Duplicates

```sql
SELECT order_id, COUNT(*) as duplicate_count
FROM orders 
GROUP BY order_id 
HAVING COUNT(*) > 1;
```

Expected: No results (no duplicates)

### 6. Verify Tracking Number Format

```sql
SELECT TOP 10 order_id, tracking 
FROM orders 
WHERE tracking NOT LIKE '1Z999AA10%';
```

Expected: No results (all tracking numbers follow the pattern)

### 7. Check Delivery Date Logic

```sql
SELECT TOP 10
    order_id,
    order_date,
    estimated_delivery,
    DATEDIFF(day, order_date, estimated_delivery) as days_to_delivery
FROM orders
WHERE DATEDIFF(day, order_date, estimated_delivery) NOT BETWEEN 1 AND 15;
```

Expected: No results (all delivery dates are 1-15 days after order date)

### 8. Orders by Date (Check Clustering)

```sql
SELECT 
    order_date,
    COUNT(*) as orders_per_day
FROM orders
GROUP BY order_date
ORDER BY order_date
LIMIT 20;
```

Expected: 250-300 orders per day (realistic clustering)

## Troubleshooting

### Connection Errors

**Error:** `[Microsoft][ODBC Driver 18 for SQL Server]SSL Provider: The certificate chain was issued by an authority that is not trusted.`

**Solution:** Add `TrustServerCertificate=yes` to your connection string (already included in template)

### ODBC Driver Not Found

**Error:** `[Microsoft][ODBC Driver Manager] Data source name not found and no default driver specified`

**Solution:** Install ODBC Driver 18 for SQL Server (see Prerequisites)

### Permission Errors

**Error:** `CREATE TABLE permission denied`

**Solution:** Ensure your database user has CREATE TABLE and INSERT permissions

### Memory Issues

**Error:** `MemoryError` when generating large datasets

**Solution:** Reduce batch size: `--batch-size 500`

## Performance Tips

1. **Batch Size:** Default 1,000 is optimal for most scenarios. Increase to 5,000 for faster inserts on powerful servers.

2. **Network Latency:** If connecting to a remote database, larger batch sizes reduce round trips.

3. **Indexes:** The script creates indexes after table creation. For very large datasets (>1M rows), consider creating indexes after data insertion.

4. **Expected Performance:**
   - Local database: 8,000-15,000 orders/sec
   - Remote database: 2,000-5,000 orders/sec
   - 100,000 orders: 10-50 seconds depending on network

## Next Steps

After setting up the database:

1. **Test the customer support agent** with real database queries
2. **Update `customer_support_agent.py`** to query the MSSQL database instead of mock data
3. **Run validation queries** to ensure data integrity
4. **Create additional test scenarios** with specific order patterns

## Support

For issues or questions:
- Check the troubleshooting section above
- Review the `.env.template` file for connection string examples
- Verify ODBC driver installation: `odbcinst -j` (Linux/macOS) or check ODBC Data Sources (Windows)

