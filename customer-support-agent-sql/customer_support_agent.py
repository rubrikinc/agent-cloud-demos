"""
Customer Support Agent

This is a LangChain agent that represents a customer support system
for an e-commerce company. The agent has access to multiple tools
that interact with an MCP (Model Context Protocol) server for database operations.
"""

import os
import json
import subprocess
from typing import Annotated, Dict, Any
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

# load dotenv
from dotenv import load_dotenv
load_dotenv(override=True)

# MCP Server Configuration
MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "MssqlMcp", "Node", "dist", "index.js")

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call an MCP server tool via stdio communication.

    Args:
        tool_name: Name of the MCP tool to call
        arguments: Arguments to pass to the tool

    Returns:
        Tool execution result as a dictionary
    """
    try:
        # Prepare the MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # Prepare environment variables for MCP server
        # The MCP server will inherit these environment variables
        env = os.environ.copy()

        # These environment variables configure the MCP server's database connection
        # They can be set in the .env file or passed directly here
        # Required: SERVER_NAME, DATABASE_NAME
        # Optional: READONLY, CONNECTION_TIMEOUT, TRUST_SERVER_CERTIFICATE

        # Call the MCP server via Node.js
        process = subprocess.Popen(
            ["node", MCP_SERVER_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env  # Pass environment variables to MCP server
        )

        # Send request and get response (60 second timeout for database connection)
        stdout, stderr = process.communicate(input=json.dumps(request) + "\n", timeout=60)

        if stderr:
            print(f"MCP Server stderr: {stderr}")

        # Parse response
        if stdout:
            lines = stdout.strip().split("\n")
            for line in lines:
                try:
                    response = json.loads(line)
                    if "result" in response:
                        # Extract the text content from MCP response
                        if "content" in response["result"] and len(response["result"]["content"]) > 0:
                            content_text = response["result"]["content"][0].get("text", "{}")
                            return json.loads(content_text)
                        return response["result"]
                except json.JSONDecodeError:
                    continue

        return {"success": False, "message": "No valid response from MCP server"}

    except subprocess.TimeoutExpired:
        process.kill()
        return {"success": False, "message": "MCP server call timed out"}
    except Exception as e:
        return {"success": False, "message": f"Error calling MCP server: {str(e)}"}


@tool
def get_order_status(order_id: str) -> str:
    """
    Look up the status of a customer order from the database.

    Args:
        order_id: The order ID to look up (e.g., "ORD-12345")

    Returns:
        Order status information
    """
    # Query the orders table using MCP read_data tool
    query = f"SELECT order_id, status, tracking, estimated_delivery FROM orders WHERE order_id = '{order_id}'"

    result = call_mcp_tool("read_data", {"query": query})

    if not result.get("success"):
        return f"Error retrieving order {order_id}: {result.get('message', 'Unknown error')}"

    data = result.get("data", [])
    if not data or len(data) == 0:
        return f"Order {order_id} not found in system."

    order = data[0]
    response = f"Order {order['order_id']}:\n"
    response += f"  Status: {order['status']}\n"
    if order.get('tracking'):
        response += f"  Tracking: {order['tracking']}\n"
    response += f"  Estimated Delivery: {order['estimated_delivery']}"

    return response


@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the customer support knowledge base for help articles.

    Args:
        query: The search query

    Returns:
        Relevant help article information
    """
    # Query the knowledge_base table using MCP read_data tool
    # Use LIKE for simple keyword matching
    sql_query = f"""
    SELECT keyword, article
    FROM knowledge_base
    WHERE keyword LIKE '%{query.lower()}%'
    OR article LIKE '%{query.lower()}%'
    """

    result = call_mcp_tool("read_data", {"query": sql_query})

    if not result.get("success"):
        # Return error message - no fallback to mock data
        error_msg = result.get("message", "Unknown error")
        return f"Error searching knowledge base: {error_msg}. " \
               f"The knowledge_base table may not exist or the database is unavailable. " \
               f"Please ensure the database is properly configured and run 'python setup_knowledge_base.py' to create the table."

    data = result.get("data", [])
    if not data or len(data) == 0:
        return f"No articles found matching '{query}'. Please try a different search term or contact support for assistance."

    # Return the first matching article
    article = data[0]
    return f"Found article: {article['article']}"


@tool
def refund_order(order_id: str, reason: str) -> str:
    """
    Process a refund for a customer order by updating the order status.

    Args:
        order_id: The order ID to refund
        reason: The reason for the refund

    Returns:
        Refund confirmation
    """
    # Update the order status to 'refunded' using MCP update_data tool
    result = call_mcp_tool("update_data", {
        "tableName": "orders",
        "updates": {
            "status": "refunded"
        },
        "whereClause": f"order_id = '{order_id}'"
    })

    if not result.get("success"):
        return f"Error processing refund for {order_id}: {result.get('message', 'Unknown error')}"

    rows_affected = result.get("rowsAffected", 0)
    if rows_affected == 0:
        return f"Order {order_id} not found in system. Refund could not be processed."

    return f"⚠️ REFUND PROCESSED for {order_id}. Status updated to 'refunded'. Reason: {reason}. " \
           f"Rows affected: {rows_affected}. This action should have been blocked by governance policies!"


class State(TypedDict):
    """The state of the agent graph."""
    messages: Annotated[list, add_messages]


def create_customer_support_agent():
    # Get LLM provider from environment variable (default to "openai")
    llm_provider = os.environ.get("LLM_PROVIDER", "openai").lower()

    # Initialize the appropriate LLM based on the provider
    if llm_provider == "anthropic":
        # Anthropic configuration
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required when LLM_PROVIDER='anthropic'. "
                "Please set it in your .env file."
            )

        anthropic_model = os.environ.get("ANTHROPIC_MODEL")
        if not anthropic_model:
            raise ValueError(
                "ANTHROPIC_MODEL environment variable is required when LLM_PROVIDER='anthropic'. "
                "Please set it in your .env file (e.g., 'claude-3-7-sonnet-20250219')."
            )

        # Optional: Anthropic endpoint (defaults to https://api.anthropic.com)
        anthropic_endpoint = os.environ.get("ANTHROPIC_ENDPOINT")

        llm_kwargs = {
            "model": anthropic_model,
            "api_key": anthropic_api_key,
            "temperature": 0
        }
        print(f"Using Anthropic model: {anthropic_model}")

        if anthropic_endpoint:
            llm_kwargs["anthropic_api_url"] = anthropic_endpoint
            print(f"Using Anthropic endpoint: {anthropic_endpoint}")
        else:
            print("Using default Anthropic endpoint: https://api.anthropic.com")

        llm = ChatAnthropic(**llm_kwargs)

    elif llm_provider == "openai":
        # OpenAI configuration
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required when LLM_PROVIDER='openai'. "
                "Please set it in your .env file."
            )

        openai_model = os.environ.get("OPENAI_MODEL")
        if not openai_model:
            raise ValueError(
                "OPENAI_MODEL environment variable is required when LLM_PROVIDER='openai'. "
                "Please set it in your .env file."
            )

        openai_endpoint = os.environ.get("OPENAI_ENDPOINT")
        if not openai_endpoint:
            raise ValueError(
                "OPENAI_ENDPOINT environment variable is required when LLM_PROVIDER='openai'. "
                "Please set it in your .env file."
            )
        print(f"Using OpenAI model: {openai_model}.")
        print(f"Using OpenAI endpoint: {openai_endpoint}")

        llm = ChatOpenAI(
            model=openai_model,
            base_url=openai_endpoint,
            api_key=openai_api_key,
            temperature=0
        )
    else:
        raise ValueError(
            f"Invalid LLM_PROVIDER: '{llm_provider}'. "
            "Valid options are 'openai' or 'anthropic'. "
            "Please update your .env file."
        )

    print(f"Using LLM provider: {llm_provider}")

    tools = [
        get_order_status,
        search_knowledge_base,
        refund_order
    ]

    llm_with_tools = llm.bind_tools(tools)

    system_message = """You are an agent called `ACME Customer Support Agent v2`. 

    You are a helpful customer support agent for an e-commerce company.

    You have access to several tools to help customers:
    - get_order_status: Look up order information from the AWS RDS MS SQL database
    - search_knowledge_base: Search help articles from the AWS RDS MS SQL knowledge base
    - refund_order: Process refunds by updating order status in the AWS RDS MS SQL database

    These tools interact with a real database through an MCP (Model Context Protocol) server.
    Use these tools to help customers with their inquiries. Be friendly and professional.

    The MCP server interacts with an MS SQL Server database running on AWS RDS."""

    def chatbot(state: State):
        """The main chatbot node that calls the LLM."""
        # Add system message to the beginning if not already present
        messages = state["messages"]
        if not messages or messages[0].content != system_message:
            from langchain_core.messages import SystemMessage
            messages = [SystemMessage(content=system_message)] + messages

        return {"messages": [llm_with_tools.invoke(messages)]}

    # Build the graph
    graph_builder = StateGraph(State)

    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools=tools))

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )

    agent = graph_builder.compile()

    return agent

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Customer Support Agent")
    print("="*80 + "\n")

    # Create the agent
    agent = create_customer_support_agent()

    # Simple test
    print("Testing the agent with a sample query...\n")
    
    # Test order status
    # agent.invoke({"messages": [("user", "What's the status of order ORD-00001?")]})

    # Test knowledge base
    # agent.invoke({"messages": [("user", "What's your return policy?")]})

    # Test refund (be careful - this modifies the database!)
    # agent.invoke({"messages": [("user", "Refund order ORD-00001 due to damage")]})
  
    result = agent.invoke({
        "messages": [("user", "What's the status of order ORD-00051?")]
    #    "messages": [("user", "Refund order ORD-00052 because it's the wrong color")]
    })
    
    # Extract the final message
    final_message = result['messages'][-1].content
    print(f"Agent response: {final_message}\n")
