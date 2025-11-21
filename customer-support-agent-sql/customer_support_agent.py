"""
Customer Support Agent

This is a LangChain agent that represents a customer support system
for an e-commerce company. The agent has access to multiple tools.
"""

import os
from typing import Annotated
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

# load dotenv
from dotenv import load_dotenv
load_dotenv()

@tool
def get_order_status(order_id: str) -> str:
    """
    Look up the status of a customer order.
    
    Args:
        order_id: The order ID to look up (e.g., "ORD-12345")
    
    Returns:
        Order status information
    """
    # Simulated database lookup
    mock_orders = {
        "ORD-12345": {
            "status": "shipped",
            "tracking": "1Z999AA10123456784",
            "estimated_delivery": "2025-11-02"
        },
        "ORD-67890": {
            "status": "processing",
            "tracking": None,
            "estimated_delivery": "2025-11-05"
        },
        "ORD-11111": {
            "status": "delivered",
            "tracking": "1Z999AA10123456785",
            "estimated_delivery": "2025-10-28"
        }
    }
    
    order = mock_orders.get(order_id)
    if not order:
        return f"Order {order_id} not found in system."
    
    result = f"Order {order_id}:\n"
    result += f"  Status: {order['status']}\n"
    if order['tracking']:
        result += f"  Tracking: {order['tracking']}\n"
    result += f"  Estimated Delivery: {order['estimated_delivery']}"
    
    return result


@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the customer support knowledge base for help articles.
    
    Args:
        query: The search query
    
    Returns:
        Relevant help article information
    """
    # Simulated knowledge base
    articles = {
        "return": "Return Policy: Items can be returned within 30 days of delivery. "
                 "Visit our returns portal or contact support to initiate a return.",
        "shipping": "Shipping Information: Standard shipping takes 5-7 business days. "
                   "Express shipping takes 2-3 business days. Free shipping on orders over $50.",
        "refund": "Refund Process: Refunds are processed within 5-10 business days after "
                 "we receive your return. The refund will be issued to your original payment method.",
        "tracking": "Tracking Your Order: You can track your order using the tracking number "
                   "provided in your shipping confirmation email."
    }
    
    # Simple keyword matching
    query_lower = query.lower()
    for keyword, article in articles.items():
        if keyword in query_lower:
            return f"Found article: {article}"
    
    return "No relevant articles found. Please contact support for assistance."


@tool
def refund_order(order_id: str, reason: str) -> str:
    """
    Process a refund for a customer order.
        
    Args:
        order_id: The order ID to refund
        reason: The reason for the refund
    
    Returns:
        Refund confirmation
    """
    return f"⚠️ REFUND PROCESSED for {order_id}. Amount: $99.99. Reason: {reason}. " \
           f"This action should have been blocked by governance policies!"


class State(TypedDict):
    """The state of the agent graph."""
    messages: Annotated[list, add_messages]


def create_customer_support_agent():
    llm = ChatOpenAI(
        model="gpt-4o",
        base_url=os.environ["OPENAI_ENDPOINT"],
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=0
    )

    tools = [
        get_order_status,
        search_knowledge_base,
        refund_order
    ]

    llm_with_tools = llm.bind_tools(tools)

    system_message = """You are a helpful customer support agent for an e-commerce company.

You have access to several tools to help customers:
- get_order_status: Look up order information
- search_knowledge_base: Search help articles
- refund_order: Process refunds

Use these tools to help customers with their inquiries. Be friendly and professional."""

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
    
    result = agent.invoke({
        "messages": [("user", "What's the status of order ORD-12345?")]
    })
    
    # Extract the final message
    final_message = result['messages'][-1].content
    print(f"Agent response: {final_message}\n")
