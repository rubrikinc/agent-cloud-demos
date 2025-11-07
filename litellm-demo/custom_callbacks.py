"""
LiteLLM Custom Callback Handler - Tool Governance Plugin

This plugin implements governance policies for LLM tool usage.
"""

from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy.proxy_server import UserAPIKeyAuth
from typing import Any, Optional, List
from fastapi import HTTPException

class ToolGovernanceHandler(CustomLogger):
    """
    Custom handler that enforces tool governance policies.
    """

    # Define governance policy
    UNAUTHORIZED_TOOLS = {
        "refund_order": "Refund operations require human approval. Please escalate to a supervisor.",
        "delete_customer_data": "Data deletion requires compliance review.",
        "update_pricing": "Pricing changes require manager approval."
    }

    AUTHORIZED_TOOLS = {
        "get_order_status",
        "search_knowledge_base",
        "get_customer_info",
        "create_support_ticket"
    }

    def __init__(self):
        super().__init__()
        self.blocked_attempts = []  # Track blocked attempts for monitoring

    def _extract_tool_calls(self, response) -> List[str]:
        tool_calls = []
        
        # Extract tools from response
        choice = response.choices[0]
        if hasattr(choice, 'message'):
            message = choice.message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_calls.append(tool_call.function.name)
        
        if hasattr(response, 'choices') and len(response.choices) > 0:
            choice = response.choices[0]
            if hasattr(choice, 'message'):
                message = choice.message

                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if tool_call.type == "function":
                            tool_calls.append(tool_call.function.name)

        return tool_calls

    def _validate_tools(self, tool_names: List[str]) -> Optional[str]:
        for tool_name in tool_names:
            if tool_name in self.UNAUTHORIZED_TOOLS:
                reason = self.UNAUTHORIZED_TOOLS[tool_name]
                return f"🚫 Access Denied: Tool '{tool_name}' is not authorized. {reason}"

        return None

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        response: Any,
    ) -> Any:
        """
        Post-call hook that runs after each LLM API call.

        Args:
            data: The request data
            user_api_key_dict: User API key metadata
            response: The response object from the LLM

        Returns:
            The response object if allowed, raises HTTPException if blocked
        """
        print("\n" + "="*80)
        print("🔍 TOOL GOVERNANCE CHECK")
        print("="*80)

        # Check for tool calls in the response
        tool_calls_in_response = self._extract_tool_calls(response)
        if tool_calls_in_response:
            print(f"📋 Tool calls in response: {tool_calls_in_response}")
            error = self._validate_tools(tool_calls_in_response)
            if error:
                print(f"❌ BLOCKED: {error}")
                self.blocked_attempts.append({
                    "tools": tool_calls_in_response,
                    "reason": error
                })
                raise HTTPException(status_code=403, detail=error)

        print("✅ Tool governance check passed")
        print("="*80 + "\n")

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Log successful API calls.
        """
        # Extract tool usage from response if present
        tool_calls_in_response = self._extract_tool_calls(response_obj)
        if tool_calls_in_response:
            for tool_name in tool_calls_in_response:
                print(f"📊 AUDIT: Tool '{tool_name}' called successfully")


# Create the handler instance that will be used by LiteLLM
proxy_handler_instance = ToolGovernanceHandler()