import os, logging, pprint, argparse, struct, sys
from typing import Annotated, Literal, Sequence
from typing_extensions import TypedDict
from urllib.parse import quote_plus
from sqlalchemy import create_engine, inspect, event, MetaData, Table, text
from sqlalchemy.schema import DropTable
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, Field

from dotenv import load_dotenv
parser = argparse.ArgumentParser(description='Run script with different environments')
parser.add_argument("-c", "--create_vector_store", action="store_true",
                    help="Create the vector store table in SQL.")
parser.add_argument("-d", "--delete", action="store_true",
                    help="Delete the vector store table in SQL instead of querying it")
parser.add_argument(
    '--env',
    required=True,
    help='Environment to load. Environments loaded from .env.* files. Environment name is the suffix of the file name. Ex. .env.demo -> -- env air-demo'
)
args = parser.parse_args()
env_file = f'.env.{args.env}'
if os.path.exists(env_file):
  print(f"Loading environment variables from {env_file}...")
  load_dotenv(env_file,override=True)
else:
  print(f"ERROR: Environment file {env_file} not found.")
  sys.exit(1)

from langchain_community.document_loaders import WebBaseLoader
from langchain_sqlserver.vectorstores import SQLServer_VectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools.retriever import create_retriever_tool
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.tools import tool


from langgraph.graph.message import add_messages
from langgraph.prebuilt import tools_condition
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

# logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.ERROR)
# logger = logging.getLogger(__name__)kk
# logger.setLevel(logging.INFO)

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
MSSQL_CONNECTION_STRING = os.getenv("MSSQL_CONNECTION_STRING")
TABLE_NAME = os.getenv("TABLE_NAME")

print(f"Loaded environment: {args.env}")

print("Connecting to SQL Server database...")
engine = create_engine("mssql+pyodbc:///?odbc_connect={}".format(quote_plus(MSSQL_CONNECTION_STRING)))
# @event.listens_for(engine, "do_connect")
# def provide_token(dialect, conn_rec, cargs, cparams):
#     # Retrieve a token from Entra ID
#     token_bytes = DefaultAzureCredential().get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
#     # Pack the token into the required structure
#     token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
#     # Inject the token into the connection parameters
#     cparams["attrs_before"] = {1256: token_struct}  # SQL_COPT_SS_ACCESS_TOKEN

with engine.connect() as conn:
    result_db_name = conn.execute(text("SELECT DB_NAME() AS name_of_current_database"))
    database_name_result = result_db_name.fetchone()
    database_name = database_name_result[0]
    result_server_name = conn.execute(text("SELECT @@SERVERNAME"))
    database_server_result = result_server_name.fetchone()
    database_server = database_server_result[0]
print("Connected to database: {} on server: {}".format(database_name, database_server))

def verify_table_exists():
    """
    Verify that the 'lilian_weng_blog_posts' table exists in the 'dn-langchain-mssql-demo' SQL Server database 'dn-langchain-mssql-demo'.

    This function uses the existing vector store instance to check table existence
    by attempting a simple similarity search operation. This approach leverages
    langchain_sqlserver's built-in Azure SQL Entra ID authentication handling.

    Exits the script with error code 1 if the table does not exist.
    """
    print("Verifying document store table exists...")

    try:

        # Use the existing vector store to check table existence
        # Since langchain_sqlserver handles Azure SQL Entra ID authentication correctly,
        # we'll leverage the main vector store instance for verification
        try:
            # Try to perform a simple operation that requires the table to exist
            # We'll attempt a similarity search with a dummy query - if the table doesn't exist, this will fail
          inspector = inspect(engine)
          table_exists = inspector.has_table(TABLE_NAME)
          if table_exists:
              print("Verified: {} table exists".format(TABLE_NAME))
          else:
              print("ERROR: Required document store {} table does not exist in the database.".format(TABLE_NAME))
              print("Please run the data ingestion script first.")
              sys.exit(1)
        except Exception as search_error:
            # Check if the error is specifically about table not existing
            error_msg = str(search_error).lower()
            if "invalid object name" in error_msg or "does not exist" in error_msg or "table" in error_msg:
                print("ERROR: Required document store {} table does not exist in the database.".format(TABLE_NAME))
                print("Please run the data ingestion script first.")
                sys.exit(1)
            else:
                # Some other error occurred, re-raise it
                print(f"ERROR: Failed to verify table existence: {str(search_error)}")
                print("Please check your database connection and try again.")
                sys.exit(1)

            if not table_exists:
                print("ERROR: Required document store {} table does not exist in the database.".format(TABLE_NAME))
                print("Please run the data ingestion script first.")
                sys.exit(1)
            else:
                print("Verified: {} table exists".format(TABLE_NAME))

    except KeyError as e:
        print(f"ERROR: Environment variable not found: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to verify table existence: {str(e)}")
        print("Please check your database connection and try again.")
        sys.exit(1)

if args.create_vector_store:
  urls = [
      "https://lilianweng.github.io/posts/2023-06-23-agent/",
      "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
      "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
  ]

  print("Loading documents...")
  docs = [WebBaseLoader(url).load() for url in urls]
  docs_list = [item for sublist in docs for item in sublist]

  print("Splitting documents...")
  text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
      chunk_size=100, chunk_overlap=50
  )
  doc_splits = text_splitter.split_documents(docs_list)
  ids = list(range(len(doc_splits)))
else:
  verify_table_exists()

# Add Vector Store
print("Configuring vector store...")
vector_store = SQLServer_VectorStore(
    embedding_function=OpenAIEmbeddings(
        model=OPENAI_EMBEDDING_MODEL,
        # api_key=OPENAI_API_KEY,
        # base_url=OPENAI_ENDPOINT,
    ),
    embedding_length=1536,
    connection_string=MSSQL_CONNECTION_STRING,
    table_name=TABLE_NAME
)

if args.create_vector_store:
  vector_store.delete()

  print("Adding documents...")
  vector_store.add_documents(doc_splits, ids=ids)    

print("Creating retriever tool...")
retriever = vector_store.as_retriever()
retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_blog_posts",
    "Search and return information about Lilian Weng blog posts on LLM agents, prompt engineering, and adversarial attacks on LLMs.",
)

if "windows.net" in MSSQL_CONNECTION_STRING:
    database_server_type = "Azure SQL Server"
else:
    database_server_type = "On-Premises SQL Server"

@tool(description="Delete the {0} table from the {1} database on the {2} {3}. This is a destructive operation that will permanently \
                  remove the table and all its data. Use with caution as this action cannot be undone. Returns: str: A message \
                  indicating the result of the operation".format(TABLE_NAME, database_name, database_server, database_server_type))
def delete_blog_posts_table() -> str:
    print("---DELETE TABLE OPERATION REQUESTED---")

    try:
        print("Connecting to SQL Server database {} using langchain_sqlserver...".format(database_name))

        # Create a temporary SQLServer_VectorStore instance to use its delete method
        # We use the same configuration as the main vector_store but create a new instance
        # to avoid affecting the main vector store object
        metadata = MetaData()
        table = Table(TABLE_NAME, metadata, autoload_with=engine)
        # Drop the table
        with engine.connect() as conn:
            conn.execute(DropTable(table, if_exists=True))
            conn.commit()
    except KeyError as e:
        error_message = f"Environment variable not found: {str(e)}"
        print(f"---ERROR: {error_message}---")
        return error_message
    except Exception as e:
        error_message = f"Error occurred while deleting table: {str(e)}"
        print(f"---ERROR: {error_message}---")
        return error_message
    
tools = [retriever_tool, delete_blog_posts_table]

print("Initializing Agent state class...")
class AgentState(TypedDict):
    # The add_messages function defines how an update should be processed
    # Default is to replace. add_messages says "append"
    messages: Annotated[Sequence[BaseMessage], add_messages]

###
### Edges
###
print("Initializing Agent graph edges...")

def grade_documents(state) -> Literal["generate", "rewrite"]:
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (messages): The current state

    Returns:
        str: A decision for whether the documents are relevant or not
    """

    print("---CHECK RELEVANCE---")

    # Data model
    class grade(BaseModel):
        """Binary score for relevance check."""

        binary_score: str = Field(description="Relevance score 'yes' or 'no'")

    # LLM
    model = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        model=OPENAI_MODEL,
        streaming=True,
        temperature=0,
    )

    # LLM with tool and validation
    llm_with_tool = model.with_structured_output(grade)

    # Prompt
    prompt = PromptTemplate(
        template="""You are a grader assessing relevance of a retrieved document to a user question. \n 
        Here is the retrieved document: \n\n {context} \n\n
        Here is the user question: {question} \n
        If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.""",
        input_variables=["context", "question"],
    )

    # Chain
    chain = prompt | llm_with_tool

    messages = state["messages"]
    last_message = messages[-1]

    question = messages[0].content
    docs = last_message.content

    scored_result = chain.invoke({"question": question, "context": docs})

    score = scored_result.binary_score

    if score == "yes":
        print("---DECISION: DOCS RELEVANT---")
        return "generate"

    else:
        print("---DECISION: DOCS NOT RELEVANT---")
        print(score)
        return "rewrite"

###
### Nodes
###
print("Initializing Agent graph nodes...")

def agent(state):
    """
    Invokes the agent model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, or simply end.

    Args:
        state (messages): The current state

    Returns:
        dict: The updated state with the agent response appended to messages
    """
    print("---CALL AGENT---")
    messages = state["messages"]
    model = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        model=OPENAI_MODEL,
        streaming=True,
        temperature=0
    )
    model = model.bind_tools(tools)
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


def rewrite(state):
    """
    Transform the query to produce a better question.

    Args:
        state (messages): The current state

    Returns:
        dict: The updated state with re-phrased question
    """

    print("---TRANSFORM QUERY---")
    messages = state["messages"]
    question = messages[0].content

    msg = [
        HumanMessage(
            content=f""" \n 
    Look at the input and try to reason about the underlying semantic intent / meaning. \n 
    Here is the initial question:
    \n ------- \n
    {question} 
    \n ------- \n
    Formulate an improved question: """,
        )
    ]

    # Grader
    model = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        model=OPENAI_MODEL,
        streaming=True,
        temperature=0
    )
    response = model.invoke(msg)
    return {"messages": [response]}


def generate(state):
    """
    Generate answer

    Args:
        state (messages): The current state

    Returns:
        dict: The updated state with re-phrased question
    """
    print("---GENERATE---")
    messages = state["messages"]
    question = messages[0].content
    last_message = messages[-1]

    docs = last_message.content

    # Prompt
    prompt = prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """ 
                You are the Lilian Weng blog post agent. You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.            
                Context: {context} 
                """,
            ),
            (
                "human",
                "Question: {question} ?",
            ),
        ]
    )

    # LLM
    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        model=OPENAI_MODEL,
        streaming=True,
        temperature=0
    )

    # Post-processing
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Chain
    rag_chain = prompt | llm | StrOutputParser()

    # Run
    response = rag_chain.invoke({"context": docs, "question": question})
    return {"messages": [response]}


# Define the prompt
print("Initializing prompt...")
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """ 
            You are the Lilian Weng blog post agent.You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.            
            Context: {context} 
            """,
        ),
        (
            "human",
            "Question: {question} ?",
        ),
    ]
)

# Define a new graph
print("Initializing agent graph...")
workflow = StateGraph(AgentState)

# Define the nodes we will cycle between
workflow.add_node("agent", agent)  # agent
retrieve = ToolNode(tools)
workflow.add_node("retrieve", retrieve)  # retrieval
workflow.add_node("rewrite", rewrite)  # Re-writing the question
workflow.add_node(
    "generate", generate
)  # Generating a response after we know the documents are relevant
# Call agent node to decide to retrieve or not
workflow.add_edge(START, "agent")

# Decide whether to retrieve
workflow.add_conditional_edges(
    "agent",
    # Assess agent decision
    tools_condition,
    {
        # Translate the condition outputs to nodes in our graph
        "tools": "retrieve",
        END: END,
    },
)

# Edges taken after the `action` node is called.
workflow.add_conditional_edges(
    "retrieve",
    # Assess agent decision
    grade_documents,
)
workflow.add_edge("generate", END)
workflow.add_edge("rewrite", "agent")

# Compile
graph = workflow.compile()

# Set the appropriate prompt based on the command line flag
if args.delete:
    question = f"Please delete the '{TABLE_NAME}' table from the '{database_name}' database on the database server '{database_server}'."
    print("Running agent in DELETE mode...")
else:
    question = "What does Lilian Weng say about the types of agent memory?"
    print("Running agent in QUERY mode...")
print(f"Question: {question}")

# Run the Agent
inputs = {
    "messages": [
        ("user", question),
    ]
}
for output in graph.stream(inputs):
    for key, value in output.items():
        pprint.pprint(f"Output from node '{key}':")
        pprint.pprint("---")
        pprint.pprint(value, indent=2, width=80, depth=None)
    pprint.pprint("---")