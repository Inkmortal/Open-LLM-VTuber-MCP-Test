from typing import AsyncIterator, List, Dict, Any, Optional, Literal
import json
from loguru import logger

from .basic_memory_agent import BasicMemoryAgent
from ..output_types import SentenceOutput, DisplayText
from ...mcp.mcp_client_manager import MCPClientManager
from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface
from ...config_manager import TTSPreprocessorConfig
from ..input_types import BatchInput, TextSource


class MCPAgent(BasicMemoryAgent):
    """
    Agent with MCP (Model Context Protocol) integration for tool usage.
    Extends BasicMemoryAgent to support function calling through MCP servers.
    """
    
    def __init__(
        self,
        llm: StatelessLLMInterface,
        system: str,
        live2d_model,
        mcp_configs: dict,
        tts_preprocessor_config: TTSPreprocessorConfig = None,
        faster_first_response: bool = True,
        segment_method: str = "pysbd",
        interrupt_method: Literal["system", "user"] = "user",
    ):
        """
        Initialize MCPAgent with MCP server configurations
        
        Args:
            llm: The LLM to use
            system: System prompt
            live2d_model: Model for expression extraction
            mcp_configs: Dictionary of MCP server configurations
            tts_preprocessor_config: Configuration for TTS preprocessing
            faster_first_response: Whether to enable faster first response
            segment_method: Method for sentence segmentation
            interrupt_method: Methods for writing interruptions signal in chat history
        """
        super().__init__(
            llm=llm,
            system=system,
            live2d_model=live2d_model,
            tts_preprocessor_config=tts_preprocessor_config,
            faster_first_response=faster_first_response,
            segment_method=segment_method,
            interrupt_method=interrupt_method,
        )
        
        self.mcp_configs = mcp_configs
        self.mcp_manager = None
        logger.info("MCPAgent initialized with MCP configs")
        
    async def start(self):
        """Initialize MCP connections on startup"""
        logger.debug(f"MCPAgent.start() called with configs: {list(self.mcp_configs.keys()) if self.mcp_configs else 'None'}")
        if self.mcp_configs:
            logger.debug("Creating MCPClientManager...")
            self.mcp_manager = MCPClientManager(self.mcp_configs)
            logger.debug("MCPClientManager created, calling initialize()...")
            await self.mcp_manager.initialize()
            logger.info("MCP connections initialized successfully")
        else:
            logger.warning("No MCP configurations provided")
    
    async def shutdown(self):
        """Shutdown MCP connections gracefully"""
        if self.mcp_manager:
            await self.mcp_manager.shutdown()
            logger.info("MCP connections shut down")
    
    def _chat_function_factory(self, original_chat_completion):
        """
        Create a chat function that integrates MCP tool calling
        """
        # Create our custom chat completion function that handles tools
        async def mcp_chat_completion(messages, system):
            """Custom chat completion that handles MCP tools"""
            # Check if we have tools and LLM supports them
            if not self.mcp_manager or not await self._llm.supports_function_calling():
                # Fallback to original behavior
                async for token in original_chat_completion(messages, system):
                    yield token
                return
            
            # Get available tools
            tools = self.mcp_manager.get_tool_schemas_for_llm()
            
            # Process with tools
            assistant_message_content = ""
            tool_calls_to_make = []
            
            # First pass: Get text and identify tool calls
            async for chunk in self._llm.chat_completion(
                messages=messages,
                system=system,
                tools=tools if tools else None
            ):
                if isinstance(chunk, str):
                    # Regular text - just yield it
                    assistant_message_content += chunk
                    yield chunk
                        
                elif isinstance(chunk, dict) and chunk.get("type") == "tool_call":
                    # Collect tool calls
                    logger.debug(f"Received tool call chunk: {chunk}")
                    tool_calls_to_make.append(chunk)
            
            # Store the complete assistant message in memory
            # Note: This is handled by parent class after getting complete response
            
            # If tools were called, execute them and get natural response
            if tool_calls_to_make:
                logger.info(f"=== Tool calls to execute: {len(tool_calls_to_make)} ===")
                for i, tc in enumerate(tool_calls_to_make):
                    logger.info(f"Tool {i}: {tc.get('function', {}).get('name')} with ID: {tc.get('id')}")
                
                # Add tool call info to memory for context
                self._memory.append({
                    "role": "assistant",
                    "content": assistant_message_content,
                    "tool_calls": tool_calls_to_make
                })
                
                # Execute tools and yield the summary
                async for text in self._execute_and_summarize_tools(tool_calls_to_make):
                    yield text
        
        # Let the parent class apply its decorator pipeline to our custom function
        return super()._chat_function_factory(mcp_chat_completion)
    
    async def _execute_and_summarize_tools(self, tool_calls: list, depth: int = 0) -> AsyncIterator[str]:
        """Execute tools and get natural language summary using standard format"""
        
        # Prevent infinite recursion
        MAX_TOOL_DEPTH = 5
        if depth >= MAX_TOOL_DEPTH:
            logger.warning(f"Maximum tool calling depth ({MAX_TOOL_DEPTH}) reached, stopping")
            yield "I've reached the maximum number of tool calls. Let me summarize what I found so far."
            return
        
        # Execute each tool and add results to memory
        for tool_call in tool_calls:
            func = tool_call["function"]
            tool_call_id = tool_call["id"]  # Should always have ID now
            
            try:
                # Parse arguments
                args = func["arguments"]
                if isinstance(args, str):
                    args = json.loads(args)
                
                # Execute tool
                result = await self.mcp_manager.execute_tool(
                    namespaced_name=func["name"],
                    arguments=args
                )
                
                # Result should now be a dict with 'content' and 'isError' fields
                logger.debug(f"Tool {func['name']} returned: {result}")
                
                # Format the result for the LLM
                if isinstance(result, dict) and result.get('isError', False):
                    # Error result
                    tool_content = json.dumps({"error": result.get('content', 'Unknown error')})
                else:
                    # Success result - just pass the content
                    tool_content = result.get('content', '') if isinstance(result, dict) else str(result)
                
                # Add tool result to memory in standard format
                self._memory.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": func["name"],
                    "content": tool_content
                })
                
            except Exception as e:
                logger.error(f"Tool execution failed for {func['name']}: {e}")
                # Add error to memory
                self._memory.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": func["name"],
                    "content": json.dumps({"error": str(e)})
                })
        
        # Second pass: Get natural language summary from LLM
        # Prepare messages including tool responses
        summary_messages = []
        
        # Debug: Log memory state before preparing summary
        logger.debug("=== Memory state before summary ===")
        for i, msg in enumerate(self._memory):
            logger.debug(f"Memory[{i}]: role={msg.get('role')}, "
                        f"has_tool_calls={bool(msg.get('tool_calls'))}, "
                        f"tool_call_id={msg.get('tool_call_id', 'N/A')}, "
                        f"name={msg.get('name', 'N/A')}")
        
        for msg in self._memory[1:]:  # Skip system message
            if msg.get("role") == "tool":
                # Include tool messages with all their fields
                summary_messages.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "name": msg["name"],
                    "content": msg["content"]
                })
            else:
                # Regular messages (including assistant messages with tool calls)
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    # Assistant message with tool calls - include them
                    summary_messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        "tool_calls": msg["tool_calls"]
                    })
                else:
                    # Regular messages without tool calls
                    summary_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
        
        # Debug: Log summary messages before sending
        logger.debug("=== Summary messages to send ===")
        for i, msg in enumerate(summary_messages):
            logger.debug(f"Message[{i}]: {msg}")
        
        # Get available tools for the next call
        tools = self.mcp_manager.get_tool_schemas_for_llm()
        
        # Allow the LLM to make more tool calls or provide final answer
        assistant_message_content = ""
        more_tool_calls = []
        
        async for chunk in self._llm.chat_completion(
            messages=summary_messages,
            system=self._system,
            tools=tools  # IMPORTANT: Include tools so LLM can make more calls
        ):
            if isinstance(chunk, str):
                assistant_message_content += chunk
                # Just yield the text - parent's pipeline will process it
                yield chunk
            elif isinstance(chunk, dict) and chunk.get("type") == "tool_call":
                # LLM wants to make another tool call
                logger.info(f"LLM requesting additional tool call: {chunk.get('function', {}).get('name')}")
                more_tool_calls.append(chunk)
        
        # If more tools were requested, execute them recursively
        if more_tool_calls:
            # Add the assistant message with tool calls to memory
            self._memory.append({
                "role": "assistant",
                "content": assistant_message_content,
                "tool_calls": more_tool_calls
            })
            # Recursively execute the new tools
            async for text in self._execute_and_summarize_tools(more_tool_calls, depth + 1):
                yield text
        else:
            # No more tools, just add the final response
            if assistant_message_content:
                self._memory.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
    
    def _get_natural_error_message(self, tool_name: str, error: Exception) -> str:
        """Convert errors to character-appropriate messages"""
        error_str = str(error).lower()
        
        if "auth" in error_str or "permission" in error_str:
            return "I'm having trouble accessing that service. "
        elif "timeout" in error_str:
            return "That's taking a bit longer than expected. "
        elif "not found" in error_str:
            return "I couldn't find what you're looking for. "
        else:
            return "I ran into a small issue there. "