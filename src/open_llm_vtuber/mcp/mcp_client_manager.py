from typing import Dict, List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
import asyncio
import sys
import subprocess
import io
from contextlib import AsyncExitStack
from loguru import logger


class MCPClientManager:
    def __init__(self, mcp_configs: dict):
        self.configs = mcp_configs
        self.servers = {}
        self.tools_cache = {}
        self.exit_stack = AsyncExitStack()  # Manage async contexts
        
    async def initialize(self):
        """Connect to all configured MCP servers generically"""
        logger.debug("Initializing MCPClientManager exit stack")
        await self.exit_stack.__aenter__()  # Initialize the exit stack
        logger.debug("Exit stack initialized")
        
        logger.debug(f"Total MCP servers to connect: {len(self.configs)}")
        for server_name, config in self.configs.items():
            try:
                logger.info(f"========== Attempting to connect to MCP server: {server_name} ==========")
                transport_type = config.get("type", "stdio")
                logger.debug(f"Transport type: {transport_type}")
                
                if transport_type == "stdio":
                    # Create server parameters
                    logger.debug(f"Creating stdio params for {server_name}:")
                    logger.debug(f"  Command: {config['command']}")
                    logger.debug(f"  Args: {config.get('args', [])}")
                    logger.debug(f"  Raw env from config: {config.get('env')}")
                    
                    # On Windows, we need to pass None for env to use default environment
                    # Empty dict {} causes issues with subprocess creation
                    env = config.get("env")
                    if env == {}:
                        logger.debug("  Converting empty env dict to None for default environment")
                        env = None
                    
                    logger.debug(f"  Final env: {env}")
                    logger.debug(f"  Platform: {sys.platform}")
                    
                    server_params = StdioServerParameters(
                        command=config["command"],
                        args=config.get("args", []),
                        env=env
                    )
                    logger.debug(f"StdioServerParameters created: {server_params}")
                    
                    # Start stdio client and keep it alive using exit stack
                    logger.debug(f"About to call stdio_client() for {server_name}")
                    logger.debug(f"Full command that will be executed: {config['command']} {' '.join(config.get('args', []))}")
                    
                    try:
                        logger.debug("Entering stdio_client context manager...")
                        transport = await asyncio.wait_for(
                            self.exit_stack.enter_async_context(stdio_client(server_params)),
                            timeout=10.0  # Increased timeout for debugging
                        )
                        logger.debug(f"stdio_client context manager entered successfully")
                        read, write = transport
                        logger.debug(f"Got stdio streams for {server_name}: read={read}, write={write}")
                    except asyncio.TimeoutError:
                        logger.error(f"TIMEOUT: stdio_client took more than 10 seconds for {server_name}")
                        logger.error(f"Command was: {config['command']} {' '.join(config.get('args', []))}")
                        logger.error(f"This usually means:")
                        logger.error(f"  1. The subprocess failed to start")
                        logger.error(f"  2. The command is invalid or not found")
                        logger.error(f"  3. The subprocess is waiting for input")
                        continue
                    except Exception as e:
                        logger.error(f"Exception creating stdio transport: {type(e).__name__}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
                    
                    # Create and initialize session using context manager
                    logger.debug(f"Creating ClientSession for {server_name}")
                    session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                    logger.debug(f"ClientSession context entered, about to call initialize()")
                    
                    try:
                        logger.debug(f"Calling session.initialize() for {server_name}...")
                        await asyncio.wait_for(session.initialize(), timeout=10.0)
                        logger.debug(f"session.initialize() completed successfully for {server_name}")
                    except asyncio.TimeoutError:
                        logger.error(f"TIMEOUT: session.initialize() took more than 10 seconds for {server_name}")
                        logger.error(f"This means the MCP server is not responding to the initialization handshake")
                        logger.error(f"Possible causes:")
                        logger.error(f"  1. The MCP server doesn't implement the protocol correctly")
                        logger.error(f"  2. The server crashed during startup")
                        logger.error(f"  3. There's a version mismatch in the protocol")
                        continue
                    except Exception as e:
                        logger.error(f"Exception during session initialization: {type(e).__name__}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
                    
                    # Store the session
                    self.servers[server_name] = session
                    logger.debug(f"Session stored for {server_name}")
                    
                    # Discover tools
                    logger.debug(f"Calling session.list_tools() for {server_name}...")
                    try:
                        tools_response = await asyncio.wait_for(session.list_tools(), timeout=5.0)
                        logger.debug(f"list_tools() returned {len(tools_response.tools) if hasattr(tools_response, 'tools') else 'unknown'} tools")
                    except asyncio.TimeoutError:
                        logger.error(f"TIMEOUT: list_tools() took more than 5 seconds for {server_name}")
                        continue
                    except Exception as e:
                        logger.error(f"Exception listing tools: {type(e).__name__}: {e}")
                        continue
                    
                    # Cache tools with namespaced names
                    logger.debug(f"Caching tools for {server_name}")
                    for i, tool in enumerate(tools_response.tools):
                        namespaced_name = f"{server_name}.{tool.name}"
                        logger.debug(f"  Tool {i+1}: {tool.name} -> {namespaced_name}")
                        # Handle both snake_case and camelCase attribute names
                        input_schema = getattr(tool, 'input_schema', getattr(tool, 'inputSchema', None))
                        self.tools_cache[namespaced_name] = {
                            "server_name": server_name,
                            "original_name": tool.name,
                            "description": tool.description,
                            "input_schema": input_schema
                        }
                    
                    logger.info(f"✓ Successfully connected to {server_name}, found {len(tools_response.tools)} tools")
                    
                elif transport_type == "sse":
                    # For SSE, use sse_client
                    url = config["url"]
                    headers = config.get("headers", {})
                    
                    logger.debug(f"Starting SSE client for {server_name} at {url}")
                    transport = await self.exit_stack.enter_async_context(
                        sse_client(url, headers=headers)
                    )
                    read, write = transport
                    logger.debug(f"Got SSE streams for {server_name}")
                    
                    # Create and initialize session using context manager
                    session = await self.exit_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    logger.debug(f"Session initialized for {server_name}")
                    
                    # Store the session
                    self.servers[server_name] = session
                    logger.debug(f"Session stored for {server_name}")
                    
                    # Discover tools
                    logger.debug(f"Calling session.list_tools() for {server_name}...")
                    try:
                        tools_response = await asyncio.wait_for(session.list_tools(), timeout=5.0)
                        logger.debug(f"list_tools() returned {len(tools_response.tools) if hasattr(tools_response, 'tools') else 'unknown'} tools")
                    except asyncio.TimeoutError:
                        logger.error(f"TIMEOUT: list_tools() took more than 5 seconds for {server_name}")
                        continue
                    except Exception as e:
                        logger.error(f"Exception listing tools: {type(e).__name__}: {e}")
                        continue
                    
                    # Cache tools with namespaced names
                    logger.debug(f"Caching tools for {server_name}")
                    for i, tool in enumerate(tools_response.tools):
                        namespaced_name = f"{server_name}.{tool.name}"
                        logger.debug(f"  Tool {i+1}: {tool.name} -> {namespaced_name}")
                        # Handle both snake_case and camelCase attribute names
                        input_schema = getattr(tool, 'input_schema', getattr(tool, 'inputSchema', None))
                        self.tools_cache[namespaced_name] = {
                            "server_name": server_name,
                            "original_name": tool.name,
                            "description": tool.description,
                            "input_schema": input_schema
                        }
                    
                    logger.info(f"✓ Successfully connected to {server_name}, found {len(tools_response.tools)} tools")
                    
                else:
                    logger.warning(f"Unknown transport type {transport_type} for {server_name}")
                    continue
                
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_name}: {e}")
                # Continue with other servers
    
    async def shutdown(self):
        """Gracefully close all MCP sessions"""
        try:
            await self.exit_stack.__aexit__(None, None, None)
            logger.info("All MCP connections closed")
        except Exception as e:
            logger.error(f"Error during MCP shutdown: {e}")
    
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
        
        # Extract content from CallToolResult object
        logger.debug(f"Converting CallToolResult to dict for {namespaced_name}")
        
        # Extract the text content from the result
        extracted_content = []
        if hasattr(result, 'content') and result.content:
            for content_item in result.content:
                if hasattr(content_item, 'text'):
                    extracted_content.append(content_item.text)
                elif hasattr(content_item, 'type') and content_item.type == 'text':
                    # Fallback if text is stored differently
                    extracted_content.append(str(content_item))
        
        # Build the response in a JSON-serializable format
        response = {
            "content": "\n".join(extracted_content) if extracted_content else "",
            "isError": getattr(result, 'isError', False)
        }
        
        # Add metadata if present
        if hasattr(result, 'meta') and result.meta is not None:
            response["meta"] = result.meta
            
        logger.debug(f"Converted result: {response}")
        
        return response