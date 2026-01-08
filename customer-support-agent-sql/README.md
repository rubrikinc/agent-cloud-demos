# Quick Start Guide - MCP-Enabled Customer Support Agent

Get the customer support agent running with MCP server integration in 5 minutes.

## Prerequisites

- Python 3.9+
- Node.js 22.21.1+
- A running MS SQL Server or MS SQL as a Service (AWS, Azure, GCP, etc.)
- ODBC Driver 18 for SQL Server

## Step 1: Create Python Virtual Environment

Create a new Python virtual environment in `.venv`:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

## Step 2: Install Dependencies

### Python Dependencies
```bash
pip install -r requirements.txt
```

### Node.js Dependencies (MCP Server)
```bash
cd MssqlMcp/Node
npm install
npm run build
cd ../..
```

## Step 3: Configure Environment

Create a `.env` file:
```bash
cp .env.template .env
```

Edit `.env` and set your credentials:
```env
# OpenAI Configuration
OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o

# MSSQL Configuration (RECOMMENDED: Use ODBC connection string)
MSSQL_CONNECTION_STRING='Driver={ODBC Driver 18 for SQL Server};Server=your-server;Database=your-db;UID=user;PWD=pass;Connection Timeout=30;TrustServerCertificate=yes;'

# MCP Server Settings
READONLY=false  # Set to "true" for read-only mode
```

### MCP Server Authentication Priority

The MCP server uses a **three-tier priority system** for database authentication:

1. **Priority 1: ODBC Connection String** (RECOMMENDED)
   - If `MSSQL_CONNECTION_STRING` is set, the MCP server uses it exclusively
   - All connection settings come from the ODBC string
   - `SERVER_NAME`, `DATABASE_NAME`, `CONNECTION_TIMEOUT`, `TRUST_SERVER_CERTIFICATE` are **ignored**
   - `READONLY` is still respected

2. **Priority 2: SQL Server Authentication**
   - If `MSSQL_CONNECTION_STRING` is NOT set, but `SQL_USER` and `SQL_PASSWORD` ARE set
   - Uses `SERVER_NAME`, `DATABASE_NAME`, `SQL_USER`, `SQL_PASSWORD`, `CONNECTION_TIMEOUT`, `TRUST_SERVER_CERTIFICATE`
   - `READONLY` is respected

3. **Priority 3: Azure AD Authentication**
   - If neither ODBC string nor SQL credentials are set
   - Uses `SERVER_NAME`, `DATABASE_NAME`, `CONNECTION_TIMEOUT`, `TRUST_SERVER_CERTIFICATE`
   - Requires interactive browser login
   - `READONLY` is respected

**💡 Tip**: Use Priority 1 (ODBC connection string) for the simplest configuration. All settings are in one place and it's consistent with Python's pyodbc usage.

## Step 4: Set Up Database

### Create a database if needed:

```sql
CREATE DATABASE Customer_Orders_DB;
```

### Create Orders Table
```bash
python setup_orders_database.py --num-orders 1000
```

This creates an `orders` table with 1,000 sample orders.

### Create Knowledge Base Table
```bash
python setup_knowledge_base.py
```

This creates a `knowledge_base` table with customer support articles.

## Step 5: Test MCP Integration

```bash
python test_mcp_integration.py
```

Expected output:
```
✓ MCP server found
✅ Test passed: Successfully listed tables
✅ Test passed: Retrieved 5 orders
✅ Test passed: Found knowledge base article
Passed: 3/3
✅ All tests passed!
```

## Step 6: Run the Agent

```bash
python customer_support_agent.py
```

Expected output:
```
================================================================================
Customer Support Agent
================================================================================

Testing the agent with a sample query...

Agent response: Order ORD-00001:
  Status: shipped
  Tracking: 1Z999AA10123456784
  Estimated Delivery: 2025-11-25
```

## Example Queries

### Check Order Status
```python
from customer_support_agent import create_customer_support_agent

agent = create_customer_support_agent()

result = agent.invoke({
    "messages": [("user", "What's the status of order ORD-00001?")]
})

print(result['messages'][-1].content)
```

### Search Knowledge Base
```python
result = agent.invoke({
    "messages": [("user", "What's your return policy?")]
})

print(result['messages'][-1].content)
```

### Process Refund (⚠️ Modifies Database)
```python
result = agent.invoke({
    "messages": [("user", "I need to refund order ORD-00001 because the item was damaged")]
})

print(result['messages'][-1].content)
```

## Environment Variables Reference

### Which Variables Are Used by the MCP Server?

The MCP server's behavior depends on which authentication method is active:

#### ✅ When Using ODBC Connection String (Priority 1 - Current Setup)

If `MSSQL_CONNECTION_STRING` is set in your `.env` file:

| Variable | Used? | Notes |
|----------|-------|-------|
| `MSSQL_CONNECTION_STRING` | ✅ Yes | All connection settings come from this ODBC string |
| `READONLY` | ✅ Yes | Controls which tools are available (read-only vs. full access) |
| `SERVER_NAME` | ❌ No | Ignored - server comes from ODBC string |
| `DATABASE_NAME` | ❌ No | Ignored - database comes from ODBC string |
| `SQL_USER` | ❌ No | Ignored - username comes from ODBC string (UID parameter) |
| `SQL_PASSWORD` | ❌ No | Ignored - password comes from ODBC string (PWD parameter) |
| `CONNECTION_TIMEOUT` | ❌ No | Ignored - timeout comes from ODBC string |
| `TRUST_SERVER_CERTIFICATE` | ❌ No | Ignored - TrustServerCertificate comes from ODBC string |

**Example ODBC string with all settings:**
```env
MSSQL_CONNECTION_STRING='Driver={ODBC Driver 18 for SQL Server};Server=myserver.database.windows.net;Database=mydb;UID=myuser;PWD=mypass;Connection Timeout=60;TrustServerCertificate=yes;'
```

#### ✅ When Using SQL Server Authentication (Priority 2)

If `MSSQL_CONNECTION_STRING` is NOT set, but `SQL_USER` and `SQL_PASSWORD` ARE set:

| Variable | Used? | Notes |
|----------|-------|-------|
| `SERVER_NAME` | ✅ Yes | Database server hostname |
| `DATABASE_NAME` | ✅ Yes | Database name |
| `SQL_USER` | ✅ Yes | SQL Server username |
| `SQL_PASSWORD` | ✅ Yes | SQL Server password |
| `CONNECTION_TIMEOUT` | ✅ Yes | Connection timeout in seconds (default: 30) |
| `TRUST_SERVER_CERTIFICATE` | ✅ Yes | Whether to trust self-signed certificates (default: false) |
| `READONLY` | ✅ Yes | Controls which tools are available |

**Example configuration:**
```env
SERVER_NAME=myserver.database.windows.net
DATABASE_NAME=mydb
SQL_USER=myuser
SQL_PASSWORD=mypass
CONNECTION_TIMEOUT=60
TRUST_SERVER_CERTIFICATE=true
READONLY=false
```

#### ✅ When Using Azure AD Authentication (Priority 3)

If neither `MSSQL_CONNECTION_STRING` nor `SQL_USER`/`SQL_PASSWORD` are set:

| Variable | Used? | Notes |
|----------|-------|-------|
| `SERVER_NAME` | ✅ Yes | Azure SQL server hostname |
| `DATABASE_NAME` | ✅ Yes | Database name |
| `CONNECTION_TIMEOUT` | ✅ Yes | Connection timeout in seconds (default: 30) |
| `TRUST_SERVER_CERTIFICATE` | ✅ Yes | Whether to trust self-signed certificates (default: false) |
| `READONLY` | ✅ Yes | Controls which tools are available |

**Example configuration:**
```env
SERVER_NAME=myserver.database.windows.net
DATABASE_NAME=mydb
CONNECTION_TIMEOUT=60
TRUST_SERVER_CERTIFICATE=false
READONLY=false
```

**Note**: This method requires interactive browser login when the MCP server starts.

### How to Switch Authentication Methods

**To use ODBC (Recommended):**
1. Set `MSSQL_CONNECTION_STRING` in `.env`
2. Comment out or remove `SQL_USER` and `SQL_PASSWORD`

**To use SQL Server Authentication:**
1. Comment out or remove `MSSQL_CONNECTION_STRING`
2. Set `SERVER_NAME`, `DATABASE_NAME`, `SQL_USER`, `SQL_PASSWORD`

**To use Azure AD:**
1. Comment out or remove `MSSQL_CONNECTION_STRING`
2. Comment out or remove `SQL_USER` and `SQL_PASSWORD`
3. Set `SERVER_NAME` and `DATABASE_NAME`

## Troubleshooting

### "MCP server not found"
**Solution**: Build the MCP server
```bash
cd MssqlMcp/Node
npm run build
```

### "knowledge_base table not found"
**Solution**: Create the table
```bash
python setup_knowledge_base.py
```

### "Connection failed"
**Solution**: Check your connection string in `.env`
```bash
# Test connection
python -c "import pyodbc; import os; from dotenv import load_dotenv; load_dotenv(); pyodbc.connect(os.getenv('MSSQL_CONNECTION_STRING'))"
```

**Solution**: Verify which authentication method is being used
```bash
# Check MCP server logs in stderr output
python test_mcp_integration.py
# Look for one of these messages:
# "[MCP Server] Using ODBC connection string for SQL authentication"
# "[MCP Server] Using SQL Server authentication for user: <username>"
# "[MCP Server] Using Azure AD Interactive Browser authentication"
```

### "No valid response from MCP server"
**Solution**: Check Node.js is installed
```bash
node --version  # Should be 22.21.1+
```

### "MCP server call timed out"
**Solution**: Check database connectivity
**Solution**: Increase timeout in `call_mcp_tool()`
**Solution**: Increase `Connection Timeout` in your ODBC connection string or `CONNECTION_TIMEOUT` variable

### "Tool 'update_data' not found" or "Tool 'insert_data' not found"
**Solution**: Check if `READONLY=true` in your `.env` file
- When `READONLY=true`, only read-only tools are available: `read_data`, `list_table`, `describe_table`
- When `READONLY=false`, all tools are available including: `insert_data`, `update_data`, `create_table`, `drop_table`
- The `READONLY` setting is **always respected** regardless of which authentication method you use

## Architecture Overview

```
┌─────────────────────────────────────────┐
│   Customer Support Agent (Python)       │
│   ┌─────────────────────────────────┐   │
│   │ get_order_status()              │   │
│   │ search_knowledge_base()         │   │
│   │ refund_order()                  │   │
│   └─────────────┬───────────────────┘   │
└─────────────────┼───────────────────────┘
                  │ JSON-RPC 2.0 (stdio)
                  ▼
┌─────────────────────────────────────────┐
│   MCP Server (Node.js)                  │
│   ┌─────────────────────────────────┐   │
│   │ read_data                       │   │
│   │ update_data                     │   │
│   │ insert_data                     │   │
│   │ list_table                      │   │
│   └─────────────┬───────────────────┘   │
└─────────────────┼───────────────────────┘
                  │ SQL Queries
                  ▼
┌─────────────────────────────────────────┐
│   MSSQL Database                        │
│   ┌─────────────────────────────────┐   │
│   │ orders                          │   │
│   │ knowledge_base                  │   │
│   └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Next Steps

1. **Explore the code**: Review `customer_support_agent.py` to understand the implementation
2. **Read the docs**: Check out `MCP_INTEGRATION_README.md` for detailed documentation
3. **Add more data**: Populate the database with more orders and articles
4. **Customize tools**: Modify the tools to fit your specific use case
5. **Add governance**: Implement approval workflows for sensitive operations

## Resources

- [MCP Integration README](./MCP_INTEGRATION_README.md) - Detailed documentation
- [Refactoring Summary](./REFACTORING_SUMMARY.md) - What changed and why
- [Database Setup Guide](./DATABASE_SETUP_GUIDE.md) - Database configuration
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the test output: `python test_mcp_integration.py`
3. Check MCP server logs in stderr output
4. Verify database connectivity with validation queries

## What's Different from Mock Implementation?

| Feature | Mock (Before) | MCP (After) |
|---------|---------------|-------------|
| Data Source | Hardcoded dicts | MSSQL Database |
| Order Status | 3 mock orders | 1,000+ real orders |
| Knowledge Base | 4 hardcoded articles | Database table |
| Refunds | Mock message | Real database update |
| Offline Mode | ✅ Works | ❌ Requires database |
| Fallback Behavior | ✅ Uses mock data | ❌ Fails with error message |
| Production Ready | ❌ No | ✅ Yes |

## Performance

Typical latency per tool call:
- **get_order_status**: 100-300ms
- **search_knowledge_base**: 100-300ms
- **refund_order**: 150-400ms

Latency includes:
- Subprocess spawn (~50ms)
- Database query execution
- JSON serialization/deserialization

## Security

The MCP integration includes:
- ✅ SQL injection prevention
- ✅ Parameterized queries
- ✅ Query validation
- ✅ Result sanitization
- ✅ Timeout protection

---

**Ready to go?** Run `python customer_support_agent.py` and start chatting with your agent! 🚀

