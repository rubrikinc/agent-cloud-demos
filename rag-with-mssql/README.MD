# Agentic RAG with SQL Server Vector Store

This project implements an **Agentic Retrieval Augmented Generation (RAG)** system using LangChain, LangGraph, and SQL Server (or Azure SQL) as a vector store. The agent intelligently decides when to retrieve information from a vector database, evaluates document relevance, and generates contextual responses based on Lilian Weng's blog posts about LLM agents, prompt engineering, and adversarial attacks.

## Overview

The `agentic-rag.py` script demonstrates an advanced RAG implementation that:
- Uses **LangGraph** to create an agentic workflow with decision-making capabilities
- Stores document embeddings in **SQL Server or Azure SQL** using the native vector type
- Implements **document relevance grading** to ensure high-quality responses
- Supports **query rewriting** to improve retrieval results
- Provides **tool-based operations** for managing the vector store

This implementation is based on the [LangGraph Agentic RAG tutorial](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_agentic_rag/) but adapted to use the `langchain_sqlserver` library for SQL Server integration.

### Rubrik Agent Cloud Integration

This agentic RAG implementation is specifically designed as a **demonstration platform for Rubrik's Agent Cloud and Agent Rewind capabilities**. As AI agents become increasingly autonomous and are granted permissions to perform operational tasks—such as database management, infrastructure provisioning, or data manipulation—the risk of unintended consequences grows significantly. An agent making a well-intentioned but incorrect decision can result in data loss, service disruption, or compliance violations.

**Rubrik Agent Rewind** addresses this critical challenge by providing a safety net for agentic operations. This demo showcases how Rubrik's technology enables organizations to:
- **Recover from agent mistakes**: Quickly restore databases and data to a point-in-time before an agent performed a destructive operation
- **Build confidence in agent deployment**: Deploy autonomous agents with greater assurance, knowing that mistakes can be reversed
- **Demonstrate governance and control**: Show customers how to maintain operational safety while leveraging the efficiency gains of AI agents
- **Enable safe experimentation**: Allow agents to operate with elevated permissions in controlled environments, with the ability to roll back any unintended changes

This demo intentionally includes destructive operations (table deletion) to provide a realistic scenario where Agent Rewind's value becomes immediately apparent—transforming a potentially catastrophic agent error into a recoverable event that takes seconds to remediate.

> [!WARNING]
> **CRITICAL SAFETY NOTICE - READ BEFORE USE**
>
> This AI agent has **destructive capabilities** and can permanently delete tables and data from Microsoft SQL Server databases. The agent is equipped with a `delete_blog_posts_table` tool that, when invoked, will drop the specified table and all its contents from the database.
>
> **Key Safety Considerations:**
> - ⚠️ **Production Risk**: Exercise extreme caution when running this agent in production or near-production environments
> - 🔒 **Permissions**: The agent requires `db_owner` role or equivalent permissions, giving it broad database access
> - 🎯 **Intentional Design**: The delete functionality is deliberately included to demonstrate Rubrik Agent Rewind's recovery capabilities
> - 💾 **Backup Requirements**: Ensure Rubrik or equivalent backup/recovery mechanisms are configured and tested before granting the agent delete permissions
> - 🧪 **Demo Environment**: For customer demonstrations, use isolated demo databases with non-critical data
> - 📋 **Recovery Plan**: Have a documented recovery procedure in place before running the agent with the `-d` (delete) flag
>
> **For Sales Engineers**: When demonstrating this capability to customers, emphasize that the destructive operations showcase the "before Agent Rewind" scenario—highlighting the business risk that Rubrik Agent Rewind mitigates. Always perform demonstrations in controlled environments with active Rubrik protection enabled.

## Architecture

The agent workflow includes:
1. **Agent Node**: Decides whether to retrieve documents or answer directly
2. **Retrieval Node**: Fetches relevant documents from the SQL Server vector store
3. **Grading Node**: Evaluates document relevance to the query
4. **Rewrite Node**: Reformulates queries when documents aren't relevant
5. **Generate Node**: Produces final answers using retrieved context

## Prerequisites

Before running this project, ensure you have:

### System Requirements
- **Python 3.8+** installed on your system
- **ODBC Driver 18 for SQL Server** installed
  - Windows: Download from [Microsoft ODBC Driver for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
  - macOS: `brew install msodbcsql18`
  - Linux: Follow [Microsoft's installation guide](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)

### Database Requirements
- **SQL Server 2025 CTP** (with native vector support) or **Azure SQL Database**
  - SQL Server 2025 introduces the native [Vector data type](https://learn.microsoft.com/sql/t-sql/data-types/vector-data-type?view=azuresqldb-current&tabs=csharp)
  - For Azure SQL: See [Try Azure SQL Database for free](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-offer?view=azuresql)
- Database user with permissions to create, read, and delete tables

### API Requirements
- **OpenAI API key** with access to:
  - Chat completion models (e.g., `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`)
  - Embedding models (e.g., `text-embedding-3-small`, `text-embedding-3-large`)

## Installation

### 1. Clone the Repository

First, create a directory for Rubrik projects and clone the repository:

```bash
# Create a rubrik directory in your home folder
mkdir -p ~/rubrik

# Navigate to the rubrik directory
cd ~/rubrik

# Clone the agent-cloud-demos repository
git clone https://github.com/rubrikinc/agent-cloud-demos.git

# Navigate to the rag-with-mssql project directory
cd agent-cloud-demos/rag-with-mssql
```

**For Windows users (PowerShell):**
```powershell
# Create a rubrik directory in your home folder
New-Item -ItemType Directory -Force -Path "$HOME\rubrik"

# Navigate to the rubrik directory
cd "$HOME\rubrik"

# Clone the agent-cloud-demos repository
git clone https://github.com/rubrikinc/agent-cloud-demos.git

# Navigate to the rag-with-mssql project directory
cd agent-cloud-demos\rag-with-mssql
```

You should now be in the `rag-with-mssql` directory, ready to proceed with the remaining installation steps.

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv .venv
```

Activate the virtual environment:
- **Windows**: `.venv\Scripts\activate`
- **macOS/Linux**: `source .venv/bin/activate`

### 3. Install Dependencies

```bash
pip install -U -r requirements.txt
```

This will install all required packages including:
- `langchain` and `langchain-community` - Core LangChain framework
- `langchain-sqlserver` - SQL Server vector store integration
- `langchain-openai` - OpenAI model integrations
- `langgraph` - Agent workflow orchestration
- `sqlalchemy` and `pyodbc` - Database connectivity
- `azure-identity` - Azure authentication (for Azure SQL)
- `python-dotenv` - Environment variable management
- Additional utilities: `beautifulsoup4`, `tiktoken`, `pydantic`, `pypdf`

## Configuration

### 1. Set Up SQL Server Database

#### For Azure SQL Database:

1. **Enable SQL Authentication** (if using username/password):
   - In Azure Portal, navigate to your SQL Server
   - Under "Settings" → "Azure Active Directory", configure authentication

2. **Create a database user**:
   ```sql
   CREATE LOGIN <login> WITH PASSWORD = '<password>';
   GO

   USE [<your-database>];
   GO

   CREATE USER <user> FROM LOGIN <login>;
   GO
   ```

3. **Grant necessary permissions**:
   ```sql
   USE [<your-database>];
   GO

   ALTER ROLE db_owner ADD MEMBER [<user>];
   GO
   ```

4. **Configure firewall rules**:
   - In Azure Portal, add your client IP address to the SQL Server firewall rules

#### For On-Premises SQL Server:

1. Enable SQL Server Authentication (if not using Windows Authentication)
2. Create a database and user with the `db_owner` role.
3. Ensure SQL Server is configured to accept remote connections 

### 2. Create Environment Configuration File

The script uses environment-specific configuration files. Create a configuration file based on the template:

```bash
cp .env.template .env.demo
```

Edit `.env.demo` (or your chosen environment name) with your actual configuration:

```bash
# OpenAI Configuration
OPENAI_API_KEY="sk-your-actual-openai-api-key"
OPENAI_ENDPOINT="https://api.openai.com/v1"
OPENAI_MODEL="gpt-4o"
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

# Application Configuration
USER_AGENT="WebBaseLoader"
TABLE_NAME="lilian_weng_blog_posts"

# SQL Server Connection String (choose one option below)
```

#### Connection String Options:

**Option 1: SQL Server with SQL Authentication**
```bash
MSSQL_CONNECTION_STRING='Driver={ODBC Driver 18 for SQL Server};Server=<server>;Database=<database-name>;Connection Timeout=30;TrustServerCertificate=yes;LongAsMax=yes;UID=<username>;PWD=<password>;'
```

**Option 2: SQL Server with Windows Authentication**
```bash
MSSQL_CONNECTION_STRING='Driver={ODBC Driver 18 for SQL Server};Server=<server>;Database=<database-name>;Connection Timeout=30;TrustServerCertificate=yes;LongAsMax=yes;Trusted_Connection=yes;'
```

**Option 3: Azure SQL with Entra ID Authentication**
```bash
MSSQL_CONNECTION_STRING='Driver={ODBC Driver 18 for SQL Server};Server=<your-server-name>.database.windows.net;Database=<database-name>;Connection Timeout=60;LongAsMax=yes;Authentication=ActiveDirectoryIntegrated;'
```

### 3. Environment Variables Explained

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key for authentication | `sk-proj-...` |
| `OPENAI_ENDPOINT` | OpenAI API endpoint URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Chat completion model to use | `gpt-4o`, `gpt-4-turbo` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model for vector generation | `text-embedding-3-small` |
| `TABLE_NAME` | SQL table name for vector storage | `lilian_weng_blog_posts` |
| `MSSQL_CONNECTION_STRING` | ODBC connection string for SQL Server | See options above |

## Usage

The `agentic-rag.py` script supports three main operations:

### 1. Create and Populate Vector Store

This operation downloads blog posts from Lilian Weng's website, splits them into chunks, generates embeddings, and stores them in SQL Server:

```bash
python agentic-rag.py --env demo -c
```

**What happens:**
- Loads documents from three blog post URLs:
  - LLM Powered Autonomous Agents
  - Prompt Engineering Guide
  - Adversarial Attacks on LLMs
- Splits documents into chunks (100 tokens with 50 token overlap)
- Generates embeddings using OpenAI's embedding model
- Creates the vector store table in SQL Server
- Stores approximately 150+ document chunks with embeddings

**Expected output:**
```
Loading environment variables from .env.demo...
Loaded environment: demo
Connecting to SQL Server database...
Connected to database: <database-name> on server: <server-name>
Loading documents...
Splitting documents...
Configuring vector store...
Adding documents...
Creating retriever tool...
...
```

### 2. Query the Vector Store (Agentic RAG)

Run the agent to answer questions using the stored documents:

```bash
python agentic-rag.py --env demo
```

**What happens:**
- Verifies the vector store table exists
- Initializes the agentic workflow graph
- Processes the default question: *"What does Lilian Weng say about the types of agent memory?"*
- Agent decides whether to retrieve documents
- Retrieves relevant documents from SQL Server
- Grades document relevance
- Generates a concise answer (max 3 sentences)

**Expected output:**
```
Loading environment variables from .env.demo...
Connected to database: <database-name> on server: <server-name>
Verifying document store table exists...
Verified: lilian_weng_blog_posts table exists
Configuring vector store...
Creating retriever tool...
Running agent in QUERY mode...
Question: What does Lilian Weng say about the types of agent memory?
---CALL AGENT---
---CHECK RELEVANCE---
---DECISION: DOCS RELEVANT---
---GENERATE---
Output from node 'generate':
---
'Lilian Weng discusses three types of agent memory: sensory memory, short-term memory, and long-term memory...'
```

### 3. Delete the Vector Store Table

Remove the vector store table from the database:

```bash
python agentic-rag.py --env demo -d
```

**What happens:**
- Verifies the table exists
- Agent processes a deletion request
- Executes the `delete_blog_posts_table` tool
- Drops the table from SQL Server

**Expected output:**
```
Running agent in DELETE mode...
Question: Please delete the 'lilian_weng_blog_posts' table...
---CALL AGENT---
---DELETE TABLE OPERATION REQUESTED---
Connecting to SQL Server database...
Table 'lilian_weng_blog_posts' successfully deleted
```

### Command-Line Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `--env` | N/A | **Required**. Environment name (loads `.env.<name>` file) |
| `--create_vector_store` | `-c` | Create and populate the vector store table |
| `--delete` | `-d` | Delete the vector store table |

## How It Works

### Agentic Workflow

The script implements a sophisticated multi-node workflow using LangGraph:

```
START → Agent → [Retrieve or END]
         ↓
      Retrieve → Grade Documents → [Generate or Rewrite]
         ↓                              ↓
      Generate → END              Rewrite → Agent
```

1. **Agent Node**: Uses GPT-4 to decide if retrieval is needed
2. **Retrieve Node**: Queries SQL Server vector store for relevant documents
3. **Grade Documents**: Evaluates if retrieved documents are relevant
4. **Generate**: Creates answer using relevant documents
5. **Rewrite**: Reformulates query if documents aren't relevant, then loops back

### Vector Store Implementation

- Uses SQL Server's native **vector data type** (SQL Server 2025+)
- Embeddings are 1536-dimensional vectors (OpenAI `text-embedding-3-small`)
- Supports similarity search using vector operations
- Stores document content, metadata, and embeddings in a single table

### Document Processing

- **Chunking**: Uses `RecursiveCharacterTextSplitter` with tiktoken encoding
- **Chunk size**: 100 tokens
- **Overlap**: 50 tokens (ensures context continuity)
- **Source**: Web-based document loader for blog posts

## Expected Behavior

### Successful Query Example

**Input**: "What does Lilian Weng say about the types of agent memory?"

**Agent Workflow**:
1. Agent decides to retrieve documents
2. Retrieves 4-5 relevant chunks from vector store
3. Grades documents as relevant
4. Generates concise answer

**Output**:
> "Lilian Weng describes three types of agent memory: sensory memory (learning embedding representations), short-term memory (in-context learning with limited context window), and long-term memory (external vector store for fast retrieval)."

### Query Rewrite Example

If initial retrieval returns irrelevant documents:
1. Agent retrieves documents
2. Grader marks documents as not relevant
3. Query is rewritten for better semantic matching
4. Agent retrieves again with improved query

## Troubleshooting

### Common Issues

#### 1. ODBC Driver Not Found
**Error**: `[Microsoft][ODBC Driver Manager] Data source name not found`

**Solution**: Install ODBC Driver 18 for SQL Server
```bash
# macOS
brew install msodbcsql18

# Verify installation
odbcinst -q -d
```

#### 2. Connection Timeout
**Error**: `Connection Timeout Expired`

**Solutions**:
- Verify SQL Server is running and accessible
- Check firewall rules (Azure SQL or on-premises)
- Increase `Connection Timeout` in connection string
- For Azure SQL: Add your IP to firewall rules

#### 3. Table Does Not Exist
**Error**: `ERROR: Required document store table does not exist`

**Solution**: Run the create operation first:
```bash
python agentic-rag.py --env demo -c
```

#### 4. Authentication Failed
**Error**: `Login failed for user`

**Solutions**:
- Verify username/password in connection string
- Check SQL Server authentication mode
- For Azure SQL: Verify Entra ID authentication is configured
- Ensure user has necessary permissions

#### 5. OpenAI API Errors
**Error**: `AuthenticationError` or `RateLimitError`

**Solutions**:
- Verify `OPENAI_API_KEY` is correct
- Check API quota and billing
- Ensure model names are correct (`gpt-4o`, not `gpt-4.1`)

#### 6. Vector Type Not Supported
**Error**: `Invalid column type 'vector'`

**Solution**: Ensure you're using SQL Server 2025 CTP or Azure SQL Database with vector support enabled

### Debug Mode

To enable detailed logging, uncomment these lines in `agentic-rag.py`:

```python
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
```

## Examples

### Example 1: Complete Workflow

```bash
# 1. Create environment file
cp .env.template .env.prod
# Edit .env.prod with your configuration

# 2. Create and populate vector store
python agentic-rag.py --env prod -c

# 3. Query the agent
python agentic-rag.py --env prod

# 4. Clean up (optional)
python agentic-rag.py --env prod -d
```

### Example 2: Multiple Environments

```bash
# Development environment
python agentic-rag.py --env dev -c
python agentic-rag.py --env dev

# Production environment
python agentic-rag.py --env prod -c
python agentic-rag.py --env prod
```

### Example 3: Custom Questions

To ask custom questions, modify line 478 in `agentic-rag.py`:

```python
# Change this line:
question = "What does Lilian Weng say about the types of agent memory?"

# To your custom question:
question = "What are the challenges in prompt engineering?"
```

## Advanced Configuration

### Customizing Chunk Size

Modify lines 148-150 in `agentic-rag.py`:

```python
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=200,  # Increase for larger chunks
    chunk_overlap=100  # Increase overlap for better context
)
```

### Using Different Embedding Models

Update your `.env` file:

```bash
# For higher quality (but more expensive)
OPENAI_EMBEDDING_MODEL="text-embedding-3-large"
```

**Note**: If changing embedding models, you must:
1. Delete the existing vector store: `python agentic-rag.py --env demo -d`
2. Update `embedding_length` in line 164 of `agentic-rag.py` (1536 for small, 3072 for large)
3. Recreate the vector store: `python agentic-rag.py --env demo -c`

### Adding Custom Documents

Modify lines 137-141 in `agentic-rag.py`:

```python
urls = [
    "https://your-custom-url-1.com",
    "https://your-custom-url-2.com",
    # Add more URLs
]
```

## Performance Considerations

- **Initial Setup**: Creating the vector store takes 2-5 minutes (downloads, processes, and embeds ~150 chunks)
- **Query Time**: Typical queries complete in 5-15 seconds
- **Embedding Costs**: ~$0.02 per 1M tokens (text-embedding-3-small)
- **LLM Costs**: Varies by model (GPT-4o: ~$5/$15 per 1M tokens input/output)

## Security Best Practices

1. **Never commit `.env.*` files** to version control
2. **Use environment-specific configurations** for dev/staging/prod
3. **Rotate API keys regularly**
4. **Use Azure Managed Identity** for Azure SQL when possible
5. **Implement least-privilege access** for database users
6. **Enable SSL/TLS** for database connections (included in connection strings)

## Additional Resources

- [LangChain SQL Server Integration](https://github.com/langchain-ai/langchain-azure/tree/main/libs/sqlserver)
- [LangGraph Agentic RAG Tutorial](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_agentic_rag/)
- [SQL Server 2025 Vector Type Documentation](https://learn.microsoft.com/sql/t-sql/data-types/vector-data-type)
- [Azure SQL Database Documentation](https://learn.microsoft.com/en-us/azure/azure-sql/database/)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)

## Contributing

When modifying this project:
1. Test changes with both Azure SQL and on-premises SQL Server
2. Update this README with any new configuration requirements
3. Ensure backward compatibility with existing `.env` files
4. Document any new dependencies in `requirements.txt`

## License

This project is part of the Rubrik agent-cloud-demos repository. Please refer to the repository's license file for licensing information.