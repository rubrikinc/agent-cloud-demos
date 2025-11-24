"""
Test MCP Integration

This script tests the MCP server integration with the customer support agent
by directly calling the MCP tools and verifying the responses.

Usage:
    python test_mcp_integration.py
"""

import os
import sys
import json
import subprocess
from typing import Dict, Any

# Add parent directory to path to import from customer_support_agent
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

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
        print(f"\n📤 Sending request to MCP server:")
        print(f"   Tool: {tool_name}")
        print(f"   Arguments: {json.dumps(arguments, indent=2)}")

        # Prepare environment variables for MCP server
        # The MCP server will inherit these environment variables
        env = os.environ.copy()

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
            print(f"   ⚠️  MCP Server stderr:")
            for line in stderr.split('\n'):
                if line.strip():
                    print(f"      {line}")
        
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
                            result = json.loads(content_text)
                            print(f"📥 Received response:")
                            print(f"   Success: {result.get('success')}")
                            print(f"   Message: {result.get('message', 'N/A')}")
                            if result.get('data'):
                                print(f"   Data: {json.dumps(result['data'][:2], indent=2)}...")  # Show first 2 records
                            return result
                        return response["result"]
                except json.JSONDecodeError:
                    continue
        
        return {"success": False, "message": "No valid response from MCP server"}
        
    except subprocess.TimeoutExpired:
        process.kill()
        return {"success": False, "message": "MCP server call timed out"}
    except Exception as e:
        return {"success": False, "message": f"Error calling MCP server: {str(e)}"}


def test_list_tables():
    """Test listing tables in the database."""
    print("\n" + "="*80)
    print("TEST 1: List Tables")
    print("="*80)
    
    result = call_mcp_tool("list_table", {"parameters": []})
    
    if result.get("success"):
        print("✅ Test passed: Successfully listed tables")
        return True
    else:
        print(f"❌ Test failed: {result.get('message')}")
        return False


def test_read_orders():
    """Test reading from the orders table."""
    print("\n" + "="*80)
    print("TEST 2: Read Orders")
    print("="*80)
    
    query = "SELECT TOP 5 order_id, status, tracking, estimated_delivery FROM orders"
    result = call_mcp_tool("read_data", {"query": query})
    
    if result.get("success") and result.get("data"):
        print(f"✅ Test passed: Retrieved {len(result['data'])} orders")
        return True
    else:
        print(f"❌ Test failed: {result.get('message')}")
        return False


def test_read_knowledge_base():
    """Test reading from the knowledge_base table."""
    print("\n" + "="*80)
    print("TEST 3: Read Knowledge Base")
    print("="*80)
    
    query = "SELECT keyword, article FROM knowledge_base WHERE keyword = 'return'"
    result = call_mcp_tool("read_data", {"query": query})
    
    if result.get("success"):
        if result.get("data") and len(result["data"]) > 0:
            print(f"✅ Test passed: Found knowledge base article")
            return True
        else:
            print("⚠️  Warning: knowledge_base table exists but is empty")
            print("   Run: python setup_knowledge_base.py")
            return False
    else:
        print(f"⚠️  Warning: knowledge_base table may not exist")
        print(f"   Message: {result.get('message')}")
        print("   Run: python setup_knowledge_base.py")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("MCP Integration Test Suite")
    print("="*80)
    
    # Check if MCP server exists
    if not os.path.exists(MCP_SERVER_PATH):
        print(f"\n❌ Error: MCP server not found at {MCP_SERVER_PATH}")
        print("   Please build the MCP server first:")
        print("   cd MssqlMcp/Node && npm install && npm run build")
        return 1
    
    print(f"✓ MCP server found at: {MCP_SERVER_PATH}")
    
    # Run tests
    tests = [
        test_list_tables,
        test_read_orders,
        test_read_knowledge_base,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test error: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed or require setup")
        return 1


if __name__ == "__main__":
    exit(main())

