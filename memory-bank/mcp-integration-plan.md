# MCP Integration Plan for Open-LLM-VTuber

## Overview
This document provides a comprehensive implementation plan for integrating MCP (Model Context Protocol) servers into Open-LLM-VTuber, enabling the AI VTuber to access Jira tickets and local files seamlessly during conversations without any provider or server-specific hardcoding.

## Key Findings from Architecture Analysis

### Current State
1. **No function calling support** - LLM interfaces only handle basic chat completion
2. **Generic OpenAI-compatible interface exists** - Works with Gemini, OpenAI, Groq, etc.
3. **No plugin system** - Uses modular architecture with factories
4. **MCP config exists** - YAML already has MCP server definitions
5. **Streaming architecture** - All responses stream through WebSocket to frontend
6. **TTS pipeline** - Text is processed server-side before audio generation

### Critical Constraints
1. **Tool calls must NEVER reach TTS** - Frontend receives processed audio
2. **Must remain provider-agnostic** - No hardcoding for specific LLM providers
3. **Must remain MCP server-agnostic** - No special handling for specific servers

## MCP Protocol Understanding

### How MCP Works
1. **MCP is NOT direct function calling** - It's a protocol layer
2. **Communication via JSON-RPC 2.0** over stdio, SSE, or HTTP
3. **Capability discovery** through:
   - `list_tools()` - Returns available tool schemas
   - `list_resources()` - Returns data sources
   - `list_prompts()` - Returns prompt templates
4. **Tool execution** via `call_tool(name, arguments)`
5. **mcp-remote** is just a transport - handles auth/connection, not special functionality

### MCP Server Lifecycle
```
1. Client → Server: initialize (with protocol version)
2. Server → Client: capabilities & server info
3. Client → Server: initialized notification
4. Client → Server: list_tools request
5. Server → Client: available tools list
6. Client → Server: call_tool requests as needed
```

## Implementation Architecture

### Design Principles
1. **Provider-agnostic** - Use OpenAI function calling format (industry standard)
2. **Server-agnostic** - All MCP servers treated equally
3. **Minimal changes** - Extend existing interfaces, don't replace
4. **Generic approach** - No hardcoding for specific providers or servers

### Component Architecture
```
User Input
    ↓
WebSocket Handler
    ↓
MCPAgent (new)
    ├── OpenAI-Compatible LLM (ANY provider)
    │   └── Enhanced with optional tools parameter
    ├── Generic MCP Client Manager
    │   ├── MCP Server 1 (stdio/sse/http)
    │   ├── MCP Server 2 (stdio/sse/http)
    │   └── MCP Server N (any transport)
    └── Response Pipeline → TTS
```

## Detailed Implementation Plan

### Phase 1: Enhance LLM Interface (Minimal Changes)

#### 1.1 Add Function Calling Check
```python
# src/open_llm_vtuber/agent/stateless_llm/stateless_llm_interface.py
class StatelessLLMInterface(ABC):
    # Existing method stays unchanged
    @abstractmethod
    async def chat_completion(...) -> AsyncIterator[str]:
        pass
    
    # Add simple capability check
    async def supports_function_calling(self) -> bool:
        """Check if this LLM supports function calling"""
        return False  # Default, override in implementations
```

#### 1.2 Enhance OpenAI-Compatible Implementation
```python
# src/open_llm_vtuber/agent/stateless_llm/openai_compatible_llm.py
class AsyncLLM(StatelessLLMInterface):
    
    async def supports_function_calling(self) -> bool:
        """OpenAI-compatible endpoints typically support function calling"""
        return True
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, Any]], 
        system: str = None,
        tools: List[Dict[str, Any]] = None  # Just add optional parameter!
    ) -> AsyncIterator[Union[str, Dict]]:
        """Enhanced to support tools when provided"""
        
        # Build messages as before
        if system:
            messages = [{"role": "system", "content": system}] + messages
        
        # Create completion kwargs
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }
        
        # Add tools if provided (works with Gemini, OpenAI, etc!)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        try:
            stream = await self.client.chat.completions.create(**kwargs)
            
            # Tool call aggregator for streaming chunks
            tool_calls_aggregator = {}  # {index: {"id": ..., "name": ..., "arguments": ""}}
            
            # Parse streaming response
            async for chunk in stream:
                delta = chunk.choices[0].delta
                
                # Yield text content
                if delta.content:
                    yield delta.content
                
                # Aggregate tool call chunks
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tool_call_chunk in delta.tool_calls:
                        index = tool_call_chunk.index
                        
                        # Initialize aggregator for this index
                        if index not in tool_calls_aggregator:
                            tool_calls_aggregator[index] = {
                                "id": tool_call_chunk.id,
                                "name": "",
                                "arguments": ""
                            }
                        
                        # Accumulate name and arguments
                        if tool_call_chunk.function.name:
                            tool_calls_aggregator[index]["name"] += tool_call_chunk.function.name
                        if tool_call_chunk.function.arguments:
                            tool_calls_aggregator[index]["arguments"] += tool_call_chunk.function.arguments
            
            # After stream completes, yield complete tool calls
            for index, call_info in tool_calls_aggregator.items():
                if call_info["name"]:  # Only yield if we have a function name
                    yield {
                        "type": "tool_call",
                        "id": call_info["id"],
                        "function": {
                            "name": call_info["name"],
                            "arguments": call_info["arguments"]
                        }
                    }
                            
        except Exception as e:
            # Only fallback for specific tool-related errors
            if "tools" in str(e).lower() or "function" in str(e).lower():
                logger.warning(f"Provider doesn't support tools, falling back: {e}")
                # Recursive call without tools
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                stream = await self.client.chat.completions.create(**kwargs)
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                # Re-raise other errors
                raise
```

### Phase 2: Generic MCP Client Implementation

#### 2.1 Create Generic MCP Client Manager
```python
# src/open_llm_vtuber/mcp/mcp_client_manager.py
from mcp import ClientSession
from mcp.client.stdio import StdioTransport
from mcp.client.sse import SSETransport
import asyncio
from loguru import logger

class MCPClientManager:
    def __init__(self, mcp_configs: dict):
        self.configs = mcp_configs
        self.servers = {}
        self.tools_cache = {}
        
    async def initialize(self):
        """Connect to all configured MCP servers generically"""
        for server_name, config in self.configs.items():
            try:
                # Create transport based on type
                transport = await self._create_transport(config)
                if not transport:
                    logger.warning(f"Unknown transport type for {server_name}")
                    continue
                
                # Create session and manage lifecycle manually
                session = ClientSession(transport)
                await session.start()  # Start the transport
                await session.initialize()
                
                # Store active session
                self.servers[server_name] = session
                
                # Discover tools
                tools_response = await session.list_tools()
                
                # Cache tools with namespaced names
                for tool in tools_response.tools:
                    # Namespace tool to avoid conflicts
                    namespaced_name = f"{server_name}.{tool.name}"
                    self.tools_cache[namespaced_name] = {
                        "server_name": server_name,
                        "original_name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    }
                
                logger.info(f"Connected to {server_name}, found {len(tools_response.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_name}: {e}")
                # Continue with other servers
    
    async def shutdown(self):
        """Gracefully close all MCP sessions"""
        for server_name, session in self.servers.items():
            try:
                await session.shutdown()
                logger.info(f"Disconnected from MCP server {server_name}")
            except Exception as e:
                logger.error(f"Failed to shutdown MCP server {server_name}: {e}")
    
    async def _create_transport(self, config: dict):
        """Create appropriate transport based on config"""
        transport_type = config.get("type", "stdio")
        
        if transport_type == "stdio":
            return StdioTransport(
                command=config["command"],
                args=config.get("args", []),
                env=config.get("env", {})
            )
        elif transport_type == "sse":
            return SSETransport(
                url=config["url"],
                headers=config.get("headers", {})
            )
        # Add more transport types as needed
        
        return None
    
    def get_tool_schemas_for_llm(self) -> List[Dict]:
        """Convert MCP tools to OpenAI function calling format"""
        tools = []
        for tool_name, tool_info in self.tools_cache.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info["input_schema"]
                }
            })
        return tools
    
    async def execute_tool(self, namespaced_name: str, arguments: dict) -> dict:
        """Execute tool on appropriate MCP server"""
        tool_info = self.tools_cache.get(namespaced_name)
        if not tool_info:
            raise ValueError(f"Unknown tool: {namespaced_name}")
        
        server = self.servers.get(tool_info["server_name"])
        if not server:
            raise RuntimeError(f"Server {tool_info['server_name']} not connected")
        
        # Call tool with original name
        result = await server.call_tool(
            name=tool_info["original_name"],
            arguments=arguments
        )
        
        return result
```

### Phase 3: Create MCPAgent

#### 3.1 Implement MCPAgent
```python
# src/open_llm_vtuber/agent/mcp_agent.py
from .memory_agent import BasicMemoryAgent
from ..mcp.mcp_client_manager import MCPClientManager
import json
from loguru import logger

class MCPAgent(BasicMemoryAgent):
    def __init__(self, llm, memory, response_pipe, mcp_configs):
        super().__init__(llm, memory, response_pipe)
        self.mcp_configs = mcp_configs
        self.mcp_manager = None
        
    async def start(self):
        """Initialize MCP connections on startup"""
        if self.mcp_configs:
            self.mcp_manager = MCPClientManager(self.mcp_configs)
            await self.mcp_manager.initialize()
        
    async def process_message(self, text: str, voice_name: str = "default"):
        # Add to memory
        self.memory.add_human_message(text)
        
        # Check if we have tools and LLM supports them
        if not self.mcp_manager or not await self.llm.supports_function_calling():
            # Fallback to basic agent behavior
            await super().process_message(text, voice_name)
            return
        
        # Get available tools
        tools = self.mcp_manager.get_tool_schemas_for_llm()
        
        # Process with tools
        assistant_message_content = ""
        tool_calls_to_make = []
        
        try:
            # First pass: Get text and identify tool calls
            async for chunk in self.llm.chat_completion(
                messages=self.memory.get_history(),
                system=self.persona_prompt,
                tools=tools if tools else None
            ):
                if isinstance(chunk, str):
                    # Regular text - send to TTS
                    assistant_message_content += chunk
                    await self.response_pipe.push(chunk)
                    
                elif isinstance(chunk, dict) and chunk.get("type") == "tool_call":
                    # Collect tool calls
                    tool_calls_to_make.append(chunk)
            
            # Add assistant's message to memory (including tool call intent)
            assistant_msg = {
                "role": "assistant",
                "content": assistant_message_content
            }
            if tool_calls_to_make:
                assistant_msg["tool_calls"] = tool_calls_to_make
            self.memory.add_message(assistant_msg)
            
            # If tools were called, execute them and get natural response
            if tool_calls_to_make:
                await self._execute_and_summarize_tools(tool_calls_to_make)
            
        except Exception as e:
            logger.error(f"Error in MCP agent processing: {e}")
            # Fallback to basic processing
            await super().process_message(text, voice_name)
        
        finally:
            await self.response_pipe.close()
    
    async def _execute_and_summarize_tools(self, tool_calls: list):
        """Execute tools and get natural language summary using standard format"""
        
        # Execute each tool and add results to memory
        for tool_call in tool_calls:
            func = tool_call["function"]
            tool_call_id = tool_call["id"]
            
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
                
                # Add tool result to memory in standard format
                self.memory.add_message({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": func["name"],
                    "content": json.dumps(result)  # Result as string
                })
                
            except Exception as e:
                logger.error(f"Tool execution failed for {func['name']}: {e}")
                # Add error to memory
                self.memory.add_message({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": func["name"],
                    "content": json.dumps({"error": str(e)})
                })
        
        # Second pass: Get natural language summary from LLM
        async for chunk in self.llm.chat_completion(
            messages=self.memory.get_history(),
            system=self.persona_prompt
            # No tools parameter - just getting a summary
        ):
            if isinstance(chunk, str):
                await self.response_pipe.push(chunk)
    
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
```

### Phase 4: Integration

#### 4.1 Register MCPAgent in Factory
```python
# src/open_llm_vtuber/agent/agent_factory.py
elif agent_config.conversation_agent_choice == "mcp_agent":
    from .mcp_agent import MCPAgent
    
    # Get MCP configs
    mcp_configs = agent_config.agent_settings.mcp_agent.get("mcp_servers", {})
    
    # Create agent
    agent = MCPAgent(
        llm=llm,
        memory=memory,
        response_pipe=response_pipe,
        mcp_configs=mcp_configs
    )
    
    # Initialize MCP connections
    await agent.start()
```

#### 4.2 Configuration (No Changes Needed!)
```yaml
# conf.yaml - Already configured correctly!
agent_config:
  conversation_agent_choice: "mcp_agent"
  agent_settings:
    mcp_agent:
      llm_provider: "gemini_llm"
      mcp_servers:
        atlassian:
          type: "stdio"
          command: "C:/Program Files/nodejs/npx.cmd"
          args: ["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"]
        filesystem:
          type: "stdio"
          command: "C:/Program Files/nodejs/npx.cmd"
          args: ["-y", "@modelcontextprotocol/server-filesystem", 
                 "C:/Users/danhc/Documents/", "C:/Users/danhc/Desktop/"]
```

## Critical Implementation Notes

### Fixed Issues from Review

1. **MCP Session Lifecycle Management**
   - Sessions are now created and started manually (not in `async with` block)
   - Added `shutdown()` method for graceful cleanup
   - Sessions remain active for the lifetime of the application

2. **Streaming Tool Call Aggregation**
   - Tool calls are now properly aggregated across streaming chunks
   - Uses index-based aggregation to handle partial tool calls
   - Only yields complete tool calls after stream ends

3. **Standard Tool Result Format**
   - Uses OpenAI's standard `role: "tool"` message format
   - Includes `tool_call_id` for proper correlation
   - Results are JSON-stringified as required by the API

4. **Improved Error Handling**
   - Only falls back on tool-specific errors (not all exceptions)
   - Preserves other errors for proper debugging
   - Tool execution errors are captured in standard format

## Key Benefits of This Approach

1. **Provider Agnostic**
   - Works with ANY OpenAI-compatible provider
   - No Gemini-specific code
   - No hardcoding for different LLMs

2. **MCP Server Agnostic**
   - All servers treated identically
   - mcp-remote auth handled by the transport itself
   - Easy to add new servers via config

3. **Minimal Code Changes**
   - Only adds optional `tools` parameter to existing method
   - Doesn't break existing functionality
   - Clean extension of current architecture

4. **Industry Standard**
   - Uses OpenAI function calling format
   - Compatible with most LLM providers
   - Well-documented approach

5. **Clean Separation**
   - Tool calls never reach TTS
   - Natural error handling
   - Maintains VTuber personality

## Testing Strategy

1. **Unit Tests**
   - Mock LLM responses with tool calls
   - Test MCP client with mock servers
   - Verify tool result processing

2. **Integration Tests**
   - Test with actual MCP servers
   - Verify Jira operations
   - Test file system access

3. **Provider Tests**
   - Test with Gemini
   - Test with OpenAI (if available)
   - Test fallback behavior

## Success Criteria

1. **Works with current config** - No config changes needed
2. **Jira access works** - Via mcp-remote without special handling
3. **File access works** - Via filesystem server
4. **Natural conversation** - No tool syntax in audio
5. **Provider independent** - Same code for all LLMs

## Future Considerations

1. **Tool namespacing** - Prevents conflicts between servers
2. **Tool filtering** - Could add regex patterns to limit tools
3. **Response caching** - Cache tool results for efficiency
4. **Parallel execution** - Execute multiple tools concurrently
5. **Tool composition** - Chain tools together