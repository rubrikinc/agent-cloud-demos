-- ============================================================================
-- MSSQL Orders Database Validation Queries
-- ============================================================================
-- Run these queries after executing setup_orders_database.py to validate
-- that the data was generated correctly.
-- ============================================================================

-- 1. Verify Row Count
-- Expected: 100,000 (or your specified number)
SELECT COUNT(*) as total_orders FROM orders;

-- 2. Check Date Range
-- Expected: ~3 years (1095 days) of data
SELECT 
    MIN(order_date) as earliest_order,
    MAX(order_date) as latest_order,
    DATEDIFF(day, MIN(order_date), MAX(order_date)) as days_span
FROM orders;

-- 3. Verify Status Distribution
-- Expected: Roughly equal distribution across all 6 statuses (~16.67% each)
SELECT 
    status, 
    COUNT(*) as count,
    CAST(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders) AS DECIMAL(5,2)) as percentage
FROM orders 
GROUP BY status 
ORDER BY count DESC;

-- 4. Sample Records
-- View first 10 orders
SELECT TOP 10 * FROM orders ORDER BY order_id;

-- 5. Check for Duplicates
-- Expected: No results (no duplicates)
SELECT order_id, COUNT(*) as duplicate_count
FROM orders 
GROUP BY order_id 
HAVING COUNT(*) > 1;

-- 6. Verify Tracking Number Format
-- Expected: No results (all tracking numbers follow the pattern 1Z999AA10XXXXXXXXX)
SELECT TOP 10 order_id, tracking 
FROM orders 
WHERE tracking NOT LIKE '1Z999AA10%';

-- 7. Check Delivery Date Logic
-- Expected: No results (all delivery dates are 1-15 days after order date)
SELECT TOP 10
    order_id,
    order_date,
    estimated_delivery,
    DATEDIFF(day, order_date, estimated_delivery) as days_to_delivery
FROM orders
WHERE DATEDIFF(day, order_date, estimated_delivery) NOT BETWEEN 1 AND 15;

-- 8. Orders by Date (Check Clustering)
-- Expected: 250-300 orders per day (realistic clustering)
SELECT TOP 20
    order_date,
    COUNT(*) as orders_per_day
FROM orders
GROUP BY order_date
ORDER BY order_date;

-- 9. Orders by Status and Date Range
-- Useful for testing date-based queries
SELECT 
    status,
    COUNT(*) as total_orders,
    MIN(order_date) as earliest,
    MAX(order_date) as latest
FROM orders
GROUP BY status
ORDER BY status;

-- 10. Sample Orders for Each Status
-- Get one example of each status for testing
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY status ORDER BY order_id) as rn
    FROM orders
) t
WHERE rn = 1
ORDER BY status;

-- 11. Recent Orders (Last 30 Days)
-- Test date filtering
SELECT TOP 100
    order_id,
    status,
    tracking,
    order_date,
    estimated_delivery
FROM orders
WHERE order_date >= DATEADD(day, -30, (SELECT MAX(order_date) FROM orders))
ORDER BY order_date DESC;

-- 12. Orders by Month
-- View distribution across months
SELECT 
    YEAR(order_date) as year,
    MONTH(order_date) as month,
    COUNT(*) as orders_count
FROM orders
GROUP BY YEAR(order_date), MONTH(order_date)
ORDER BY year, month;

-- 13. Test Specific Order IDs (from customer_support_agent.py examples)
-- These should exist if you generated at least 12,345 orders
SELECT * FROM orders WHERE order_id IN ('ORD-00001', 'ORD-12345', 'ORD-67890');

-- 14. Index Usage Check
-- Verify indexes were created
SELECT 
    i.name as index_name,
    i.type_desc as index_type,
    c.name as column_name
FROM sys.indexes i
INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.object_id = OBJECT_ID('orders')
ORDER BY i.name, ic.key_ordinal;

-- 15. Table Size and Statistics
-- Check table size and row count
SELECT 
    t.name AS table_name,
    p.rows AS row_count,
    SUM(a.total_pages) * 8 AS total_space_kb,
    SUM(a.used_pages) * 8 AS used_space_kb,
    (SUM(a.total_pages) - SUM(a.used_pages)) * 8 AS unused_space_kb
FROM sys.tables t
INNER JOIN sys.indexes i ON t.object_id = i.object_id
INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE t.name = 'orders'
GROUP BY t.name, p.rows;

